from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import requests


@dataclass(frozen=True)
class AIConfig:
    configured: bool
    provider: str
    model: str | None = None
    api_key: str | None = None
    azure_endpoint: str | None = None
    azure_deployment: str | None = None
    azure_api_version: str = "2024-02-15-preview"
    status_message: str = "AI features are not configured yet."


def get_ai_config() -> AIConfig:
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if azure_key and azure_endpoint and azure_deployment:
        return AIConfig(
            configured=True,
            provider="azure_openai",
            api_key=azure_key,
            azure_endpoint=azure_endpoint.rstrip("/"),
            azure_deployment=azure_deployment,
            azure_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            status_message="AI configured with Azure OpenAI.",
        )

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return AIConfig(
            configured=True,
            provider="openai",
            api_key=openai_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            status_message="AI configured with OpenAI.",
        )

    return AIConfig(configured=False, provider="none")


def call_llm(config: AIConfig, system_prompt: str, user_prompt: str, timeout: int = 60) -> dict[str, Any]:
    if not config.configured:
        return {
            "ok": False,
            "text": "AI features are not configured yet.",
            "error": "missing_configuration",
        }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        if config.provider == "azure_openai":
            url = (
                f"{config.azure_endpoint}/openai/deployments/{config.azure_deployment}"
                f"/chat/completions?api-version={config.azure_api_version}"
            )
            response = requests.post(
                url,
                headers={
                    "api-key": config.api_key or "",
                    "Content-Type": "application/json",
                },
                json={
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 1200,
                },
                timeout=timeout,
            )
        else:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.model,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 1200,
                },
                timeout=timeout,
            )

        response.raise_for_status()
        payload = response.json()
        text = payload["choices"][0]["message"]["content"].strip()
        return {"ok": True, "text": text, "error": None}
    except Exception as exc:
        return {
            "ok": False,
            "text": "AI response is not available. The structured data sections remain available.",
            "error": str(exc),
        }
