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

{"doc_id":"MAIL::20260304041556epcms2p4dfa6f42f609a326cd0e8ba7496363ebe_epcms2p4","chunk_id":"MAIL::20260304041556epcms2p4dfa6f42f609a326cd0e8ba7496363ebe_epcms2p4_000000","title":"■3/5(목) Global운영팀 일일근태","merge_title_content":"■3/5(목) Global운영팀 일일근태 [SEP] [문서 정보]\n\nBULLET::- 제목: ■3/5(목) Global운영팀 일일근태\nBULLET::- 최초 작성일: 2026-03-05\nBULLET::- 마지막 수정일: 2026-03-05\nBULLET::- URL : https://confluence.samsungds.net/pages/viewpage.action?pageId=3349871062\nBULLET::- FILE_URL : https://s3drive.samsungds.net/?namespace=org-scm_group-mem&bucket=goc_mail_1&folderPrefix=mail_eml%2F2026-03-05%2F20260304041556epcms2p4dfa6f42f609a326cd0e8ba7496363ebeBCC20260304223012813%2F\nBULLET::- S3 URI: s3://goc_mail_1/mail_eml/2026-03-05/20260304041556epcms2p4dfa6f42f609a326cd0e8ba7496363ebeBCC20260304223012813/■3_5(목) Global운영팀 일일근태_20260305_073000_4c1b3b3a.eml\nBULLET::- S3 KEY: mail_eml/2026-03-05/20260304041556epcms2p4dfa6f42f609a326cd0e8ba7496363ebeBCC20260304223012813/■3_5(목) Global운영팀","permission_groups":["rag-public"],"creator_id":"sungmook.cho","created_time":"2026-03-05T00:00:00.000+09:00"}

[RAG Search] Result from glossary_m3_100chunk50: {'took': 14, 'timed_out': False, '_shards': {'total': 1, 'successful': 1, 'skipped': 0, 'failed': 0}, 'hits': {'total': {'value': 3646, 'relation': 'eq'}, 'max_score': None, 'hits': [{'_index': 'glossary_dsglossary_m3_100chunk50_batch-000001', '_id': 'glossary_dsglossary_000YBDQLK_SCH_0002_000000', '_score': 0.016393442, '_rank': 1, '_source': {'doc_id': 'glossary_dsglossary_000YBDQLK_SCH_0002', 'created_time': '2025-09-19T03:51:25.668798+09:00', 'permission_groups': ['rag-public'], 'source_type': 'glossary', 'source_subtype': 'dsglossary', 'title': '고객 정보 파일', 'url': 'https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=000YBDQLK_SCH_0002', 'trees': ['판매', '고객대응', 'Account 관리'], 'tags': [''], 'hyperlinks': [], 'images': [], 'creator_id': 'duo', 'modifier_id': 'duo', 'modified_time': '2025-09-18T16:59:26+09:00', 'file_name': 'glossary_dsglossary_000YBDQLK_SCH_0002.json', 'chunk_id': 'glossary_dsglossary_000YBDQLK_SCH_0002_000000', 'statistics': {'byte_size': 525, 'token_count': 122, 'char_count': 255}, 'merge_title_content': '고객 정보 파일 [SEP] 고객 정보 파일  판매 고객대응 Account 관리 null 거래선에 대한 모든 정보를 정리해 놓은 파일이며 주요 내용은 거래선 개요, 연혁, 임원진, 조직도, Biz Revenue (연도별, 제품별 등), 특이사항 등을 정리하고, 당사의 거래선向 Biz Revenue(년도별, 제품별), 주요한 Biz 이슈 및 주요 구매관련 인력에 대한 약력을 간단히 정리하며방문/출장 회의전 사용하며, Word File 형태로 보관되어 있음.\n', 'indexed_time': '2026-02-07T04:12:32.202083+09:00'}}, {'_index': 'glossary_dsglossary_m3_100chunk50_batch-000001', '_id': 'glossary_dsglossary_000YBB5N6_SCH_0002_000000', '_score': 0.016393442, '_rank': 2, '_source': {'doc_id': 'glossary_dsglossary_000YBB5N6_SCH_0002', 'created_time': '2025-09-19T03:51:25.668798+09:00', 'permission_groups': ['rag-public'], 'source_type': 'glossary', 'source_subtype': 'dsglossary', 'title': 'F/O', 'url': 'https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=000YBB5N6_SCH_0002', 'trees': ['개발', 'FLASH_개발', ''], 'tags': [['반도체연구소']], 'hyperlinks': [], 'images': [], 'creator_id': 'duo', 'modifier_id': 'duo', 'modified_time': '2025-09-18T16:33:54+09:00', 'file_name': 'glossary_dsglossary_000YBB5N6_SCH_0002.json', 'chunk_id': 'glossary_dsglossary_000YBB5N6_SCH_0002_000000', 'statistics': {'byte_size': 77, 'token_count': 32, 'char_count': 57}, 'merge_title_content': 'F/O [SEP] F/O 개발 FLASH_개발 null null Fab out. WF를 꺼내오는것 -\n', 'indexed_time': '2026-02-07T04:24:45.081487+09:00'}}, {'_index': 'glossary_dsglossary_m3_100chunk50_batch-000001', '_id': 'glossary_dsglossary_000YBB5ZD_SCH_0002_000000', '_score': 0.016129032, '_rank': 3, '_source': {'doc_id': 'glossary_dsglossary_000YBB5ZD_SCH_0002', 'created_time': '2025-09-19T03:51:25.668798+09:00', 'permission_groups': ['rag-public'], 'source_type': 'glossary', 'source_subtype': 'dsglossary', 'title': 'RFP', 'url': 'https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=000YBB5ZD_SCH_0002', 'trees': ['인프라', 'Facility', 'Facility 시공'], 'tags': [['Facility팀_일반']], 'hyperlinks': [], 'images': [], 'creator_id': 'duo', 'modifier_id': 'duo', 'modified_time': '2025-09-18T16:33:43+09:00', 'file_name': 'glossary_dsglossary_000YBB5ZD_SCH_0002.json', 'chunk_id': 'glossary_dsglossary_000YBB5ZD_SCH_0002_000000', 'statistics': {'byte_size': 408, 'token_count': 102, 'char_count': 198}, 'merge_title_content': 'RFP [SEP] RFP 인프라 Facility Facility 시공 null 발주처가 공사를 담당할 업체를 최종적으로 선정하기 전에 선별된 업체에게 보내는 공사에 대한 요구사항을 체계적으로 정리한 문서이다. 당 사업장에서는 사급,도 급발주에 있어서 해당 발주에 대한 요구사항을 정리한 내용임. (Specification, 납기, 금액, 제반사항 等) -\n', 'indexed_time': '2026-02-07T04:24:42.016381+09:00'}}]}}
[RAG Search] Found 3 documents in glossary_m3_100chunk50
[RAG Search] Total results: 6
[RAG] 병렬 검색 완료: query=FLASH 이슈 사항 정리 해줘 docs=6
[RAG Domain Selection] selected_rag_domain=mail, glossary_intent=False, force_glossary=False, mail_match=True, glossary_match=False
[RAG Final] selected_rag_domain=mail used_rag=True fallback_reason=
[LLM PERF] total=13824ms init=690ms memory=691ms rewrite=1ms rag=906ms rerank=3ms llm=12060ms
[llm-worker-1][f6e9eaf5-cf74-490b-a7cd-f709c022c210] done queue_wait=0.03s total=13.85s rag_calls=1 llm_calls=1 used_rag=True memory_hit=True memory_message_count=6 memory_prompt_chars=1613 rewrite_used_memory=False fallback_reason= rpm=1@2026-03-06 08:03

청크 : CHUNK = ChunkFactor(logic="fixed_size", chunk_size=600, chunk_overlap=120, separator=" ")

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
