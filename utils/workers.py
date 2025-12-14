import threading
import queue
from utils.ai_client import get_ai_response_blocking
from datetime import datetime

ui_queue = queue.Queue()

def queue_ui_call(func, *args, **kwargs):
    ui_queue.put((func, args, kwargs))

def process_ui_queue(window):
    try:
        while True:
            func, args, kwargs = ui_queue.get_nowait()
            func(*args, **kwargs)
    except queue.Empty:
        pass
    window.after(50, lambda: process_ui_queue(window))

def process_ai_response_worker(client, user_input, append_to_chatbox, stream_ai_response_on_main):
    # blocking call to the AI
    ai_response = get_ai_response_blocking(client, user_input)

    def do_ui():
        # show AI prefix and stream the body
        append_to_chatbox("🤖: ", "ai", newline=False)
        stream_ai_response_on_main(ai_response, speed_ms=6)
        # save to global storage log (optional)

        # Try to append to the currently loaded session (if any) and persist it.
        # We import ui.STATE lazily to avoid circular imports.
        try:
            import ui
            import session_manager
            now_iso = datetime.utcnow().isoformat()
            if ui.STATE.get("current_session_obj"):
                ui.STATE["current_session_obj"].setdefault("messages", []).append({
                    "role": "assistant", "text": ai_response, "time": now_iso
                })
                # persist the session file + update index preview
                session_manager.save_session(ui.STATE["current_session_obj"])
        except Exception:
            # no-op on failure; fallback already logged via save_message
            pass

    queue_ui_call(do_ui)
