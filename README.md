# gocllm

## LLM/RAG Runtime ENV

- `LLM_WORKERS` (default: `4`): 작업 큐를 소비하는 LLM 워커 수
- `LLM_JOB_QUEUE_MAX` (default: `200`): LLM 작업 큐 최대 적재량
- `LLM_MAX_CONCURRENT` / `LLM_MAX_CONCURRENCY` (default: `4`): 실제 LLM 처리 동시 실행 상한(세마포어)
- `LLM_PER_USER_SINGLEFLIGHT` (default: `true`): 유저당 동시에 1개 요청만 허용
- `LLM_RETRY_ATTEMPTS` (default: `3`): 502/503/504 재시도 횟수
- `LLM_RETRY_BASE_DELAY` (default: `1.5`): 재시도 백오프 기본 지연(초)
- `ENABLE_QUERY_REWRITE` (default: `true`): 검색 질의 재작성 on/off
- `MAX_RAG_QUERIES` (default: `3`): 질문당 최대 RAG 검색 질의 수
- `RAG_INCLUDE_ORIGINAL_QUERY` (default: `true`): 재작성 외 원문 질의 포함 여부
- `RAG_RETRIEVE_MODE` (default: `hybrid`): `bm25`, `knn`, `hybrid`, `weighted_hybrid`
- `RAG_BM25_BOOST` (default: `0.025`): weighted_hybrid 시 BM25 가중치
- `RAG_KNN_BOOST` (default: `7.98`): weighted_hybrid 시 KNN 가중치
- `RAG_FILTER_DATE_FIELD` (default: `created_time`): 상대 날짜 필터에 사용할 인덱스 시간 필드명

## 동작 시나리오 (요약)

- SINGLE에서 일반 텍스트 입력 → LLM 처리
- SINGLE에서 `INTRO`/`HOME` 버튼 또는 트리거 텍스트 → 홈 카드
- GROUP에서는 UI는 DM 라우팅되지만 LLM은 기본 비활성
- 예: `HBM 저번주 이슈 정리해줘` → 저번주 기간 필터를 RAG 조회에 적용, 관련 문서가 충분하면 문서 기반 + AI 추가참고 형식으로 응답

#기타

- 등록자 쿼리 : "SELECT SSO_ID FROM SCM_WP.T_T_FOR_MASTER A WHERE 1=1 AND a.sso_id = 'sungmook.cho' AND A.DEPT_NAME LIKE '%SCM%메모리%' and a.POSITION_CODE is not null AND A.SSO_ID NOT IN ('SCM.RPA','SCM 봇','메모리STO2','메모리 STO','dalbong.chatbot01', 'dalbongbot01', 'dalbong.bot01', 'command.center', 'thatcoolguy')"

🔗 이슈지 바로가기 👉 https://go/이슈지

[RAG Search Error] Index: rp-gocinfo-mail, Error: RAG API Error: no available retrieval endpoint (bm25 not found)
Traceback (most recent call last):
  File "H:\python_pjt\main.py", line 709, in search_rag_documents
    result = rag_client.retrieve(
             ^^^^^^^^^^^^^^^^^^^^
  File "H:\python_pjt\main.py", line 581, in retrieve
    raise Exception(f"RAG API Error: no available retrieval endpoint ({last_error or 'unknown'})")
Exception: RAG API Error: no available retrieval endpoint (bm25 not found)
[RAG Search] Total results: 0
[RAG] 병렬 검색 완료: query=hbm 정보 알려줘 docs=0
[llm-worker-1][e39729d0-a195-46cf-9ec9-ff3619b8cc17] done queue_wait=0.00s total=7.56s rag_calls=1 llm_calls=1 used_rag=False fallback_reason=검색 문서 유사도가 기준치(0.35)보다 낮았습니다. rpm=1@2026-03-05 08:50
