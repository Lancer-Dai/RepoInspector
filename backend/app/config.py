"""配置管理：使用 pydantic-settings 从环境变量/.env 加载。"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。"""

    # GitHub
    github_token: str | None = None
    request_timeout: float = 10.0
    cache_ttl_seconds: int = 300
    max_concurrent_requests: int = 6

    # 大模型（OpenAI 兼容协议）
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.siliconflow.cn/v1"
    llm_model: str = "Qwen/Qwen3.5-4B"
    llm_timeout: float = 30.0
    llm_cache_ttl_seconds: int = 3600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
