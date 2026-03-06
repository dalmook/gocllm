from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from .llm_client import LLMClient


class Step(BaseModel):
    id: str
    tool: Literal["rag.search", "rag.extract_entities", "db.query", "compute.diff", "answer.compose"]
    args: Dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    intent: Literal["data_only", "rag_only", "hybrid"]
    steps: List[Step]


class Planner:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def make_plan(self, question: str, query_catalog: List[Dict[str, str]]) -> Plan:
        # fallback heuristic if llm is not configured
        if not self.llm.enabled:
            if "이슈" in question:
                return Plan(intent="rag_only", steps=[
                    Step(id="s1", tool="rag.search", args={"query": question, "top_k": 5}),
                    Step(id="s2", tool="answer.compose", args={"question": question, "rag_from": "s1", "data_from": []}),
                ])
            return Plan(intent="data_only", steps=[
                Step(id="s1", tool="db.query", args={"query_id": "psi_sales_by_month", "params": {}}),
                Step(id="s2", tool="answer.compose", args={"question": question, "data_from": ["s1"]}),
            ])

        sys_prompt = (
            "You are a strict planning engine. Output JSON only. Never write SQL. "
            "Select query_id from catalog only."
        )
        user_prompt = (
            f"question={question}\n"
            f"catalog={query_catalog}\n"
            "Return Plan JSON with intent(data_only|rag_only|hybrid) and steps."
        )
        data = self.llm.invoke_json(sys_prompt, user_prompt)
        return Plan.model_validate(data)
