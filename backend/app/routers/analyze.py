"""/api/analyze 与 /api/ai-review 路由。"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from .. import cache
from ..analyzer import (
    aggregate_monthly,
    analyze_contributors,
    analyze_issues,
    analyze_languages,
    analyze_releases,
    build_basic,
    build_social,
    compute_health_score,
)
from ..config import settings
from ..github_client import GitHubAPIError, GitHubClient, parse_repo_url
from ..llm_client import LLMError, review_repo
from ..models import (
    AIReview,
    AIReviewRequest,
    AnalyzeRequest,
    ErrorResponse,
    RepoReport,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------- 用户自定义配置覆盖（来自前端 header） ----------

class ConfigOverrides:
    """用户在请求 header 中传入的自定义配置。"""

    def __init__(
        self,
        github_token: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        llm_model: Optional[str] = None,
    ):
        self.github_token = github_token or None
        self.llm_api_key = llm_api_key or None
        self.llm_base_url = llm_base_url or None
        self.llm_model = llm_model or None

    def is_default(self) -> bool:
        return not any([self.github_token, self.llm_api_key, self.llm_base_url, self.llm_model])

    def fingerprint(self) -> str:
        """生成短哈希用于缓存键隔离不同用户配置。"""
        raw = f"{self.github_token}|{self.llm_api_key}|{self.llm_base_url}|{self.llm_model}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


async def get_overrides(
    x_github_token: Optional[str] = Header(default=None, alias="X-Github-Token"),
    x_llm_api_key: Optional[str] = Header(default=None, alias="X-LLM-Api-Key"),
    x_llm_base_url: Optional[str] = Header(default=None, alias="X-LLM-Base-Url"),
    x_llm_model: Optional[str] = Header(default=None, alias="X-LLM-Model"),
) -> ConfigOverrides:
    return ConfigOverrides(
        github_token=x_github_token,
        llm_api_key=x_llm_api_key,
        llm_base_url=x_llm_base_url,
        llm_model=x_llm_model,
    )


# ---------- 工具：从 URL 拿到 RepoReport（缓存命中 / 触发分析） ----------

async def get_or_fetch_report(url: str, overrides: ConfigOverrides) -> RepoReport:
    """获取仓库报告：优先用缓存，否则触发完整分析。"""
    try:
        owner, repo = parse_repo_url(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_url", "message": str(e)})

    cache_key = f"{owner.lower()}/{repo.lower()}|{overrides.fingerprint()}"
    cached = cache.get(cache_key, ttl=settings.cache_ttl_seconds)
    if cached is not None:
        return cached

    # 缓存未命中，复用 analyze 完整流程
    return await _fetch_and_cache(owner, repo, cache_key, overrides)


async def _fetch_and_cache(
    owner: str, repo: str, cache_key: str, overrides: ConfigOverrides
) -> RepoReport:
    """实际从 GitHub 拉取并缓存。"""
    token = overrides.github_token or settings.github_token
    async with GitHubClient(token=token) as gh:
        results = await asyncio.gather(
            gh.get_repo(owner, repo),
            gh.get_languages(owner, repo),
            gh.get_contributors(owner, repo),
            gh.get_commit_activity(owner, repo),
            gh.search_issues_count(owner, repo, "open"),
            gh.search_issues_count(owner, repo, "closed"),
            gh.list_releases(owner, repo),
            return_exceptions=True,
        )

    repo_data, languages, contributors, activity, open_n, closed_n, releases = results

    # 仓库信息是核心，失败需抛出
    if isinstance(repo_data, GitHubAPIError) or (
        not isinstance(repo_data, dict) and isinstance(repo_data, Exception)
    ):
        err = repo_data if isinstance(repo_data, GitHubAPIError) else GitHubAPIError(500, str(repo_data))
        if err.status == 404:
            raise HTTPException(status_code=404, detail={"error": "repo_not_found", "message": err.message})
        if err.status == 429:
            raise HTTPException(
                status_code=429,
                detail={"error": "rate_limited", "message": err.message, "retry_after": err.retry_after or 60},
                headers={"Retry-After": str(err.retry_after or 60)},
            )
        raise HTTPException(status_code=err.status or 500, detail={"error": "github_error", "message": err.message})

    if isinstance(languages, Exception):
        logger.warning("languages 拉取失败: %s", languages)
        languages = {}
    if isinstance(contributors, Exception):
        logger.warning("contributors 拉取失败: %s", contributors)
        contributors = []
    if isinstance(activity, Exception):
        logger.warning("commit_activity 拉取失败: %s", activity)
        activity = []
    if isinstance(open_n, Exception):
        open_n = 0
    if isinstance(closed_n, Exception):
        closed_n = 0
    if isinstance(releases, Exception):
        releases = []

    basic = build_basic(repo_data)
    social = build_social(repo_data)
    lang_stats = analyze_languages(languages or {})
    contrib_stats = analyze_contributors(contributors or [], top_n=10)
    monthly = aggregate_monthly(activity or [])
    issue_stats = analyze_issues(int(open_n or 0), int(closed_n or 0))
    release_stats = analyze_releases(releases or [], top_n=5)
    health = compute_health_score(repo_data, contributors or [], monthly, issue_stats, release_stats)

    report = RepoReport(
        basic=basic,
        social=social,
        languages=lang_stats,
        contributors=contrib_stats,
        commits_monthly=monthly,
        issues=issue_stats,
        releases=release_stats,
        health=health,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    cache.set(cache_key, report)
    return report


# ---------- 路由 ----------

@router.post(
    "/analyze",
    response_model=RepoReport,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
async def analyze(
    req: AnalyzeRequest,
    overrides: ConfigOverrides = Depends(get_overrides),
) -> RepoReport:
    """分析仓库并返回量化指标。"""
    return await get_or_fetch_report(req.url, overrides)


@router.post(
    "/ai-review",
    response_model=AIReview,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def ai_review(
    req: AIReviewRequest,
    overrides: ConfigOverrides = Depends(get_overrides),
) -> AIReview:
    """调用大模型对仓库进行综合评估（基于已分析的报告）。"""
    # 1) 拿到仓库报告（命中缓存则秒返）
    report = await get_or_fetch_report(req.url, overrides)

    # 2) 检查 AI 缓存（按 overrides 隔离）
    owner, repo = parse_repo_url(req.url)
    ai_cache_key = f"ai:{owner.lower()}/{repo.lower()}|{overrides.fingerprint()}"
    cached = cache.get(ai_cache_key, ttl=settings.llm_cache_ttl_seconds)
    if cached is not None:
        return cached

    # 3) 调用大模型（带 overrides）
    try:
        result = await review_repo(
            report.model_dump(),
            api_key=overrides.llm_api_key,
            base_url=overrides.llm_base_url,
            model=overrides.llm_model,
        )
    except LLMError as e:
        logger.error("AI review failed: %s", e)
        if e.status in (429,):
            raise HTTPException(
                status_code=429,
                detail={"error": "llm_rate_limited", "message": e.message, "retry_after": e.retry_after or 60},
                headers={"Retry-After": str(e.retry_after or 60)},
            )
        if e.status in (401, 403):
            raise HTTPException(status_code=500, detail={"error": "llm_auth", "message": "LLM API Key 无效或未配置"})
        # 其它（超时、空响应、解析失败等）
        raise HTTPException(
            status_code=502,
            detail={"error": "llm_failed", "message": e.message or "AI 评估失败"},
        )

    eff_model = overrides.llm_model or settings.llm_model
    review = AIReview(
        score=result["score"],
        summary=result["summary"],
        strengths=result["strengths"],
        weaknesses=result["weaknesses"],
        suggestions=result["suggestions"],
        model=result.get("model", eff_model),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    cache.set(ai_cache_key, review)
    return review


@router.get("/config")
async def get_config() -> dict:
    """返回当前系统默认配置（用于前端初始化设置弹窗的默认值）。"""
    return {
        "github_token": settings.github_token or "",
        "llm_api_key": settings.llm_api_key or "",
        "llm_base_url": settings.llm_base_url,
        "llm_model": settings.llm_model,
    }
