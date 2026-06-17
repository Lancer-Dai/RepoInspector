"""指标聚合与健康度评分。"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, List, Optional

from .models import (
    BasicInfo,
    ContributorStat,
    HealthScore,
    IssueStats,
    LanguageStat,
    MonthlyCommit,
    ReleaseInfo,
    SocialInfo,
)


# ---------- 基础信息 ----------

def build_basic(repo: dict) -> BasicInfo:
    license_info = repo.get("license") or {}
    owner = repo.get("owner") or {}
    return BasicInfo(
        full_name=repo.get("full_name", ""),
        name=repo.get("name", ""),
        description=repo.get("description"),
        html_url=repo.get("html_url", ""),
        owner_login=owner.get("login", ""),
        owner_avatar=owner.get("avatar_url", ""),
        created_at=repo.get("created_at", ""),
        updated_at=repo.get("updated_at", ""),
        pushed_at=repo.get("pushed_at", ""),
        default_branch=repo.get("default_branch", "main"),
        license_name=license_info.get("spdx_id") or license_info.get("name"),
        archived=bool(repo.get("archived", False)),
        topics=repo.get("topics") or [],
    )


def build_social(repo: dict) -> SocialInfo:
    return SocialInfo(
        stars=int(repo.get("stargazers_count", 0)),
        forks=int(repo.get("forks_count", 0)),
        watchers=int(repo.get("subscribers_count", repo.get("watchers_count", 0))),
        open_issues=int(repo.get("open_issues_count", 0)),
    )


# ---------- 语言分布 ----------

def analyze_languages(raw: dict) -> List[LanguageStat]:
    if not raw:
        return []
    total = sum(int(v) for v in raw.values()) or 1
    items = sorted(raw.items(), key=lambda x: -x[1])
    return [
        LanguageStat(name=k, bytes=int(v), percentage=round(int(v) / total * 100, 2))
        for k, v in items
    ]


# ---------- 贡献者 ----------

def analyze_contributors(raw: list, top_n: int = 10) -> List[ContributorStat]:
    result: List[ContributorStat] = []
    for c in (raw or [])[:top_n]:
        result.append(
            ContributorStat(
                login=c.get("login", ""),
                avatar_url=c.get("avatar_url", ""),
                contributions=int(c.get("contributions", 0)),
                html_url=c.get("html_url", ""),
            )
        )
    return result


# ---------- 提交活跃度 ----------

def aggregate_monthly(weekly: list) -> List[MonthlyCommit]:
    """把 GitHub 返回的周统计数据聚合为按月。"""
    if not weekly:
        return []
    bucket: dict[str, int] = {}
    for week in weekly:
        # week 结构: {week: unix_ts, total: int, days: [...]}
        ts = int(week.get("week", 0))
        if not ts:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        key = f"{dt.year:04d}-{dt.month:02d}"
        bucket[key] = bucket.get(key, 0) + int(week.get("total", 0))
    return [MonthlyCommit(month=k, count=v) for k, v in sorted(bucket.items())]


# ---------- Issue 统计 ----------

def analyze_issues(open_count: int, closed_count: int) -> IssueStats:
    total = open_count + closed_count
    close_rate = (closed_count / total) if total > 0 else 0.0
    return IssueStats(
        open=open_count,
        closed=closed_count,
        avg_close_hours=None,  # 精确计算需要遍历 issue 列表，代价过高，留作可选项
        close_rate=round(close_rate, 4),
    )


# ---------- Release ----------

def analyze_releases(raw: list, top_n: int = 5) -> List[ReleaseInfo]:
    return [
        ReleaseInfo(
            tag_name=r.get("tag_name", ""),
            name=r.get("name"),
            published_at=r.get("published_at"),
            html_url=r.get("html_url", ""),
        )
        for r in (raw or [])[:top_n]
    ]


# ---------- 健康度评分 ----------

def _clamp(v: float, lo: float = 0, hi: float = 100) -> int:
    return max(lo, min(hi, int(round(v))))


def compute_health_score(
    repo: dict,
    contributors: list,
    monthly_commits: list,
    issues: IssueStats,
    releases: list,
) -> HealthScore:
    """综合健康度评分（0-100）。"""

    stars = int(repo.get("stargazers_count", 0))
    forks = int(repo.get("forks_count", 0))

    # 流行度：对数归一化
    popularity_raw = math.log10(stars + 1) / math.log10(200_000) * 100
    popularity = _clamp(popularity_raw)

    # 活跃度：近 3 月 commit + Release 频次
    recent_commits = sum(m.count for m in monthly_commits[-3:]) if monthly_commits else 0
    activity_part1 = min(recent_commits / 300.0, 1.0) * 70  # commit 占比 70 分
    activity_part2 = min(len(releases) / 5.0, 1.0) * 30       # release 占比 30 分
    activity = _clamp(activity_part1 + activity_part2)

    # 社区：贡献者数量 + Issue 关闭率
    contrib_n = len(contributors or [])
    community_part1 = min(contrib_n / 30.0, 1.0) * 60
    community_part2 = issues.close_rate * 40
    community = _clamp(community_part1 + community_part2)

    # 维护性：未 archived + 有 LICENSE + 有描述
    maintenance = 0
    if not repo.get("archived", False):
        maintenance += 40
    if (repo.get("license") or {}).get("spdx_id"):
        maintenance += 30
    if repo.get("description"):
        maintenance += 20
    if (repo.get("open_issues_count", 0) > 0) or len(releases) > 0:
        maintenance += 10
    maintenance = _clamp(maintenance)

    total = _clamp(popularity * 0.3 + activity * 0.3 + community * 0.2 + maintenance * 0.2)

    return HealthScore(
        total=total,
        popularity=popularity,
        activity=activity,
        community=community,
        maintenance=maintenance,
    )
