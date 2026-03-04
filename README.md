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
