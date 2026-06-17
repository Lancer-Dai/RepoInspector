"""GitHub API 客户端：封装 REST 调用，处理限流与错误。"""
from __future__ import annotations

import asyncio
import re
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from .config import settings


GITHUB_API = "https://api.github.com"


class GitHubAPIError(Exception):
    """通用 GitHub API 错误。"""

    def __init__(self, status: int, message: str, retry_after: Optional[int] = None):
        self.status = status
        self.message = message
        self.retry_after = retry_after
        super().__init__(f"GitHub API error {status}: {message}")


# ---------- URL 解析 ----------

_URL_RE = re.compile(
    r"^https?://github\.com/([A-Za-z0-9][A-Za-z0-9._-]*)/([A-Za-z0-9][A-Za-z0-9._-]*)(?:\.git)?/?$"
)


def parse_repo_url(url: str) -> tuple[str, str]:
    """从 GitHub 仓库 URL 中解析出 (owner, repo)。"""
    if not url:
        raise ValueError("URL 不能为空")
    url = url.strip()
    m = _URL_RE.match(url)
    if not m:
        # 兜底：尝试用 urlparse 提取 path
        try:
            parts = urlparse(url).path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] and parts[1]:
                return parts[0], parts[1].removesuffix(".git")
        except Exception:
            pass
        raise ValueError(f"非法的 GitHub 仓库 URL: {url}")
    return m.group(1), m.group(2)


# ---------- 客户端 ----------

class GitHubClient:
    """异步 GitHub API 客户端。"""

    def __init__(self, token: Optional[str] = None, timeout: float = 10.0):
        self.token = token or settings.github_token
        self.timeout = timeout
        self._sem = asyncio.Semaphore(settings.max_concurrent_requests)
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "RepoInspector/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self._client = httpx.AsyncClient(timeout=timeout, headers=headers)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "GitHubClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def _get(self, path: str, params: Optional[dict] = None) -> Any:
        url = f"{GITHUB_API}{path}"
        async with self._sem:
            try:
                resp = await self._client.get(url, params=params)
            except httpx.TimeoutException as e:
                raise GitHubAPIError(0, f"请求超时: {e}") from e
            except httpx.HTTPError as e:
                raise GitHubAPIError(0, f"网络错误: {e}") from e

        if resp.status_code == 404:
            raise GitHubAPIError(404, "仓库不存在或为私有仓库")
        if resp.status_code in (403, 429):
            # 限流
            remaining = resp.headers.get("X-RateLimit-Remaining")
            reset = resp.headers.get("X-RateLimit-Reset")
            retry_after = None
            if reset and reset.isdigit():
                import time
                retry_after = max(0, int(reset) - int(time.time()))
            raise GitHubAPIError(429, f"GitHub API 限流（剩余 {remaining}）", retry_after=retry_after)
        if resp.status_code >= 400:
            try:
                msg = resp.json().get("message", resp.text)
            except Exception:
                msg = resp.text
            raise GitHubAPIError(resp.status_code, msg)

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # ---------- 仓库基础 ----------

    async def get_repo(self, owner: str, repo: str) -> dict:
        return await self._get(f"/repos/{owner}/{repo}")

    async def get_languages(self, owner: str, repo: str) -> dict:
        return await self._get(f"/repos/{owner}/{repo}/languages")

    async def get_contributors(self, owner: str, repo: str, per_page: int = 30) -> list:
        return await self._get(
            f"/repos/{owner}/{repo}/contributors",
            params={"per_page": per_page, "anon": "false"},
        )

    async def get_commit_activity(self, owner: str, repo: str) -> list:
        """近 1 年 commit 统计（按周）。可能返回 202 表示计算中，需重试。"""
        for _ in range(3):
            data = await self._get(f"/repos/{owner}/{repo}/stats/commit_activity")
            if data:
                return data
            await asyncio.sleep(0.5)
        return []

    async def search_issues_count(self, owner: str, repo: str, state: str) -> int:
        """使用 search API 精确统计 issue 数量。state: open/closed。"""
        q = f"repo:{owner}/{repo} is:issue state:{state}"
        try:
            data = await self._get("/search/issues", params={"q": q, "per_page": 1})
            return int(data.get("total_count", 0))
        except GitHubAPIError as e:
            # 搜索 API 也可能限流，失败时降级
            if e.status in (403, 429):
                return 0
            raise

    async def list_releases(self, owner: str, repo: str, per_page: int = 5) -> list:
        return await self._get(f"/repos/{owner}/{repo}/releases", params={"per_page": per_page})
