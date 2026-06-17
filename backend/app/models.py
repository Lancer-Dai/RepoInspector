"""Pydantic 数据模型：请求/响应结构定义。"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="GitHub 仓库 URL，如 https://github.com/owner/repo")


class LanguageStat(BaseModel):
    name: str
    bytes: int
    percentage: float


class ContributorStat(BaseModel):
    login: str
    avatar_url: str
    contributions: int
    html_url: str


class IssueStats(BaseModel):
    open: int
    closed: int
    avg_close_hours: Optional[float] = None
    close_rate: float = 0.0


class MonthlyCommit(BaseModel):
    month: str  # "2025-07"
    count: int


class HealthScore(BaseModel):
    total: int
    popularity: int
    activity: int
    community: int
    maintenance: int


class BasicInfo(BaseModel):
    full_name: str
    name: str
    description: Optional[str] = None
    html_url: str
    owner_login: str
    owner_avatar: str
    created_at: str
    updated_at: str
    pushed_at: str
    default_branch: str
    license_name: Optional[str] = None
    archived: bool = False
    topics: List[str] = []


class SocialInfo(BaseModel):
    stars: int
    forks: int
    watchers: int
    open_issues: int


class ReleaseInfo(BaseModel):
    tag_name: str
    name: Optional[str] = None
    published_at: Optional[str] = None
    html_url: str


class RepoReport(BaseModel):
    basic: BasicInfo
    social: SocialInfo
    languages: List[LanguageStat]
    contributors: List[ContributorStat]
    commits_monthly: List[MonthlyCommit]
    issues: IssueStats
    releases: List[ReleaseInfo]
    health: HealthScore
    generated_at: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    retry_after: Optional[int] = None


class AIReviewRequest(BaseModel):
    url: str = Field(..., description="GitHub 仓库 URL")


class AIReview(BaseModel):
    score: int
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    model: str
    generated_at: str
