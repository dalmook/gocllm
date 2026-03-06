#!/usr/bin/env python3
"""
Quick test chatbot: question -> Oracle SQL -> LLM answer

Example:
  python sql_llm_test.py --question "2월 WC 버전 판매 몇개야"

DB env (optional if you use same defaults as gocllm.py):
  ORACLE_HOST (default: gmgsdd09-vip.sec.samsung.net)
  ORACLE_PORT (default: 2541)
  ORACLE_SERVICE (default: MEMSCM)
  ORACLE_USER (default: memscm)
  ORACLE_PW / ORACLE_PASSWORD (default: mem01scm)
  ORACLE_DSN (optional: if set, used directly)

LLM env (same style as gocllm):
  LLM_PROVIDER_PROFILE=gauss|gpt_oss

  # gauss profile
  LLM_API_KEY
  LLM_API_URL
  LLM_MODEL_NAME
  LLM_SEND_SYSTEM_NAME
  LLM_USER_TYPE

  # gpt_oss profile
  GPT_OSS_API_KEY
  GPT_OSS_API_URL
  GPT_OSS_MODEL_NAME
  GPT_OSS_SEND_SYSTEM_NAME
  GPT_OSS_USER_TYPE
"""

import argparse
import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List

import oracledb
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


BASE_SQL = """
select yearmonth, version, sum(sales_meq) as sales
from mst_psi_simul_report
where workdate = to_char(sysdate,'yyyymmdd')
  and p_module = 'PMIX'
  and s_module = 'SOKBO'
""".strip()


MONTH_MAP = {
    "1월": "01", "2월": "02", "3월": "03", "4월": "04", "5월": "05", "6월": "06",
    "7월": "07", "8월": "08", "9월": "09", "10월": "10", "11월": "11", "12월": "12",
}


def llm_config(user_id: str = "bot") -> Dict[str, Any]:
    profile = os.getenv("LLM_PROVIDER_PROFILE", "gauss").strip().lower()

    if profile == "gpt_oss":
        return {
            "base_url": os.getenv("GPT_OSS_API_URL", "http://apigw-stg.samsungds.net:8000/gpt-oss/1/gpt-oss-120b/v1"),
            "model": os.getenv("GPT_OSS_MODEL_NAME", "openai/gpt-oss-120b"),
            "headers": {
                "x-dep-ticket": os.getenv("GPT_OSS_API_KEY", ""),
                "Send-System-Name": os.getenv("GPT_OSS_SEND_SYSTEM_NAME", "GOC_MAIL_RAG_PIPELINE"),
                "User-Id": user_id,
                "User-Type": os.getenv("GPT_OSS_USER_TYPE", "AD_ID"),
                "Prompt-Msg-Id": str(uuid.uuid4()),
                "Completion-Msg-Id": str(uuid.uuid4()),
            },
        }

    return {
        "base_url": os.getenv("LLM_API_URL", "http://apigw.samsungds.net:8000/model-23/1/gausso4-instruct/v1"),
        "model": os.getenv("LLM_MODEL_NAME", "GaussO4-instruct"),
        "headers": {
            "x-dep-ticket": os.getenv("LLM_API_KEY", ""),
            "Send-System-Name": os.getenv("LLM_SEND_SYSTEM_NAME", "GOC_MAIL_RAG_PIPELINE"),
            "User-Id": user_id,
            "User-Type": os.getenv("LLM_USER_TYPE", "bot"),
            "Prompt-Msg-Id": str(uuid.uuid4()),
            "Completion-Msg-Id": str(uuid.uuid4()),
        },
    }


def create_llm(user_id: str = "bot") -> ChatOpenAI:
    os.environ.setdefault("OPENAI_API_KEY", "dummy")
    cfg = llm_config(user_id)
    return ChatOpenAI(
        base_url=cfg["base_url"],
        model=cfg["model"],
        temperature=0.1,
        max_tokens=600,
        default_headers=cfg["headers"],
    )


def parse_filters(question: str):
    q = (question or "").strip()
    month = None
    for k, v in MONTH_MAP.items():
        if k in q:
            month = v
            break

    version_like = None
    m = re.search(r"([A-Za-z0-9_-]+)\s*버전", q)
    if m:
        version_like = m.group(1).upper()

    return month, version_like


def build_sql(month: str | None, version_like: str | None):
    sql = BASE_SQL
    binds = {}

    # yearmonth is text like '202603'
    if month:
        sql += "\n  and substr(yearmonth, 5, 2) = :p_month"
        binds["p_month"] = month

    if version_like:
        sql += "\n  and upper(version) like :p_version"
        binds["p_version"] = f"%{version_like}%"

    sql += "\ngroup by yearmonth, version"
    sql += "\norder by yearmonth, version"
    return sql, binds


def query_db(sql: str, binds: Dict[str, Any]) -> List[Dict[str, Any]]:
    # same default style as gocllm.py (for quick local test)
    host = os.getenv("ORACLE_HOST", "gmgsdd09-vip.sec.samsung.net")
    port = int(os.getenv("ORACLE_PORT", "2541"))
    service = os.getenv("ORACLE_SERVICE", "MEMSCM")
    user = os.getenv("ORACLE_USER", "memscm")
    pwd = os.getenv("ORACLE_PW", os.getenv("ORACLE_PASSWORD", "mem01scm"))
    dsn = os.getenv("ORACLE_DSN") or oracledb.makedsn(host, port, service_name=service)

    with oracledb.connect(user=user, password=pwd, dsn=dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, binds)
            rows = cur.fetchall()

    out = []
    for ym, ver, qty in rows:
        out.append({
            "yearmonth": str(ym),
            "version": str(ver),
            "sales": float(qty) if qty is not None else 0.0,
        })
    return out


def llm_answer(question: str, rows: List[Dict[str, Any]]) -> str:
    llm = create_llm("sql-test-bot")
    system = """
당신은 영업 데이터 요약 어시스턴트입니다.
규칙:
1) 제공된 SQL 결과만 근거로 답변한다.
2) 없는 값은 추측하지 않는다.
3) 답변은 간결하게: 한줄 요약 + 표 형태 bullet.
""".strip()

    data_json = json.dumps(rows, ensure_ascii=False)
    user = f"질문: {question}\n\nSQL 결과(JSON):\n{data_json}"
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return (resp.content or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True, help="예: 2월 WC 버전 판매 몇개야")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    question = args.question
    month, version_like = parse_filters(question)
    sql, binds = build_sql(month, version_like)

    if args.debug:
        print("[DEBUG] month=", month, "version_like=", version_like)
        print("[DEBUG] SQL:\n", sql)
        print("[DEBUG] binds=", binds)

    rows = query_db(sql, binds)

    if not rows:
        print("조회 결과가 없습니다.")
        return

    # quick plain fallback
    total = sum(r["sales"] for r in rows)
    print(f"[RAW] 조회 {len(rows)}건, 판매 합계={total:,.2f}")

    answer = llm_answer(question, rows)
    print("\n=== LLM Answer ===")
    print(answer)


if __name__ == "__main__":
    main()
