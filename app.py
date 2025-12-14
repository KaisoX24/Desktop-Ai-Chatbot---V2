from utils.helpers import load_env
from utils.ai_client import init_client
from utils.ui import setup_ui
from utils.session_manager import initialize

if __name__ == "__main__":
    api_key = load_env()
    client = init_client(api_key)
    initialize()
    window, append_to_chatbox = setup_ui(client)

    if client is None:
        append_to_chatbox("GROQ API key not set. Configure GROQ_API_KEY in assets/.env or system environment.\n", "system")

    append_to_chatbox("Ready. Type and press Enter to send (Shift+Enter for newline).\n", "system")
    window.mainloop()