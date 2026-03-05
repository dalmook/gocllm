    if (token or "") == DASHBOARD_TOKEN:
        return HTMLResponse(ui.DASHBOARD_HTML.replace("__DASHBOARD_TITLE__", DASHBOARD_TITLE).replace("__TOKEN__", token or ""))

    return HTMLResponse(ui.DASHBOARD_LOGIN_HTML.replace("__DASHBOARD_TITLE__", DASHBOARD_TITLE))

# KNOX 재연결 함수
def job_knox_reconnect():
    global chatBot
    # 이미 연결되어 있으면 재시도 안함
    if chatBot is not None:
        return
    
    print("[knox_reconnect] KNOX 연결 시도...")
    try:
        new_chatBot = KnoxMessenger(host=KNOX_HOST, systemId=KNOX_SYSTEM_ID, token=KNOX_TOKEN)
        new_chatBot.device_regist()
        new_chatBot.getKeys()
        chatBot = new_chatBot
        print("[knox_reconnect] KNOX 연결 성공! chatBot 객체 재설정 완료")
    except Exception as e:
        print(f"[knox_reconnect] KNOX 연결 실패: {e}")


@app.on_event("startup")
def on_startup():
    global chatBot
    store.init_db()
    start_llm_workers()
    print(f"[startup] LLM workers started: workers={LLM_WORKERS}, max_concurrent={LLM_MAX_CONCURRENT}, queue_max={LLM_JOB_QUEUE_MAX}")

    # KNOX 연결 - 실패해도 앱은 계속 실행
    try:
        chatBot = KnoxMessenger(host=KNOX_HOST, systemId=KNOX_SYSTEM_ID, token=KNOX_TOKEN)
        chatBot.device_regist()
        chatBot.getKeys()
        print("[startup] KNOX 연결 성공")
    except Exception as e:
        print(f"[startup] KNOX 연결 실패: {e}")
        print("[startup] KNOX 기능은 사용할 수 없지만 앱은 계속 실행됩니다.")
        print("[startup] 5분마다 자동 재연결을 시도합니다.")
        chatBot = None  # KNOX 기능 비활성화

    # 스케줄러 시작
    try:
        scheduler.add_job(job_issue_summary_daily, CronTrigger(hour=8, minute=00), id="issue_summary", replace_existing=True)
        # scheduler.add_job(job_issue_deadline_reminder_daily, CronTrigger(hour=8, minute=35), id="issue_deadline_remind", replace_existing=True)
        # KNOX 재연결 작업: 5분마다 실행
        scheduler.add_job(job_knox_reconnect, CronTrigger(minute="*/5"), id="knox_reconnect", replace_existing=True)
        scheduler.start()
        print("[startup] 스케줄러 시작 성공 (KNOX 재연결: 5분마다)")
    except Exception as e:
        print(f"[startup] 스케줄러 시작 실패: {e}")

    print("[BOOT] main =", __file__)
    print("[BOOT] store=", store.__file__)
    print("[BOOT] ui   =", ui.__file__)

    print("[startup] ready")


@app.post("/message")
async def post_message(request: Request):
    # KNOX 연결 안 된 경우
    if chatBot is None:
        return {"ok": False, "error": "KNOX 연결 안됨"}
    
    body = await request.body()
    info = json.loads(AESCipher(chatBot.key).decrypt(body))
    print(info)

    chatroom_id = int(info["chatroomId"])
    sender_name = info.get("senderName", "") or ""
    sender_knox = info.get("senderKnoxId", "") or ""
    sender = sender_name if sender_name else sender_knox

    action, payload = parse_action_payload(info)

    if action == "NOOP":
        return {"ok": True}

    try:
        if action == "OPEN_URL":
            url = (payload.get("url") or "").strip()
            title = (payload.get("title") or "🔗 바로가기").strip()
            if url:
                chatBot.send_adaptive_card(chatroom_id, ui.build_quicklink_card(title, url))
            else:
                chatBot.send_text(chatroom_id, "링크가 비어있어요.")
            return {"ok": True}

        elif action in ("HOME", "INTRO"):
            chatBot.send_adaptive_card(chatroom_id, ui.build_home_card(dashboard_url=DASHBOARD_URL, infocenter_url=INFOCENTER_URL))


        elif action == "WARN_RUN":
            run_warning_once_to_chatroom(chatroom_id)

        elif action == "QUICK_LINKS":
            ui_room = route_ui_room(chatroom_id, info, sender_name)  # ✅ GROUP이면 DM, SINGLE이면 그대로
            chatBot.send_adaptive_card(ui_room, ui.build_quick_links_card(QUICK_LINK_ALIASES))
            return {"ok": True}
        
        # ---------- LLM Chatbot ----------
        elif action == "LLM_CHAT":
            if not is_llm_allowed_user(sender_knox):
                chatBot.send_adaptive_card(chatroom_id, ui.build_home_card(dashboard_url=DASHBOARD_URL, infocenter_url=INFOCENTER_URL))
                return {"ok": True}

            question = (payload.get("question") or "").strip()
            if not question:
                chatBot.send_text(chatroom_id, "질문 내용이 비어있습니다. /ask 질문내용 또는 질문:내용 형식으로 입력해주세요.")
                return {"ok": True}

            try:
                request_id = str(uuid.uuid4())
                job = {
                    "chatroom_id": chatroom_id,
                    "sender_knox": sender_knox,
                    "sender_name": sender_name,
                    "chat_type": (info.get("chatType") or "").upper(),
                    "question": question,
                    "requested_at": time.time(),
                    "request_id": request_id,
                }

                try:
                    chatBot.send_text(chatroom_id, "🤔 검색 중입니다. 잠시만 기다려주세요...")
                except Exception as send_err:
                    print("[send thinking message failed]", send_err)

                if not enqueue_llm_job(job):
                    chatBot.send_text(chatroom_id, LLM_QUEUE_FULL_MESSAGE)
                    return {"ok": True}

                return {"ok": True}
            except Exception as e:
                print(f"[LLM Dispatch Error] {e}")
                import traceback
                traceback.print_exc()
                try:
                    chatBot.send_text(chatroom_id, f"LLM 요청 처리 오류: {e}")
                except Exception:
                    pass
                return {"ok": True}

        
        # ---------- Generic Query Router ----------
        elif action in ui.ACTION_TO_QUERY:
            ui_room = route_ui_room(chatroom_id, info, sender_name)  # ✅ DM 우선

            mode, qkey = ui.ACTION_TO_QUERY[action]
            spec = ui.QUERY_REGISTRY[qkey]

            if mode == "FORM":
                chatBot.send_adaptive_card(ui_room, ui.build_query_form_card(spec))
                return {"ok": True}


            for f in spec.get("fields", []):
                if f.get("required") and not (payload.get(f["id"]) or "").strip():
                    chatBot.send_text(ui_room, f"필수값 누락: {f.get('label', f['id'])}")
                    chatBot.send_adaptive_card(ui_room, ui.build_query_form_card(spec))
                    return {"ok": True}

            params_builder = spec.get("params_builder")
            params = params_builder(payload) if callable(params_builder) else None

            # (수정 코드 - 교체용)
            result = RUNNERS[spec["runner"]](params or {}) if spec.get("runner") else run_oracle_query(spec["sql"], params=params)

            # ✅ runner가 AdaptiveCard(dict)로 주면 그대로 전송하고 종료
            if isinstance(result, dict) and result.get("type") == "AdaptiveCard":
                chatBot.send_adaptive_card(ui_room, result)
                return {"ok": True}

            df = result  # DataFrame으로 간주

            if spec.get("output") == "MSG7_TABLE":
                chatBot.send_table_csv_msg7(ui_room, df, title=spec.get("title","조회 결과"))
            else:
                chatBot.send_adaptive_card(ui_room, ui.df_to_table_card(df, title=spec.get("title","조회 결과")))

            return {"ok": True}
        
        # (추가 코드 - 교체/추가용)  ※ Generic Query Router 위쪽 아무 곳에 추가
        elif action == "TERM_UNKNOWN_SUBMIT":
            ui_room = route_ui_room(chatroom_id, info, sender_name)  # ✅ 누락 보완

            findword = (payload.get("findword") or "").strip()
            memo = (payload.get("memo") or "").strip()
            rooms = [x.strip() for x in TERM_ADMIN_ROOM_IDS.split(",") if x.strip().isdigit()]

            msg = f"📩 [용어 반영 요청]\n- 단어: {findword}\n- 요청자: {sender}\n" + (f"- 메모: {memo}\n" if memo else "")
            if rooms:
                for rid in rooms:
                    chatBot.send_text(int(rid), msg)
                chatBot.send_text(ui_room, "접수 완료 ✅ (담당자에게 전달했습니다)")
            else:
                chatBot.send_text(ui_room, "접수 완료 ✅ (TERM_ADMIN_ROOM_IDS 미설정이라 전달은 생략됨)")
            return {"ok": True}      

        # ---------- Issue ----------
        elif action == "ISSUE_FORM":
            scope = store.scope_room_id(chatroom_id, payload)          # ✅ 데이터 스코프(원래 단체방)
            ui_room = route_ui_room(chatroom_id, info, sender_name)    # ✅ UI는 DM (SINGLE이면 그대로)

            chatBot.send_adaptive_card(
                ui_room,
                ui.build_issue_form_card(sender_hint=sender, room_id=str(scope))
            )
            return {"ok": True}


        elif action == "ISSUE_CREATE":
            scope = store.scope_room_id(chatroom_id, payload)          # ✅ 데이터 스코프(원래 단체방)
            ui_room = route_ui_room(chatroom_id, info, sender_name)    # ✅ UI는 DM (SINGLE이면 그대로)
            origin_room = int(scope)

            title = (payload.get("title") or "").strip()
            content = (payload.get("content") or "").strip()
            url = (payload.get("url") or "").strip()
            occur_date = (payload.get("occur_date") or "").strip()
            target_date = (payload.get("target_date") or "").strip()
            owner = (payload.get("owner") or "").strip()

            if not title:
                chatBot.send_text(ui_room, "제목이 비어있습니다. 다시 발의해 주세요.")
                chatBot.send_adaptive_card(
                    ui_room,
                    ui.build_issue_form_card(sender_hint=sender, room_id=str(origin_room))
                )
                return {"ok": True}

            issue_id = store.issue_create(
                origin_room,
                title,
                content,
                url,
                occur_date,
                target_date,
                owner,
                sender
            )

            # ✅ 완료 메시지/UI 갱신은 ui_room(DM)으로
            chatBot.send_text(ui_room, f"✅ 이슈 등록 완료: #{issue_id} {title}")

            try:
                issues = store.issue_list_open(str(origin_room))
                send_issue_list_card(ui_room, issues, scope_room_id=str(origin_room), recall_prev=True)
            except Exception as e:
                print("[dm issue list refresh failed]", e)

            return {"ok": True}



        elif action == "ISSUE_LIST":
            scope = store.scope_room_id(chatroom_id, payload)          # ✅ 데이터 스코프(원래 단체방)
            ui_room = route_ui_room(chatroom_id, info, sender_name)    # ✅ UI는 DM

            issues = store.issue_list_open(str(scope))
            send_issue_list_card(ui_room, issues, scope_room_id=str(scope), recall_prev=True)
            return {"ok": True}


        elif action == "ISSUE_CLEAR":
            scope = store.scope_room_id(chatroom_id, payload)
            ui_room = route_ui_room(chatroom_id, info, sender_name)

            issue_id = payload.get("issue_id")
            if issue_id is None:
                chatBot.send_text(ui_room, "issue_id가 없습니다.")
                return {"ok": True}

            store.issue_clear(str(scope), int(issue_id), sender)
            chatBot.send_text(ui_room, f"✅ Clear 처리 완료: #{issue_id}")

            issues = store.issue_list_open(str(scope))
            send_issue_list_card(ui_room, issues, scope_room_id=str(scope), recall_prev=True)
            return {"ok": True}


        elif action == "ISSUE_EDIT_FORM":
            scope = store.scope_room_id(chatroom_id, payload)
            ui_room = route_ui_room(chatroom_id, info, sender_name)

            issue_id = payload.get("issue_id")
            if issue_id is None:
                chatBot.send_text(ui_room, "issue_id가 없습니다.")
                return {"ok": True}

            issue = store.issue_get(str(scope), int(issue_id))
            if not issue:
                chatBot.send_text(ui_room, f"해당 이슈를 찾을 수 없습니다: #{issue_id}")
                return {"ok": True}

            chatBot.send_adaptive_card(ui_room, ui.build_issue_edit_form_card(issue, room_id=str(scope)))
            return {"ok": True}


        elif action == "ISSUE_UPDATE":
            scope = store.scope_room_id(chatroom_id, payload)
            ui_room = route_ui_room(chatroom_id, info, sender_name)

            issue_id = payload.get("issue_id")
            if issue_id is None:
                chatBot.send_text(ui_room, "issue_id가 없습니다.")
                return {"ok": True}

            title = (payload.get("title") or "").strip()
            content = (payload.get("content") or "").strip()
            url = (payload.get("url") or "").strip()
            occur_date = (payload.get("occur_date") or "").strip()
            target_date = (payload.get("target_date") or "").strip()
            owner = (payload.get("owner") or "").strip()

            if not title:
                chatBot.send_text(ui_room, "제목이 비어있습니다.")
                issue = store.issue_get(str(scope), int(issue_id))
                if issue:
                    chatBot.send_adaptive_card(ui_room, ui.build_issue_edit_form_card(issue, room_id=str(scope)))
                return {"ok": True}

            store.issue_update(str(scope), int(issue_id), title, content, url, occur_date, target_date, owner, actor=sender)
            chatBot.send_text(ui_room, f"✅ 수정 완료: #{issue_id} {title}")

            issues = store.issue_list_open(str(scope))
            send_issue_list_card(ui_room, issues, scope_room_id=str(scope), recall_prev=True)
            return {"ok": True}


        elif action == "ISSUE_HISTORY":
            scope = store.scope_room_id(chatroom_id, payload)
            ui_room = route_ui_room(chatroom_id, info, sender_name)

            is_nav = ("page" in payload)
            page = int(payload.get("page", 0) or 0)
            send_issue_history_card(ui_room, scope_room_id=str(scope), page=page, recall_prev=is_nav)
            return {"ok": True}


        elif action == "ISSUE_DELETE":
            scope = store.scope_room_id(chatroom_id, payload)
            ui_room = route_ui_room(chatroom_id, info, sender_name)

            issue_id = payload.get("issue_id")
            if issue_id is None:
                chatBot.send_text(ui_room, "issue_id가 없습니다.")
                return {"ok": True}

            page = int(payload.get("page", 0) or 0)
            ok, msg = store.issue_delete(str(scope), int(issue_id), sender)
            if not ok:
                chatBot.send_text(ui_room, msg)

            send_issue_history_card(ui_room, scope_room_id=str(scope), page=page, recall_prev=True)
            return {"ok": True}


        # ---------- Watchroom ----------
        elif action == "WATCHROOM_FORM":
            ui_room = route_ui_room(chatroom_id, info, sender_name)
            chatBot.send_adaptive_card(ui_room, ui.build_watchroom_form_card())


        elif action == "WATCHROOM_CREATE":
            ui_room = route_ui_room(chatroom_id, info, sender_name)

            room_title = (payload.get("room_title") or "").strip()
            members_raw = (payload.get("members") or "").strip()
            note = (payload.get("note") or "").strip()


            if not members_raw:
                chatBot.send_text(chatroom_id, "참여자 SSO가 비어있습니다. 예: sungmook.cho,cc.choi")
                chatBot.send_adaptive_card(chatroom_id, ui.build_watchroom_form_card())
                return {"ok": True}

            members = [x.strip() for x in members_raw.replace("\n", ",").split(",") if x.strip()]
            user_ids = chatBot.resolve_user_ids_from_loginids(members)
            if not user_ids:
                chatBot.send_text(chatroom_id, "참여자 변환(userID)이 실패했습니다. SSO가 맞는지 확인해 주세요.")
                return {"ok": True}

            title_to_use = room_title or note or "공지방"
            new_room_id = chatBot.room_create(user_ids, chatType=1, chatroom_title=title_to_use)
            store.add_watch_room(str(new_room_id), created_by=sender, note=note, chatroom_title=title_to_use)

            chatBot.send_text(
                chatroom_id,
                f"✅ 공지방 생성 & 푸시대상 등록 완료\n- chatroomId: {new_room_id}\n- title: {title_to_use}\n- note: {note}"
            )
            chatBot.send_text(
                new_room_id,
                "📣 이 방은 봇이 생성한 공지/워닝/이슈 방입니다.\n- 워닝(스케줄) / 이슈요약(스케줄) 푸시 대상입니다.\n- @공급망 챗봇 으로 기능을 실행하세요."
            )
            chatBot.send_adaptive_card(new_room_id, ui.build_home_card(dashboard_url=DASHBOARD_URL, infocenter_url=INFOCENTER_URL))
            return {"ok": True}

        else:
            chatBot.send_text(chatroom_id, f"알 수 없는 action: {action}")
            chatBot.send_adaptive_card(chatroom_id, ui.build_home_card(dashboard_url=DASHBOARD_URL, infocenter_url=INFOCENTER_URL))

    except Exception as e:
        chatBot.send_text(chatroom_id, f"오류 발생: {e}")

    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host=BIND_HOST, port=BIND_PORT, workers=1)
