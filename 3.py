                return "LLM_CHAT", {"question": q}
        return "NOOP", {}

    return "NOOP", {}



# =========================
# 4) UI-state helpers (recall 카드)
# =========================
def extract_msgid_senttime(resp: dict):
    if not isinstance(resp, dict):
        return None, None

    pme = resp.get("processedMessageEntries")
    if isinstance(pme, list) and pme:
        x = pme[0] or {}
        mid = x.get("msgId")
        st  = x.get("sentTime")
        if mid is not None and st is not None:
            try:
                return int(mid), int(st)
            except:
                return mid, st

    for k in ("chatReplyResultList", "chatReplyResults", "resultList", "data", "results"):
        v = resp.get(k)
        if isinstance(v, list) and v:
            x = v[0] or {}
            mid = x.get("msgId") or x.get("messageId") or x.get("msgID")
            st  = x.get("sentTime") or x.get("sendTime") or x.get("sent_time")
            if mid is not None and st is not None:
                try:
                    return int(mid), int(st)
                except:
                    return mid, st

    mid = resp.get("msgId") or resp.get("messageId") or resp.get("msgID")
    st  = resp.get("sentTime") or resp.get("sendTime") or resp.get("sent_time")
    if mid is not None and st is not None:
        try:
            return int(mid), int(st)
        except:
            return mid, st

    return None, None


def send_issue_list_card(chatroom_id: int, issues: List[dict], *, scope_room_id: str, recall_prev: bool = True):
    if chatBot is None:
        print("[send_issue_list_card] KNOX 연결 안됨")
        return
    
    if recall_prev and ENABLE_RECALL:
        st = store.ui_get_issue_list_state(str(chatroom_id))
        if st and st.get("issue_list_msg_id") and st.get("issue_list_sent_time"):
            try:
                chatBot.recall_message(chatroom_id, int(st["issue_list_msg_id"]), int(st["issue_list_sent_time"]))
            except Exception as e:
                print("[recall issue_list card failed]", e)

        # ✅ D-day 계산 + 정렬(목표일 임박순) 보장
    for it in issues:
        it["d_day"] = store._dday(it.get("target_date", ""))

    issues.sort(key=lambda x: (999999 if x.get("d_day") is None else x.get("d_day"), int(x.get("issue_id", 0))))

    resp = chatBot.send_adaptive_card(chatroom_id, ui.build_issue_list_card(issues, room_id=str(scope_room_id)))

    mid, sent = extract_msgid_senttime(resp)
    if mid and sent:
        store.ui_set_issue_list_state(str(chatroom_id), mid, sent)


def send_issue_history_card(chatroom_id: int, *, scope_room_id: str, page: int, recall_prev: bool = False):
    if chatBot is None:
        print("[send_issue_history_card] KNOX 연결 안됨")
        return
    
    if recall_prev and ENABLE_RECALL:
        st = store.ui_get_history_state(str(chatroom_id))
        if st and st.get("history_msg_id") and st.get("history_sent_time"):
            try:
                chatBot.recall_message(chatroom_id, int(st["history_msg_id"]), int(st["history_sent_time"]))
            except Exception as e:
                print("[recall history card failed]", e)

    total = store.issue_count_all(str(scope_room_id))
    max_page = max(0, (total - 1) // store.HISTORY_PAGE_SIZE) if total > 0 else 0
    page = max(0, min(int(page), max_page))

    issues = store.issue_list_all_paged(str(scope_room_id), page, store.HISTORY_PAGE_SIZE)
    resp = chatBot.send_adaptive_card(
        chatroom_id,
        ui.build_issue_history_card(issues, page=page, total=total, page_size=store.HISTORY_PAGE_SIZE, room_id=str(scope_room_id))
    )

    mid, sent = extract_msgid_senttime(resp)
    if mid is not None and sent is not None:
        store.ui_set_history_state(str(chatroom_id), mid, sent)


# =========================
# 5) Oracle Query runner
# =========================
def run_oracle_query(sql: str, params: Optional[dict] = None) -> pd.DataFrame:
    dsn = cx_Oracle.makedsn(ORACLE_HOST, ORACLE_PORT, service_name=ORACLE_SERVICE)
    con = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PW, dsn=dsn, encoding="UTF-8")
    try:
        return pd.read_sql(sql, con, params=params)
    finally:
        try:
            con.close()
        except Exception:
            pass

# (추가 코드 - 추가용)  ※ run_oracle_query 아래쪽에 추가
def _likeify2(v: str) -> str:
    v = (v or "").strip()
    if not v:
        return ""
    return v if ("%" in v or "_" in v) else f"%{v}%"

def _ym6(s: str) -> str:
    s = "".join([c for c in (s or "") if c.isdigit()])
    return s[:6] if len(s) >= 6 else s

def run_oneview_ship(params: dict) -> pd.DataFrame:
    smon = _ym6(params.get("smon",""))
    emon = _ym6(params.get("emon",""))
    conv = (params.get("conv") or "deliverynum01").strip()
    qraw = (params.get("q") or "").strip()

    q = _likeify2(qraw.upper().replace(" ", ""))

    filter_map = {
        "deliverynum01": "a.DLVRY_NUM LIKE :q",
        "haitem01":      "a.SALE_ITEM_CODE LIKE :q",
        "haversion01":   "(b.DRAMVER LIKE :q OR b.NANDVER LIKE :q)",
        "hagc01":        "(a.GC_CODE LIKE :q OR a.GC_NAME LIKE :q)",
    }
    filter_clause = filter_map.get(conv, filter_map["deliverynum01"])

    sql = ui.SQL_ONEVIEW_SHIP_BASE.format(filter_clause=filter_clause)
    return run_oracle_query(sql, params={"smon": smon, "emon": emon, "q": q})

def run_pkgcode(params: dict) -> pd.DataFrame:
    raw = (params.get("q") or "").strip()
    q = raw.upper().replace(" ", "")

    like_q = _likeify2(q)

    # ✅ 입력에 따라 where_clause 분기 (원본 로직 그대로)
    if q.isalpha() and len(q) == 2:
        where_clause = "B.VERSION LIKE :q"
    elif len(q) == 3:
        where_clause = "A.PACK_CODE LIKE :q"
    else:
        where_clause = "(A.PACK_CODE||B.VERSION||B.PCBCODE) LIKE :q"

    sql = ui.SQL_PKGCODE_BASE.format(where_clause=where_clause)
    return run_oracle_query(sql, params={"q": like_q})


# (추가 코드 - 교체/추가용)
from difflib import SequenceMatcher

def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a or "", b or "").ratio()

def _clean_xa0(x):
    if isinstance(x, str):
        return x.replace("\xa0", " ")
    if isinstance(x, list):
        return [_clean_xa0(v) for v in x]
    if isinstance(x, dict):
        return {k: _clean_xa0(v) for k, v in x.items()}
    return x

def run_term_search(params: dict):
    q = (params.get("q") or "").strip()
    if not q:
        return ui.build_term_not_found_card(q)

    try:
        with open(TERM_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        data = _clean_xa0(data)
    except Exception:
        # 파일 못 읽으면 안내 카드
        return ui.build_term_not_found_card(q)

    qn = q.lower().replace(" ", "")

    exact = []
    starts = []
    scored = []

    for item in (data or []):
        term = (item.get("title") or "").strip()
        if not term:
            continue
        tn = term.lower().replace(" ", "")
        sim = _sim(tn, qn)

        rec = {
            "subject": (item.get("subject") or "").strip(),
            "term": term,
            "content": (item.get("content") or "").strip(),
            "link": (item.get("link") or "").strip(),
        }

        if term == q:
            exact.append((sim, rec))
        elif term.startswith(q):
            starts.append((sim, rec))
        elif qn in tn:
            scored.append((sim, rec))
        else:
            # 완전 불일치일 때도 유사도 높은 것 일부 포함(너무 낮으면 제외)
            if sim >= 0.70:
                scored.append((sim, rec))

    # 정렬/컷
    exact = sorted(exact, key=lambda x: x[0], reverse=True)[:5]
    starts = sorted(starts, key=lambda x: x[0], reverse=True)[:5]
    scored = sorted(scored, key=lambda x: x[0], reverse=True)[:9]

    merged = [r for _, r in (exact + starts + scored)]

    # 중복 제거(term+link 기준)
    seen = set()
    uniq = []
    for r in merged:
        key = (r.get("term",""), r.get("link",""))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)

    if not uniq:
        return ui.build_term_not_found_card(q)

    return ui.build_term_search_results_card(q, uniq)

def run_ps_query(params: dict) -> pd.DataFrame:
    """
    PS 파트조회 공용 러너
    - gubun: pscomp01 / psmodule01 / psmultichip01
    - conv : psfab02 / pseds03 / psasy04 / pstst05 / psmod06(모듈전용)
    - q    : 검색값
    """
    gubun = (params.get("gubun") or params.get("psgubun01") or "").strip()   # 구분
    conv  = (params.get("conv")  or params.get("psconv01")  or "").strip()   # 조회기준
    qraw  = (params.get("q")     or params.get("result")    or "").strip()   # 검색어

    if not qraw:
        return pd.DataFrame([{"Result": "코드 입력값이 비었습니다."}])
    if len(qraw.strip()) < 3:
        return pd.DataFrame([{"Result": "코드는 3자 이상 입력하세요."}])

    # ✅ MOD_CODE는 MODULE에서만 허용
    if conv == "psmod06" and gubun != "psmodule01":
        return pd.DataFrame([{"Result": "MOD_CODE(psmod06)는 MODULE에서만 조회 가능합니다."}])

    # ✅ 입력 normalize + like 처리 (바인딩)
    q = _likeify2(qraw.upper().replace(" ", ""))

    # ✅ gubun별 SQL 선택 + where 컬럼 맵(예전 코드와 동일한 컬럼들)
    if gubun == "pscomp01":
        sql = getattr(ui, "SQL_PS_COMP_BASE", "") or ""
        where_map = {
            "psfab02": "A.FOUT_CODE LIKE :q",
            "pseds03": "A.EFU_CODE  LIKE :q",
            "psasy04": "A.ABD_CODE  LIKE :q",
            "pstst05": "A.TFN_CODE  LIKE :q",
        }
        default_conv = "pseds03"

    elif gubun == "psmodule01":
        sql = getattr(ui, "SQL_PS_MODULE_BASE", "") or ""
        where_map = {
            "psfab02": "B.FAB_CODE  LIKE :q",
            "pseds03": "B.EFU_CODE  LIKE :q",
            "psasy04": "B.ABD_CODE  LIKE :q",
            "pstst05": "A.COMPCODE  LIKE :q",
            "psmod06": "A.PRODCODE  LIKE :q",
        }
        default_conv = "pseds03"

    elif gubun == "psmultichip01":
        sql = getattr(ui, "SQL_PS_MCP_BASE", "") or ""
        where_map = {
            "psfab02": "B.FOUT_CODE LIKE :q",
            "pseds03": "A.CHIPCODE  LIKE :q",
            "psasy04": "A.PRODCODE  LIKE :q",
            "pstst05": "C.TFN_CODE  LIKE :q",
        }
        default_conv = "pseds03"

    else:
        return pd.DataFrame([{"Result": f"알 수 없는 gubun: {gubun}"}])

    if not (sql or "").strip():
        return pd.DataFrame([{"Result": f"PS SQL이 비어있음: ui SQL 정의 확인 (gubun={gubun})"}])

    # ✅ conv가 이상하면 기본값으로
    where_clause = where_map.get(conv) or where_map.get(default_conv) or ""

    # ✅ SQL에 {where_clause}가 있으면 채워줌(없으면 그대로 실행)
    if "{where_clause}" in sql:
        sql = sql.format(where_clause=where_clause)

    return run_oracle_query(sql, params={"q": q})


# 기존 RUNNERS가 있으면 아래만 추가, 없으면 RUNNERS 선언 후 추가


RUNNERS: Dict[str, Any] = {}
RUNNERS["TERM_SEARCH"] = run_term_search
RUNNERS["ONEVIEW_SHIP"] = run_oneview_ship
RUNNERS["PKGCODE"] = run_pkgcode
RUNNERS["PS_QUERY"] = run_ps_query

llm_allowed_users_cache_lock = threading.Lock()
llm_allowed_users_cache: set[str] = set()
llm_allowed_users_cache_expire_at = 0.0


def _normalize_sender_knox_id(sender_knox: str) -> str:
    return (sender_knox or "").strip().lower()


def _fetch_llm_allowed_users() -> set[str]:
    if not (LLM_ALLOWED_USERS_SQL or "").strip():
        return set()

    df = run_oracle_query(LLM_ALLOWED_USERS_SQL)
    if df is None or df.empty:
        return set()

    target_col = None
    for col in df.columns:
        if str(col).lower() in ("senderknoxid", "sso_id", "ssoid"):
            target_col = col
            break
    if target_col is None:
        target_col = df.columns[0]

    allowed_users = set()
    for value in df[target_col].dropna().tolist():
        normalized = _normalize_sender_knox_id(str(value))
        if normalized:
            allowed_users.add(normalized)
    return allowed_users


def is_llm_allowed_user(sender_knox: str) -> bool:
    global llm_allowed_users_cache_expire_at

    normalized = _normalize_sender_knox_id(sender_knox)
    if not normalized:
        return False

    now_ts = time.time()
    with llm_allowed_users_cache_lock:
        if now_ts < llm_allowed_users_cache_expire_at:
            return normalized in llm_allowed_users_cache

    try:
        allowed_users = _fetch_llm_allowed_users()
    except Exception as e:
        print(f"[LLM allowlist load failed] {e}")
        return False

    expire_at = now_ts + LLM_ALLOWED_USERS_CACHE_TTL_SEC
    with llm_allowed_users_cache_lock:
        llm_allowed_users_cache.clear()
        llm_allowed_users_cache.update(allowed_users)
        llm_allowed_users_cache_expire_at = expire_at
        return normalized in llm_allowed_users_cache

def run_rightperson(params: dict) -> pd.DataFrame:
    q = (params.get("q") or "").strip()
    if not q:
        return pd.DataFrame([{"Result": "검색어를 입력하세요."}])

    # 1) Oracle
    df_oracle = run_oracle_query(ui.SQL_RIGHTPERSON_ORACLE)

    # 2) JSON (옵션)
    df_json = pd.DataFrame()
    if RIGHTPERSON_JSON_URL:
        try:
            r = requests.get(RIGHTPERSON_JSON_URL, timeout=5)
            r.raise_for_status()
            df_json = pd.DataFrame(r.json())
        except Exception:
            df_json = pd.DataFrame()

    cols = ["부서","담당제품","팀장","PL","TL","실무담당자","비고"]
    for df in (df_oracle, df_json):
        for c in cols:
            if c not in df.columns:
                df[c] = ""

    combined = pd.concat([df_json[cols], df_oracle[cols]], ignore_index=True)

    mask = (
        combined["부서"].astype(str).str.contains(q, case=False, na=False) |
        combined["담당제품"].astype(str).str.contains(q, case=False, na=False) |
        combined["팀장"].astype(str).str.contains(q, case=False, na=False) |
        combined["PL"].astype(str).str.contains(q, case=False, na=False) |
        combined["TL"].astype(str).str.contains(q, case=False, na=False) |
        combined["실무담당자"].astype(str).str.contains(q, case=False, na=False) |
        combined["비고"].astype(str).str.contains(q, case=False, na=False)
    )

    out = combined[mask].drop_duplicates().reset_index(drop=True)
    return out if not out.empty else pd.DataFrame([{"Result": f"검색 결과 없음: {q}"}])

RUNNERS["RIGHTPERSON"] = run_rightperson
# =========================
# 6) Sender userID / DM room
# =========================
def get_sender_user_id(info: dict) -> str | None:
    for k in ("senderUserId", "senderUserID", "senderUid", "senderId"):
        v = info.get(k)
        if v:
            return str(v)

    sk = (info.get("senderKnoxId") or "").strip()
    if sk.isdigit():
        return sk

    if sk:
        try:
            if chatBot is not None:
                ids = chatBot.resolve_user_ids_from_loginids([sk])
                if ids:
                    return str(ids[0])
        except:
            pass
    return None


def get_or_create_dm_room_for_user(
    sender_user_id: str,
    sender_name: str = "",
    *,
    chat_type: str | None = None,
    current_room_id: int | None = None,
) -> int | None:
    # ✅ 안전장치: SINGLE 컨텍스트면 "새로 만들지 말고" 현재 방을 DM으로 바인딩
    ct = (chat_type or "").upper()
    if ct == "SINGLE" and current_room_id:
        try:
            store.dm_set_room(sender_user_id, str(current_room_id))
        except Exception as e:
            print("[DM bind failed]", e)
        return int(current_room_id)

    cached = store.dm_get_room(sender_user_id)
    if cached:
        return int(cached)

    try:
        if chatBot is None:
            return None
        title = f"공급망봇 · {sender_name}".strip() if sender_name else None
        rid = chatBot.room_create([str(sender_user_id)], chatType=1, chatroom_title=title)
        store.dm_set_room(sender_user_id, str(rid))
        return int(rid)
    except Exception as e:
        print("[DM create failed]", e)
        return None


# ✅ (추가) 단체방에서 눌러도 UI/결과는 DM으로 보내는 라우터
def route_ui_room(chatroom_id: int, info: dict, sender_name: str = "") -> int:
    sender_user_id = get_sender_user_id(info)
    try:
        if (info.get("chatType") or "").upper() == "SINGLE" and sender_user_id:
            store.dm_set_room(str(sender_user_id), str(chatroom_id))  # ← 네 store 함수명에 맞춰 조정
    except Exception as e:
        print("[dm_room bind failed]", e)
    # ✅ SINGLE(1:1)은 원래 방에서 바로 응답
    chat_type = (info.get("chatType") or "").upper()
    if chat_type == "SINGLE":
        return chatroom_id

    # ✅ 단체방에서만 DM 라우팅
    if chat_type != "GROUP":
        return chatroom_id
    if not sender_user_id:
        return chatroom_id

    dm_room = get_or_create_dm_room_for_user(
    sender_user_id,
    sender_name,
    chat_type=chat_type,
    current_room_id=chatroom_id,
)

    return int(dm_room) if dm_room else chatroom_id



# =========================
# 7) Scheduler Jobs
# =========================
def job_issue_deadline_reminder_daily():
    today = datetime.now().date()
    issues = store.issue_list_open_all()
    if not issues:
        return

    to_send: Dict[str, List[Tuple[int, dict, str]]] = {}

    for it in issues:
        td = store._parse_ymd(it.get("target_date", ""))
        if not td:
            continue
        d = (td - today).days
        if d not in store.REMIND_DAYS:
            continue

        memo = f"D-{d}|{today.isoformat()}"
        if store.issue_event_exists(int(it["issue_id"]), "REMIND", memo):
            continue

        room = str(it.get("chatroom_id", "")).strip()
        if not room:
            continue

        to_send.setdefault(room, []).append((d, it, memo))

    if not to_send:
        return

    for room, items in to_send.items():
        try:
            if chatBot is None:
                print("[job_issue_deadline_reminder_daily] KNOX 연결 안됨, 건너뜀")
                continue
            items.sort(key=lambda x: (x[0], int(x[1]["issue_id"])))
            today_str = today.strftime("%Y-%m-%d")
            card = ui.build_issue_deadline_reminder_card([(d, it) for d, it, _memo in items], today_str)
            chatBot.send_adaptive_card(int(room), card)

            for _d, it, _memo in items:
                store.issue_event_add(int(it["issue_id"]), "REMIND", actor="BOT", memo=_memo)

        except Exception as e:
            print("job_issue_deadline_reminder_daily error:", e)


def job_warning_daily():
    rooms = store.get_watch_rooms()
    if not rooms:
        return

    try:
        if chatBot is None:
            print("[job_warning_daily] KNOX 연결 안됨, 건너뜀")
            return
        df = run_oracle_query(ui.SQL_WARN)
        msg = "⚠️ [워닝 테스트]\n" + ui.format_df_brief(df, 5)
        for rid in rooms:
            chatBot.send_text(int(rid), msg)
    except Exception as e:
        print("job_warning_daily error:", e)


# (바로 위 코드)
KR_HOLIDAYS = holidays.KR()  # 대한민국 공휴일(대체공휴일 포함)

def job_issue_summary_daily():
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    today = now.date()

    # ✅ 토/일 + 공휴일 스킵
    if today.weekday() >= 5 or today in KR_HOLIDAYS:  # 5=토, 6=일
        return

    rooms = store.get_watch_rooms()
    if not rooms:
        return

    try:
        if chatBot is None:
            print("[job_issue_summary_daily] KNOX 연결 안됨, 건너뜀")
            return
        today_str = now.strftime("%Y-%m-%d")

        for rid in rooms:
            issues = store.issue_list_open(str(rid))
            if not issues:
                continue

            for it in issues:
                it["d_day"] = store._dday(it.get("target_date", ""))

            issues.sort(key=lambda x: (
                999999 if x.get("d_day") is None else x.get("d_day"),
                int(x.get("issue_id", 0))
            ))

            card = ui.build_issue_summary_card(issues, today_str=today_str, max_items=15)
            chatBot.send_adaptive_card(int(rid), card)

    except Exception as e:
        print("job_issue_summary_daily error:", e)

def run_warning_once_to_chatroom(chatroom_id: int):
    if chatBot is None:
        print("[run_warning_once_to_chatroom] KNOX 연결 안됨")
        return
    df = run_oracle_query(ui.SQL_WARN)
    if df is None or df.empty:
        chatBot.send_text(chatroom_id, "워닝 조건: 현재 0건 ✅")
    else:
        chatBot.send_text(chatroom_id, "⚠️ 워닝 결과\n" + ui.format_df_brief(df, 10))


# =========================
# 8) FastAPI App
# =========================
app = FastAPI()
scheduler = BackgroundScheduler(timezone="Asia/Seoul")
chatBot: KnoxMessenger  # startup에서 초기화

@app.get("/api/dashboard/rooms")
def api_dashboard_rooms(token: str | None = Query(default=None)):
    _require_dashboard_token(token)
    return {"rooms": store.list_watch_rooms()}

@app.get("/api/dashboard/summary")
def api_dashboard_summary(
    token: str | None = Query(default=None),
### PART 3/3
    room_id: str | None = Query(default=None),
):
    _require_dashboard_token(token)

    today = store._today()
    open_issues = store.issue_list_open_all()
    closed_recent = store.issue_list_closed_recent(days=60)

    if room_id:
        open_issues = [x for x in open_issues if str(x.get("chatroom_id","")) == str(room_id)]

    last_map = store.get_last_activity_map([int(x["issue_id"]) for x in open_issues])

    overdue = 0
    due_7 = 0
    due_3 = 0
    no_target = 0
    long_open_14 = 0
    owner_cnt = defaultdict(int)

    urgent_list = []
    old_list = []
    stale_list = []

    for it in open_issues:
        d = store._dday(it.get("target_date",""))
        age = store._age_days(it.get("created_at",""))
        owner = (it.get("owner") or "").strip() or "(미지정)"
        owner_cnt[owner] += 1

        if d is None:
            no_target += 1
        else:
            if d < 0:
                overdue += 1
            if 0 <= d <= 7:
                due_7 += 1
            if 0 <= d <= 3:
                due_3 += 1

        if age >= 14:
            long_open_14 += 1

        urgent_list.append({
            "issue_id": it["issue_id"],
            "title": it.get("title",""),
            "owner": it.get("owner",""),
            "target_date": it.get("target_date",""),
            "d_day": d,
            "url": it.get("url",""),
        })

        old_list.append({
            "issue_id": it["issue_id"],
            "title": it.get("title",""),
            "owner": it.get("owner",""),
            "created_at": it.get("created_at",""),
            "age_days": age,
            "url": it.get("url",""),
        })

        last_evt = last_map.get(int(it["issue_id"]), "") or it.get("created_at","")
        last_dt = store._parse_dt(last_evt)
        if last_dt:
            stale_days = (datetime.now().date() - last_dt.date()).days
            stale_list.append({
                "issue_id": it["issue_id"],
                "title": it.get("title",""),
                "owner": it.get("owner",""),
                "last_event_at": last_evt,
                "stale_days": stale_days,
                "url": it.get("url",""),
            })

    urgent_list.sort(key=lambda x: (999999 if x["d_day"] is None else x["d_day"], int(x["issue_id"])))
    old_list.sort(key=lambda x: (-x["age_days"], int(x["issue_id"])))
    stale_list.sort(key=lambda x: (-x["stale_days"], int(x["issue_id"])))

    owner_top = sorted(owner_cnt.items(), key=lambda kv: kv[1], reverse=True)[:8]
    owner_top = [{"owner": k, "open_cnt": v} for k, v in owner_top]

    series = store.build_week_series(
        created_rows=store.issue_list_all_any("OPEN") + closed_recent,
        closed_rows=closed_recent,
        weeks=8
    )

    cycle_days = []
    for it in closed_recent:
        c = store._parse_dt(it.get("created_at",""))
        e = store._parse_dt(it.get("closed_at",""))
        if c and e:
            cycle_days.append((e.date() - c.date()).days)
    avg_cycle = round(sum(cycle_days)/len(cycle_days), 1) if cycle_days else None

    kpi = {
        "open_total": len(open_issues),
        "overdue": overdue,
        "due_7": due_7,
        "due_3": due_3,
        "no_target": no_target,
        "long_open_14": long_open_14,
        "red_alert": overdue + due_3,
        "avg_cycle_days_60d": avg_cycle,
        "today": today.isoformat(),
    }

    return {
        "kpi": kpi,
        "owner_top": owner_top,
        "series": series,
        "urgent_top10": urgent_list[:10],
        "old_top10": old_list[:10],
        "stale_top10": stale_list[:10],
    }

@app.get("/api/dashboard/issues")
def api_dashboard_issues(
    token: str | None = Query(default=None),
    room_id: str | None = Query(default=None),
    status: str = Query(default="OPEN"),
    owner: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=0),
    size: int = Query(default=50),
):
    _require_dashboard_token(token)

    rows = store.issue_list_all_any(None if status == "ALL" else status)

    if room_id:
        rows = [r for r in rows if str(r.get("chatroom_id","")) == str(room_id)]
    if owner:
        rows = [r for r in rows if owner.lower() in (r.get("owner","") or "").lower()]
    if q:
        qq = q.lower()
        rows = [r for r in rows if qq in (r.get("title","") or "").lower() or qq in (r.get("content","") or "").lower()]

    for r in rows:
        r["d_day"] = store._dday(r.get("target_date",""))
        r["age_days"] = store._age_days(r.get("created_at",""))

    if status == "OPEN":
        rows.sort(key=lambda x: (999999 if x["d_day"] is None else x["d_day"], -x["age_days"], int(x["issue_id"])))
    else:
        rows.sort(key=lambda x: int(x["issue_id"]), reverse=True)

    total = len(rows)
    start = page * size
    end = start + size
    return {"total": total, "page": page, "size": size, "items": rows[start:end]}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(token: str | None = Query(default=None)):
    if not DASHBOARD_TOKEN:
        t = token or ""
        return HTMLResponse(ui.DASHBOARD_HTML.replace("__DASHBOARD_TITLE__", DASHBOARD_TITLE).replace("__TOKEN__", t))

