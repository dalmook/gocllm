[MEMORY] hit=True message_count=6 prompt_chars=1613 use_in_rewrite=False
[RAG] original question=FLASH 이슈 사항 정리해줘
[RAG] normalized query=FLASH 이슈 사항 정리 해줘
[RAG] glossary_intent=False
[RAG] force_glossary=False
[RAG] search queries: ['FLASH 이슈 사항 정리 해줘']
[RAG] prefer_recent_docs=True issue_summary_intent=True strong_mail_intent=True time_range=none top_k=200 indexes=['rp-gocinfo_mail_jsonl']
[RAG Search] Query(raw): FLASH 이슈 사항 정리 해줘
[RAG Search] Query(sanitized): FLASH 이슈 사항 정리 해줘
[RAG Search] Indexes: ['rp-gocinfo_mail_jsonl']
[RAG Search] Base URL: http://apigw.samsungds.net:8000/ds_llm_rag/2/dsllmrag/elastic/v2
[RAG Search] Num Result Doc: 200
[RAG Search] Searching index: rp-gocinfo_mail_jsonl
[RAG Search Error] Index: rp-gocinfo_mail_jsonl, Error: RAG API Error: 422 - {"result":"error","error_code":"INVALID_REQUEST","message":"The request is invalid.","detail":[{"type":"less_than_equal","loc":["body","num_result_doc"],"msg":"Input should be less than or equal to 100","input":200}],"trace_id":"9eff80dee55d4726b56d37ba3ec45cfe"}
Traceback (most recent call last):
  File "h:\python_pjt\main.py", line 601, in search_rag_documents
    result = rag_client.retrieve(
             ^^^^^^^^^^^^^^^^^^^^
  File "h:\python_pjt\main.py", line 545, in retrieve
    raise Exception(f"RAG API Error: {r.status_code} - {r.text}")
Exception: RAG API Error: 422 - {"result":"error","error_code":"INVALID_REQUEST","message":"The request is invalid.","detail":[{"type":"less_than_equal","loc":["body","num_result_doc"],"msg":"Input should be less than or equal to 100","input":200}],"trace_id":"9eff80dee55d4726b56d37ba3ec45cfe"}
[RAG Search] Total results: 0
[RAG] 병렬 검색 완료: query=FLASH 이슈 사항 정리 해줘 docs=0
[RAG Domain Selection] selected_rag_domain=none, glossary_intent=False, force_glossary=False, mail_match=False, glossary_match=False
[RAG Final] selected_rag_domain=none used_rag=False fallback_reason=검색 문서 유사도가 기준치(0.35)보다 낮았습니다.
[LLM PERF] total=12300ms init=673ms memory=674ms rewrite=1ms rag=40ms rerank=0ms llm=11451ms
[llm-worker-1][c7dfa026-d6ae-44f3-af48-8145e737ac31] done queue_wait=0.05s total=12.35s rag_calls=1 llm_calls=1 used_rag=False memory_hit=True memory_message_count=6 memory_prompt_chars=1613 rewrite_used_memory=False fallback_reason=검색 문서 유사도가 기준치(0.35)보다 낮았습니다. rpm=1@2026-03-06 08:12
