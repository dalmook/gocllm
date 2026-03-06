[LLM Background Error] Error code: 404 - {'message': 'no Route matched with those values', 'request_id': 'bd54c85a874ccd54924c6a55d7dfea16'}
Traceback (most recent call last):

  File "h:\python_pjt\chatbot4\Lib\site-packages\openai\_base_client.py", line 1070, in request
    raise self._make_status_error_from_response(err.response) from None
openai.NotFoundError: Error code: 404 - {'message': 'no Route matched with those values', 'request_id': 'bd54c85a874ccd54924c6a55d7dfea16'}
[llm-worker-1][24d1e2ef-a4e7-4ddc-b4a4-b4bbaf644c47] done queue_wait=0.03s total=2.01s rag_calls=1 llm_calls=0 used_rag=True memory_hit=True memory_message_count=4 memory_prompt_chars=418 rewrite_used_memory=False fallback_reason=error:Error code: 404 - {'message': 'no Route matched with those values', 'request_id': 'bd54c85a874ccd54924c6a55d7dfea16'} rpm=1@2026-03-06 10:58
