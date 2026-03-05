            year -= 1
            month = 12
        month_range = _get_month_range(year, month)
        if month_range:
            start, end = month_range
            return _mk("저번달", start, end)

    # 3) "최근 N일/최근 N주/최근 N개월" (rolling window)
    #    - 숫자 없이 "최근/요즘/근래/최근에"만 있으면 default 7일
    recent_tokens = ("최근", "요즘", "근래", "최근에")
    if any(tok in q_compact for tok in recent_tokens):
        # 예: 최근3일 / 최근 2주 / 최근 한달 / 요즘(=default)
        # 숫자: 1~3자리, 단위: 일/주/주일/개월/달
        m = re.search(r"(최근|요즘|근래|최근에)\s*(\d{1,3})?\s*(일|주|주일|개월|달)?", q_raw)
        n = None
        unit = None
        if m:
            if m.group(2):
                try:
                    n = int(m.group(2))
                except:
                    n = None
            unit = (m.group(3) or "").strip()

        # 기본값
        if n is None:
            n = 7
        if not unit:
            unit = "일"

        unit = unit.replace("주일", "주")
        unit = unit.replace("달", "개월")

        if unit == "일":
            delta = timedelta(days=n)
            label = f"최근 {n}일"
        elif unit == "주":
            delta = timedelta(days=7 * n)
            label = f"최근 {n}주"
        else:  # "개월"
            # 월은 정확한 일수로 환산이 애매해서 실무적으로 30일*n로 rolling 처리(캘린더월은 '이번달/저번달'로 이미 커버)
            delta = timedelta(days=30 * n)
            label = f"최근 {n}개월"

        end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        start = (end - delta).replace(hour=0, minute=0, second=0, microsecond=0)
        return _mk(label, start, end)

    return None


def _filter_docs_by_datetime_range(
    documents: List[Dict[str, Any]],
    start_dt: datetime,
    end_dt: datetime,
) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    for doc in documents:
        dt = _extract_doc_datetime(doc)
        if not dt:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("Asia/Seoul"))
        dt = dt.astimezone(ZoneInfo("Asia/Seoul"))
        if start_dt <= dt < end_dt:
            filtered.append(doc)
    return filtered


def rerank_rag_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not documents:
        return []
    merged: Dict[str, Dict[str, Any]] = {}
    for doc in documents:
        key = str(
            doc.get("doc_id")
            or doc.get("id")
            or doc.get("confluence_mail_page_url")
            or doc.get("url")
            or f"{doc.get('title','')}|{doc.get('_index','')}"
        )
        raw_score = float(doc.get("_score") or 0.0)
        if key not in merged:
            item = dict(doc)
            item["_query_hits"] = 1
            item["_vector_score"] = raw_score
            merged[key] = item
        else:
            merged[key]["_query_hits"] += 1
            if raw_score > float(merged[key].get("_vector_score") or 0.0):
                keep_hits = merged[key]["_query_hits"]
                item = dict(doc)
                item["_query_hits"] = keep_hits
                item["_vector_score"] = raw_score
                merged[key] = item
    docs = list(merged.values())
    max_vec = max([float(d.get("_vector_score") or 0.0) for d in docs] or [1.0])
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    for d in docs:
        vec = float(d.get("_vector_score") or 0.0)
        vec_norm = vec / max_vec if max_vec > 0 else 0.0
        dt = _extract_doc_datetime(d)
        if dt:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("Asia/Seoul"))
            age_days = max((now - dt.astimezone(ZoneInfo("Asia/Seoul"))).total_seconds() / 86400.0, 0.0)
            recency_score = max(
                RAG_MIN_RECENCY_SCORE,
                math.exp(-math.log(2) * age_days / max(RAG_RECENCY_HALF_LIFE_DAYS, 1.0))
            )
            d["_doc_date"] = dt.astimezone(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")
        else:
            recency_score = RAG_MIN_RECENCY_SCORE
            d["_doc_date"] = "날짜 정보 없음"
        query_hit_bonus = min(max(int(d.get("_query_hits") or 1) - 1, 0), 3) * 0.03
        combined_score = ((1 - RAG_RECENCY_WEIGHT) * vec_norm) + (RAG_RECENCY_WEIGHT * recency_score) + query_hit_bonus
        d["_vector_norm"] = round(vec_norm, 4)
        d["_recency_score"] = round(recency_score, 4)
        d["_combined_score"] = round(combined_score, 4)
    docs.sort(
        key=lambda x: (
            float(x.get("_combined_score", 0.0)),
            float(x.get("_vector_score", 0.0))
        ),
        reverse=True
    )
    return docs
RAG_MIN_COMBINED_SCORE = float(os.getenv("RAG_MIN_COMBINED_SCORE", str(RAG_SIMILARITY_THRESHOLD)))
RAG_MIN_KEYWORD_HITS = int(os.getenv("RAG_MIN_KEYWORD_HITS", "1"))

GENERAL_QUESTION_HINTS = [
    "날씨", "기온", "비와", "눈와", "환율", "주가", "뉴스", "시간", "몇시",
    "today", "weather", "temperature", "stock", "news", "time"
]

def _normalize_text_for_match(s: str) -> str:
    s = (s or "").lower().strip()
    for ch in [" ", "\n", "\t", ",", ".", ":", ";", "/", "\\", "(", ")", "[", "]", "{", "}", "-", "_", "?", "!"]:
        s = s.replace(ch, " ")
    return " ".join(s.split())

def _extract_query_keywords(question: str) -> List[str]:
    q = _normalize_text_for_match(question)
    toks = [t for t in q.split() if len(t) >= 2]
    stopwords = {
        "오늘", "어때", "뭐야", "알려줘", "조회", "관련", "대한", "the", "is", "are",
        "what", "when", "how", "why", "please"
    }
    return [t for t in toks if t not in stopwords]

def should_prefer_general_llm(question: str) -> bool:
    q = (question or "").lower()
    return any(h in q for h in GENERAL_QUESTION_HINTS)

def is_rag_result_relevant(question: str, top_docs: List[Dict[str, Any]]) -> bool:
    if not top_docs:
        return False

    top1 = top_docs[0]
    top_score = float(top1.get("_combined_score") or 0.0)

    title = str(top1.get("title") or "")
    content = str(top1.get("content") or top1.get("merge_title_content") or "")
    haystack = _normalize_text_for_match(title + " " + content)

    keywords = _extract_query_keywords(question)
    keyword_hits = sum(1 for kw in keywords if kw in haystack)

    # FW:/RE: 같은 전달메일성 제목은 약간 보수적으로
    noisy_title = title.strip().upper().startswith(("FW:", "RE:"))

    effective_threshold = max(RAG_SIMILARITY_THRESHOLD, RAG_MIN_COMBINED_SCORE)
    if top_score < effective_threshold:
        return False
    if keyword_hits < RAG_MIN_KEYWORD_HITS and noisy_title:
        return False
    if keywords and keyword_hits == 0:
        return False

    return True

# =========================
# Glossary RAG Helper Functions
# =========================
def is_glossary_doc(doc: Dict[str, Any]) -> bool:
    """문서가 glossary 인덱스에서 온 것인지 확인"""
    return doc.get("_index", "") == GLOSSARY_INDEX_NAME

def is_glossary_intent(question: str) -> bool:
    """
    용어형 질문인지 판별
    - 포함 키워드: 뜻, 의미, 정의, 약자, 무슨, 뭐야, 용어, 무슨뜻
    - 정규식: 영문 대문자 약어 (2~6자)
    - 패턴: 란, ~이란
    - 단, 메일성 요약 의도(이번주/저번주/정리/이슈)가 있으면 False
    """
    q = (question or "").strip()
    if not q:
        return False
    
    # 메일성 요약 의도가 강하면 False (메일 RAG 유지)
    mail_intent_keywords = ["이번주", "저번주", "지난주", "정리", "이슈"]
    q_compact = q.replace(" ", "")
    if any(kw in q_compact for kw in mail_intent_keywords):
        return False
    
    # 용어형 질문 키워드
    glossary_keywords = ["뜻", "의미", "정의", "약자", "무슨", "뭐야", "용어", "무슨뜻"]
    if any(kw in q for kw in glossary_keywords):
        return True
    
    # 영문 대문자 약어 패턴 (2~6자)
    if re.search(r"\b[A-Z]{2,6}\b", q):
        return True
    
    # "~란", "~이란" 패턴
    if re.search(r".?란\s*$", q) or re.search(r".?이란\s*$", q):
        return True
    
    return False

def is_glossary_result_relevant(
    question: str,
    docs: List[Dict[str, Any]],
    *,
    topk: int = 3,
    min_score: float = 0.38
) -> bool:
    """
    glossary 문서들에 대한 완화된 관련성 판정
    - topK 중 하나라도 키워드/약어가 매칭되면 True
    - 점수 조건은 완화 (min_score)
    """
    if not docs:
        return False
    
    # glossary 문서만 필터
    gdocs = [d for d in docs if is_glossary_doc(d)]
    if not gdocs:
        return False
    
    # 상위 topk 대상으로 검사
    target_docs = gdocs[:topk]
    
    # 질문에서 키워드 추출
    keywords = _extract_query_keywords(question)
    
    # 약어 추출 (영문 대문자 2~8자)
    abbreviations = re.findall(r"\b[A-Z]{2,8}\b", question)
    
    # 각 문서에 대해 키워드/약어 매칭 확인
    for doc in target_docs:
        title = str(doc.get("title") or "")
        content = str(doc.get("content") or doc.get("merge_title_content") or "")
        haystack = _normalize_text_for_match(title + " " + content)
        
        # 키워드 매칭 확인
        keyword_hits = sum(1 for kw in keywords if kw in haystack)
        if keyword_hits >= 1:
            return True
        
        # 약어 매칭 확인
        for abbr in abbreviations:
            if abbr in haystack:
                return True
        
        # 점수 조건 (완화된 threshold)
        combined_score = float(doc.get("_combined_score") or 0.0)
        if combined_score >= min_score:
            return True
    
    return False

def format_rag_context(documents: List[Dict[str, Any]], max_docs: int = 3) -> str:
    if not documents:
        return ""
    context_parts = []
    for i, doc in enumerate(documents[:max_docs], 1):
        title = doc.get("title", doc.get("doc_id", "")) or "제목 없음"
        content = doc.get("content", "") or doc.get("merge_title_content", "") or ""
        index = doc.get("_index", "")
        doc_date = doc.get("_doc_date", "날짜 정보 없음")
        combined = doc.get("_combined_score", doc.get("_score", 0))
        url = doc.get("confluence_mail_page_url", "") or doc.get("url", "")
        context_parts.append(
            f"[문서 {i}]\n"
            f"제목: {title}\n"
            f"문서일시: {doc_date}\n"
            f"종합점수: {combined}\n"
            f"인덱스: {index}\n"
            f"내용: {_truncate_text(content, 2200)}\n"
            f"출처: {url}"
        )
    return "\n\n".join(context_parts)


def retrieve_rag_documents_parallel(queries: List[str], *, top_k: int) -> List[Dict[str, Any]]:
    query_list = [q.strip() for q in queries if q and q.strip()]
    if not query_list:
        return []

    all_documents: List[Dict[str, Any]] = []
    max_workers = min(len(query_list), MAX_RAG_QUERIES, 2)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(search_rag_documents, query, top_k=top_k, mode=RAG_RETRIEVE_MODE): query
            for query in query_list
        }
        for future in as_completed(future_map):
            query = future_map[future]
            try:
                docs = future.result()
                print(f"[RAG] 병렬 검색 완료: query={query} docs={len(docs)}")
                all_documents.extend(docs)
            except Exception as e:
                print(f"[RAG] 병렬 검색 실패: query={query} err={e}")

    return all_documents


LLM_BUSY_MESSAGE = "지금 답변 생성 중입니다. 완료 후 다시 질문해주세요."
LLM_QUEUE_FULL_MESSAGE = "요청이 많아 잠시 후 다시 시도해주세요."
llm_job_queue: "queue.Queue[dict]" = queue.Queue(maxsize=LLM_JOB_QUEUE_MAX)
llm_task_state_lock = threading.Lock()
inflight: Dict[str, bool] = {}
inflight_lock = threading.Lock()
llm_sem = threading.Semaphore(LLM_MAX_CONCURRENT)
llm_workers_started = False
job_metrics_lock = threading.Lock()
job_metrics = {
    "minute": "",
    "count": 0,
}


def _mark_job_counter():
    now_minute = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")
    with job_metrics_lock:
        if job_metrics["minute"] != now_minute:
            job_metrics["minute"] = now_minute
            job_metrics["count"] = 0
        job_metrics["count"] += 1
        return job_metrics["minute"], job_metrics["count"]


def enqueue_llm_job(job: Dict[str, Any]) -> bool:
    try:
        llm_job_queue.put_nowait(job)
        qsize = llm_job_queue.qsize()
        print(f"[LLM][{job.get('request_id')}] enqueue ok qsize={qsize}")
        return True
    except queue.Full:
        print(f"[LLM][{job.get('request_id')}] enqueue failed queue full")
        return False


def _build_user_key(task: Dict[str, Any]) -> str:
    sender_knox = (task.get("sender_knox") or "").strip()
    sender_name = (task.get("sender_name") or "").strip()
    if sender_knox:
        return sender_knox
    if sender_name:
        return sender_name
    return str(task.get("chatroom_id"))


def llm_worker_loop(worker_name: str):
    while True:
        task = llm_job_queue.get()
        request_id = task.get("request_id")
        requested_at = float(task.get("requested_at") or time.time())
        dequeued_at = time.time()
        user_key = _build_user_key(task)

        with inflight_lock:
            if inflight.get(user_key):
                try:
                    chatBot.send_text(task["chatroom_id"], LLM_BUSY_MESSAGE)
                except Exception as send_err:
                    print(f"[{worker_name}][{request_id}] busy msg failed: {send_err}")
                print(f"[{worker_name}][{request_id}] dropped by inflight user_key={user_key}")
                llm_job_queue.task_done()
                continue
            inflight[user_key] = True

        rag_calls = 0
        llm_calls = 0
        used_rag = False
        fallback_reason = ""
        try:
            with llm_sem:
                minute, minute_count = _mark_job_counter()
                stats = process_llm_chat_background(task)
                rag_calls = int(stats.get("rag_calls", 0))
                llm_calls = int(stats.get("llm_calls", 0))
                used_rag = bool(stats.get("used_rag", False))
                fallback_reason = str(stats.get("fallback_reason", ""))
                total_latency = time.time() - requested_at
                queue_wait = dequeued_at - requested_at
                print(
                    f"[{worker_name}][{request_id}] done queue_wait={queue_wait:.2f}s total={total_latency:.2f}s "
                    f"rag_calls={rag_calls} llm_calls={llm_calls} used_rag={used_rag} "
                    f"fallback_reason={fallback_reason} rpm={minute_count}@{minute}"
                )
        except Exception as e:
            print(f"[{worker_name}][{request_id}] unexpected worker error: {e}")
        finally:
            with inflight_lock:
                inflight[user_key] = False
            llm_job_queue.task_done()


def start_llm_workers():
    global llm_workers_started
    if llm_workers_started:
        return

    with llm_task_state_lock:
        if llm_workers_started:
            return
        for idx in range(LLM_WORKERS):
            threading.Thread(
                target=llm_worker_loop,
                args=(f"llm-worker-{idx + 1}",),
                daemon=True,
                name=f"llm-worker-{idx + 1}",
            ).start()
        llm_workers_started = True

def build_search_queries(question: str, llm: ChatOpenAI) -> List[str]:
    sanitized_original = sanitize_query(question)
    if not sanitized_original:
        return []

    queries: List[str] = []
    if RAG_INCLUDE_ORIGINAL_QUERY:
        queries.append(sanitized_original)

    if ENABLE_QUERY_REWRITE and len(sanitized_original) > 12:
        rewritten = rewrite_search_queries(question, llm)
        for item in rewritten:
            sq = sanitize_query(item)
            if sq and sq not in queries:
                queries.append(sq)

    if not queries:
        queries = [sanitized_original]
    return queries[:MAX_RAG_QUERIES]


def _process_llm_chat_background_impl(task: Dict[str, Any]) -> Dict[str, Any]:
    chatroom_id = int(task["chatroom_id"])
    question = (task.get("question") or "").strip()
    sender_knox = task.get("sender_knox") or ""
    stats = {
        "rag_calls": 0,
        "llm_calls": 0,
        "used_rag": False,
        "fallback_reason": "",
    }

    try:
        user_id = sender_knox if sender_knox else "bot"
        llm = create_llm_chatbot(user_id)

        prefer_general = should_prefer_general_llm(question)
        if prefer_general:
            from langchain_core.messages import SystemMessage, HumanMessage

            fallback_system_prompt = """
당신은 GOC 업무 지원 챗봇입니다.
이번 질문은 일반 지식/실시간 성격의 질문으로 판단하여 문서 검색 없이 일반 LLM 답변으로 안내합니다.
과도한 추측은 피하고, 불확실한 내용은 단정하지 마세요.

답변 형식
📌 한줄 요약
한 문장 요약

✅ 일반 답변
- 핵심 내용 2~5개

⚠️ 참고
- 이번 답변은 문서 기반이 아니라 일반 답변임을 짧게 안내
"""
            messages = [
                SystemMessage(content=fallback_system_prompt),
                HumanMessage(content=question)
            ]
            response = llm_invoke_with_retry(llm, messages, attempts=3, base_delay=1.5)
            stats["llm_calls"] += 1
            stats["fallback_reason"] = "prefer_general"
            answer = "📋 문서 기반 답변 미적용\n- 일반 지식/실시간 성격의 질문으로 판단했습니다.\n- 아래는 일반 LLM 답변입니다.\n\n" + response.content.strip()
            chatBot.send_text(chatroom_id, f"🤖 {answer}")
            return stats

        search_queries = build_search_queries(question, llm)
        print(f"[RAG] search queries: {search_queries}")

        time_range = _extract_time_range_from_question(question)
        retrieve_top_k = RAG_NUM_RESULT_DOC
        if time_range:
            retrieve_top_k = max(RAG_NUM_RESULT_DOC, RAG_TEMPORAL_NUM_RESULT_DOC)

        all_rag_documents = retrieve_rag_documents_parallel(
            search_queries,
            top_k=retrieve_top_k,
        )
        stats["rag_calls"] = len(search_queries)

        if time_range:
            ranged_docs = _filter_docs_by_datetime_range(
                all_rag_documents,
                time_range["start"],
                time_range["end"],
            )
            if ranged_docs:
                print(
                    f"[RAG] 기간 필터 적용: {time_range['label']} "
                    f"{time_range['start']}~{time_range['end']} docs={len(ranged_docs)}"
                )
                all_rag_documents = ranged_docs
            else:
                print(
                    f"[RAG] 기간 필터 결과 없음, 원본 결과 사용: {time_range['label']} "
                    f"{time_range['start']}~{time_range['end']}"
                )

        reranked_docs = rerank_rag_documents(all_rag_documents)[:RAG_NUM_RESULT_DOC]
        top_docs = reranked_docs[:RAG_CONTEXT_DOCS]

        # =========================
        # 메일 우선 + Glossary 완화 로직
        # =========================
        # 문서 분리
        mail_docs = [d for d in top_docs if d.get("_index") == MAIL_INDEX_NAME]
        glossary_docs = [d for d in top_docs if d.get("_index") == GLOSSARY_INDEX_NAME]

        # 로깅용 변수
        selected_rag_domain = "none"
        glossary_intent = False
        glossary_match = False
        mail_match = False

        # 1) 메일 우선: 메일 문서가 있고 관련성이 높으면 메일 RAG 사용
        if mail_docs and is_rag_result_relevant(question, mail_docs):
            selected_rag_domain = "mail"
            mail_match = True
            rag_relevant = True
            rag_context = format_rag_context(mail_docs, max_docs=RAG_CONTEXT_DOCS)
        # 2) 용어형 질문이고 glossary 문서가 있으면 완화된 기준으로 glossary RAG 사용
        elif GLOSSARY_RAG_ENABLE and is_glossary_intent(question) and glossary_docs:
            selected_rag_domain = "glossary"
            glossary_intent = True
            glossary_match = is_glossary_result_relevant(
                question,
                glossary_docs,
                topk=GLOSSARY_TOPK_MATCH,
                min_score=GLOSSARY_RELAXED_THRESHOLD
            )
            rag_relevant = glossary_match
            rag_context = format_rag_context(glossary_docs, max_docs=RAG_CONTEXT_DOCS) if glossary_match else ""
        # 3) 기존 로직 유지 (fallback)
        else:
            top_score = float(top_docs[0].get("_combined_score") or 0.0) if top_docs else 0.0
            skip_rag = top_score < RAG_SIMILARITY_THRESHOLD
            rag_relevant = (not skip_rag) and is_rag_result_relevant(question, top_docs)
            rag_context = format_rag_context(top_docs, max_docs=RAG_CONTEXT_DOCS) if rag_relevant else ""

        # 로그 출력
        print(f"[RAG Domain Selection] selected_rag_domain={selected_rag_domain}, "
              f"glossary_intent={glossary_intent}, glossary_match={glossary_match}, mail_match={mail_match}")

        if rag_context and rag_relevant:
            from langchain_core.messages import SystemMessage, HumanMessage
            stats["used_rag"] = True

            system_prompt = f"""
                당신은 GOC 업무 지원 챗봇입니다.

                최우선 규칙
                1) 아래 [검색 문서]에 있는 내용만을 근거로 "📂 문서 기반 답변"을 작성하세요. (추측/일반상식/외부지식 금지)
                2) 문서에 없는 내용은 반드시 "문서에 해당 정보가 없습니다."라고 명시하세요.
                3) 질문에 기간(이번주/저번주/지난주/오늘/어제/최근N일)이 포함되면, 답변 첫 줄 또는 요약에 적용한 기간을 반드시 명시하세요.
                4) 질문에 기간 지정이 없으면, 검색 문서 중 "가장 최신 문서일시"를 기준으로 답변하고, 그 기준 문서일시를 명시하세요.
                5) 문서 간 내용이 다르면 가장 최신 문서를 우선하고, "문서 간 상충"이라고 표시하세요.
                6) "💡 AI 의견"은 참고용 보충설명만 가능하며, 문서 사실처럼 단정하지 마세요. 문서와 충돌하면 문서가 항상 우선입니다.

                [검색 문서]
                {rag_context}

                출력 형식(아래 순서/제목을 반드시 그대로 유지)
                📌 한줄 요약
                - (기간/기준일시 포함 1문장)

                📂 문서 기반 답변
                - 핵심 사실 2~5개 (각 항목에 가능한 경우 날짜/수량/조직/대상 포함)
                - 문서에 없는 부분은 "문서에 해당 정보가 없습니다."로 표시

                💡 AI 의견
                - (참고용) 해석/실무적 의미 1~3개
                - 단정 금지(“~일 수 있습니다/권장합니다/확인 필요”)

                📂 근거 문서
                - 1) {'문서명'} | {'문서일시'} | {'근거한줄'} | {'링크'}
                - 2) ...
                (최대 3개)

                ⚠️ 주의
                - "📂 문서 기반 답변"은 문서에 있는 사실만, "💡 AI 의견"은 참고용입니다.

                🔗 이슈지 바로가기 👉 https://go/issueG
            """

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=question)]
            response = llm_invoke_with_retry(llm, messages, attempts=3, base_delay=1.5)
            stats["llm_calls"] += 1
            answer = response.content.strip()

            if "📂 근거 문서" not in answer:
                source_lines = []
                for doc in top_docs[:3]:
                    title = doc.get("title", "제목 없음")
                    doc_date = doc.get("_doc_date", "날짜 정보 없음")
                    url = doc.get("confluence_mail_page_url", "") or doc.get("url", "")
                    line = f"- {title} | {doc_date}"
                    if url:
                        line += f"\n  🔗 GO LINK: {url}"
                    source_lines.append(line)
                if source_lines:
                    answer += "\n\n📂 근거 문서\n" + "\n".join(source_lines)
        else:
            from langchain_core.messages import SystemMessage, HumanMessage
            fallback_system_prompt = """
당신은 GOC 업무 지원 챗봇입니다.
이번 질문은 문서 검색 결과가 없거나 관련성이 낮아 일반 LLM 답변으로 안내합니다.
과도한 추측은 피하고, 불확실한 내용은 단정하지 마세요.
"""
            messages = [SystemMessage(content=fallback_system_prompt), HumanMessage(content=question)]
            response = llm_invoke_with_retry(llm, messages, attempts=3, base_delay=1.5)
            stats["llm_calls"] += 1

            reason = "관련 문서를 찾지 못했습니다."
            if skip_rag:
                reason = f"검색 문서 유사도가 기준치({RAG_SIMILARITY_THRESHOLD})보다 낮았습니다."
            elif top_docs and not rag_relevant:
                reason = "검색 문서는 있었지만 질문과의 관련성이 낮았습니다."
            stats["fallback_reason"] = reason
            answer = f"📋 문서 기반 답변 미적용\n- {reason}\n- 아래는 일반 LLM 답변입니다.\n\n" + response.content.strip()

        chatBot.send_text(chatroom_id, f"🤖 {answer}")
        return stats

    except Exception as e:
        print(f"[LLM Background Error] {e}")
        import traceback
        traceback.print_exc()
        stats["fallback_reason"] = f"error:{e}"
        try:
            chatBot.send_text(chatroom_id, f"LLM 응답 오류: {e}")
        except Exception as send_err:
            print("[send error message failed]", send_err)
        return stats


def process_llm_chat_background(task: Dict[str, Any]) -> Dict[str, Any]:
    return _process_llm_chat_background_impl(task)

def rewrite_search_queries(question: str, llm: ChatOpenAI) -> List[str]:
    """
    LLM을 사용하여 질문을 검색 최적화 질의로 재작성
    
    Args:
        question: 사용자 질문
        llm: LLM 인스턴스
    
    Returns:
        재작성된 검색 질의 목록 (최대 2개)
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    
    system_prompt = """사용자의 질문을 문서 검색에 최적화된 질의로 재작성하세요.
다음 조건을 반영하여 정확히 2개의 검색 질의를 생성하세요:
1. 핵심 키워드 추출
2. 동의어/업무용 표현 보강
3. 너무 긴 문장은 짧은 검색 질의로 축약

각 질의는 줄바꿈으로 구분하세요. 다른 설명은 하지 마세요.

예시:
질문: "Apple의 공급망 투입 현황 알려줘"
답변:
Apple 공급망 투입 현황
Apple supply chain investment

질문: "삼성전자의 최신 반도체 생산량은?"
답변:
삼성전자 반도체 생산량
Samsung semiconductor production volume"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question)
    ]
    
    try:
        response = llm_invoke_with_retry(llm, messages, attempts=2, base_delay=1.0)
        queries_text = response.content.strip()
        queries = []
        for q in queries_text.split('\n'):
            normalized = q.strip()
            if normalized and normalized not in queries:
                queries.append(normalized)

        if not queries:
            return [question]
        if len(queries) == 1:
            return [queries[0], question] if queries[0] != question else [question]
        return queries[:RAG_REWRITE_QUERY_COUNT]
    except Exception as e:
        print(f"[Query Rewrite Error] {e}")
        return [question]


# =========================
# 3) Action Parsing
# =========================
def _extract_group_llm_question(txt: str) -> str:
    text = (txt or "").strip()
    if not text:
        return ""
    mention = (LLM_GROUP_MENTION_TEXT or "").strip()
    if mention and text.startswith(mention):
        return text[len(mention):].strip(" :")

    for prefix in LLM_GROUP_PREFIXES:
        pfx = prefix.strip()
        if not pfx:
            continue
        if text.startswith(pfx):
            return text[len(pfx):].strip(" :")
        if text.startswith(pfx + ",") or text.startswith(pfx + ":"):
            return text[len(pfx)+1:].strip()
    return ""


def parse_action_payload(info: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    chat_msg = info.get("chatMsg", "") or ""
    raw = chat_msg
    if " -->" in chat_msg:
        parts = chat_msg.split(" -->", 1)
        raw = parts[1].strip()

    # 1) 버튼/카드 payload(JSON) 우선
    if raw.strip().startswith("{"):
        try:
            payload = json.loads(raw)
            action = payload.get("action", "HOME")
            return action, payload
        except Exception:
            pass

    txt = raw.strip()
    txt_u = txt.upper()
    chat_type = (info.get("chatType") or "").upper()

    # 2) 시스템 트리거 우선
    if txt_u in ("INTRO", "HOME") or txt in ("홈", "/home"):
        return "INTRO", {}
    if txt in ("바로가기", "/바로가기", "링크", "/links", "links"):
        return "QUICK_LINKS", {}

    # 3) SINGLE 단축키 OPEN_URL
    if chat_type == "SINGLE":
        key = txt_u[1:] if txt_u.startswith("/") else txt_u
        title, url = resolve_quick_link(key)
        if url:
            return "OPEN_URL", {"title": title, "url": url}

    # 4) 명령어
    if txt.startswith("/warn"):
        return "WARN_RUN", {}
    if txt.startswith("/issue"):
        return "ISSUE_FORM", {}

    # 5) LLM 라우팅
    if chat_type == "SINGLE":
        if txt.startswith("/ask "):
            return "LLM_CHAT", {"question": txt[5:].strip()}
        if txt.startswith("질문:"):
            return "LLM_CHAT", {"question": txt[3:].strip()}
        if not txt.startswith("/"):
            return "LLM_CHAT", {"question": txt}
        return "NOOP", {}

    if chat_type == "GROUP":
        if LLM_CHAT_DEFAULT_MODE == "all" and not txt.startswith("/"):
            return "LLM_CHAT", {"question": txt}
        if LLM_CHAT_DEFAULT_MODE == "mention":
            q = _extract_group_llm_question(txt)
            if q:
