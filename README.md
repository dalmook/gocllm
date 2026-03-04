# gocllm

## LLM/RAG Runtime ENV

- `LLM_WORKERS` (default: `4`): 작업 큐를 소비하는 LLM 워커 수
- `LLM_JOB_QUEUE_MAX` (default: `200`): LLM 작업 큐 최대 적재량
- `LLM_MAX_CONCURRENT` (default: `4`): 실제 LLM 처리 동시 실행 상한(세마포어)
- `ENABLE_QUERY_REWRITE` (default: `true`): 검색 질의 재작성 on/off
- `MAX_RAG_QUERIES` (default: `2`): 질문당 최대 RAG 검색 질의 수
- `RAG_INCLUDE_ORIGINAL_QUERY` (default: `true`): 재작성 외 원문 질의 포함 여부
- `RAG_RETRIEVE_MODE` (default: `hybrid`): `bm25`, `knn`, `hybrid`, `weighted_hybrid`
- `RAG_BM25_BOOST` (default: `0.025`): weighted_hybrid 시 BM25 가중치
- `RAG_KNN_BOOST` (default: `7.98`): weighted_hybrid 시 KNN 가중치
