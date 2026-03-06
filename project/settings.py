from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Hybrid RAG+DB Assistant")
    app_env: str = os.getenv("APP_ENV", "dev")
    timezone: str = os.getenv("APP_TIMEZONE", "Asia/Seoul")

    # planner llm
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    llm_send_system_name: str = os.getenv("LLM_SEND_SYSTEM_NAME", "HYBRID_ASSISTANT")
    llm_user_type: str = os.getenv("LLM_USER_TYPE", "AD_ID")

    # oracle
    oracle_host: str = os.getenv("ORACLE_HOST", "")
    oracle_port: int = int(os.getenv("ORACLE_PORT", "1521"))
    oracle_service: str = os.getenv("ORACLE_SERVICE", "")
    oracle_user: str = os.getenv("ORACLE_USER", "")
    oracle_password: str = os.getenv("ORACLE_PW", os.getenv("ORACLE_PASSWORD", ""))
    oracle_dsn: str = os.getenv("ORACLE_DSN", "")

    query_dir: str = os.getenv("QUERY_DIR", "project/query_registry/queries")


settings = Settings()
