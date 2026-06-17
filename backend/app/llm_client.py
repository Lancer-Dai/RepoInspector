"""大模型客户端：调用 OpenAI 兼容协议（SiliconFlow / DeepSeek / 智谱 等）。"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Optional

from openai import AsyncOpenAI

from .config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """大模型调用相关错误。"""

    def __init__(self, status: int, message: str, retry_after: Optional[int] = None):
        self.status = status
        self.message = message
        self.retry_after = retry_after
        super().__init__(f"LLM error {status}: {message}")


_client: Optional[AsyncOpenAI] = None
_client_signature: Optional[tuple] = None


def _get_client(api_key: str, base_url: str, timeout: float) -> AsyncOpenAI:
    """获取（或创建匹配覆盖参数）的 OpenAI 客户端。

    当用户通过前端自定义 API key / base_url 时，需要为不同配置创建独立客户端实例。
    """
    global _client, _client_signature
    sig = (api_key, base_url, timeout)
    if _client is None or _client_signature != sig:
        if not api_key:
            raise LLMError(500, "未配置 LLM_API_KEY，无法调用大模型")
        _client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        _client_signature = sig
    return _client


# ---------- Prompt 模板 ----------

_SYSTEM_PROMPT = """你是资深软件工程师和开源项目评估专家。
请基于提供的 GitHub 仓库量化指标，进行专业、客观、有建设性的综合评估。

要求：
1. 综合考虑流行度、活跃度、社区、维护性、代码语言分布等维度
2. 给出 0-100 的整数评分（可参考提供的系统评分，但允许有 ±10 分的调整）
3. 总结要简洁有信息量，避免空话
4. 优势/不足/建议必须具体、可操作，避免泛泛而谈
5. 严格返回 JSON 格式（不要包含任何 markdown 代码块标记）"""

_USER_PROMPT_TEMPLATE = """请基于以下 GitHub 仓库量化指标，独立进行综合评估并打分。

【仓库基础信息】
- 名称: {full_name}
- 描述: {description}
- 许可证: {license_name}
- 是否归档: {archived}
- 主要语言: {languages}

【社交指标】
- Stars: {stars}
- Forks: {forks}
- Watchers: {watchers}
- Open Issues: {open_issues}

【活跃度指标】
- 近 3 月 commit 数: {recent_commits}
- 最近 12 月 commit 数: {total_commits}
- 最近 Release 数: {release_count}

【Issue 健康度】
- Open / Closed: {open_n} / {closed_n}
- 关闭率: {close_rate}%

请严格按以下 JSON 结构返回（不要任何 markdown 包装）:
{{
  "score": 整数 0-100,
  "summary": "2-3 句整体评价",
  "strengths": ["具体优势1", "具体优势2", "具体优势3"],
  "weaknesses": ["具体不足1", "具体不足2"],
  "suggestions": ["可操作建议1", "可操作建议2", "可操作建议3"]
}}"""


def _build_user_prompt(report: dict) -> str:
    basic = report["basic"]
    social = report["social"]
    languages = report.get("languages", [])
    monthly = report.get("commits_monthly", [])
    issues = report["issues"]

    lang_str = ", ".join(f"{l['name']} ({l['percentage']}%)" for l in languages[:5]) or "未知"
    recent_commits = sum(m["count"] for m in monthly[-3:]) if monthly else 0
    total_commits = sum(m["count"] for m in monthly) if monthly else 0

    return _USER_PROMPT_TEMPLATE.format(
        full_name=basic.get("full_name", ""),
        description=basic.get("description") or "无",
        license_name=basic.get("license_name") or "无",
        archived="是" if basic.get("archived") else "否",
        languages=lang_str,
        stars=social.get("stars", 0),
        forks=social.get("forks", 0),
        watchers=social.get("watchers", 0),
        open_issues=social.get("open_issues", 0),
        recent_commits=recent_commits,
        total_commits=total_commits,
        release_count=len(report.get("releases", [])),
        open_n=issues.get("open", 0),
        closed_n=issues.get("closed", 0),
        close_rate=round(issues.get("close_rate", 0) * 100, 1),
    )


# ---------- JSON 解析（兜底：模型偶尔不会输出纯 JSON） ----------

_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _parse_json_lenient(content: str) -> dict:
    """尝试从模型输出中提取 JSON 字典。"""
    content = content.strip()
    # 去掉 markdown 代码块包装
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    m = _JSON_RE.search(content)
    if m:
        return json.loads(m.group(0))
    raise LLMError(500, f"无法解析模型输出为 JSON: {content[:200]}")


def _normalize(data: dict) -> dict:
    """把模型输出归一化到标准结构。"""
    score = data.get("score", 0)
    try:
        score = int(round(float(score)))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    def _list(value) -> list[str]:
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    return {
        "score": score,
        "summary": str(data.get("summary", "")).strip(),
        "strengths": _list(data.get("strengths")),
        "weaknesses": _list(data.get("weaknesses")),
        "suggestions": _list(data.get("suggestions")),
    }


# ---------- 对外 API ----------

async def review_repo(
    report: dict,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
) -> dict:
    """调用大模型对仓库进行综合评估。

    入参 report 应是 RepoReport 字典。
    返回归一化后的字典: {score, summary, strengths, weaknesses, suggestions, model}

    备注：SiliconFlow 上的 Qwen3.5 系列模型有两个特殊点：
    1. 必须 stream=True，否则返回 400
    2. 默认是思考模型，会把 token 预算花在 reasoning_content，需要
       enable_thinking=False 关闭思考才能拿到最终 JSON
    拼接所有 delta.content（若仍走思考，则回退到 reasoning_content）。

    所有可选参数优先使用传入值，否则回退到环境变量中的配置。
    """
    eff_api_key = api_key or settings.llm_api_key
    eff_base_url = (base_url or settings.llm_base_url).rstrip("/")
    eff_model = model or settings.llm_model
    eff_timeout = timeout if timeout is not None else settings.llm_timeout

    client = _get_client(eff_api_key, eff_base_url, eff_timeout)
    user_prompt = _build_user_prompt(report)

    # 硬性总时长上限：openai 流式客户端对 eff_timeout 的应用
    # 在某些边界情况下不可靠，套一层 asyncio.wait_for 确保最终能退出
    hard_timeout = max(60.0, eff_timeout + 30.0)

    parts: list[str] = []
    try:
        async def _call():
            stream = await client.chat.completions.create(
                model=eff_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
                stream=True,
                # Qwen3.5 系列是思考模型：默认会把预算花在 reasoning_content 上，
                # 关闭思考模式后才能直接产出最终回答
                extra_body={"enable_thinking": False},
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if not delta:
                    continue
                if delta.content:
                    parts.append(delta.content)
                elif getattr(delta, "reasoning_content", None):
                    # 兜底：若模型仍输出思考内容，先保存
                    parts.append(delta.reasoning_content)
            return "".join(parts)

        content = await asyncio.wait_for(_call(), timeout=hard_timeout)
    except asyncio.TimeoutError as e:
        raise LLMError(
            504,
            f"模型响应超时（>{hard_timeout:.0f}s）。"
            f"{eff_model} 在复杂 prompt 下可能较慢，可换用更快的模型。",
        ) from e
    except Exception as e:  # noqa: BLE001
        # openai 库的异常体系较复杂，统一转 LLMError
        status = getattr(e, "status_code", 500)
        message = str(e)
        retry_after = None
        ra = getattr(e, "retry_after", None)
        if ra is not None:
            try:
                retry_after = int(ra)
            except (TypeError, ValueError):
                retry_after = None
        logger.error("LLM call failed: %s", message)
        raise LLMError(status, message, retry_after) from e

    content = content.strip()
    if not content:
        raise LLMError(500, "模型返回内容为空")

    data = _parse_json_lenient(content)
    normalized = _normalize(data)
    normalized["model"] = eff_model
    return normalized
