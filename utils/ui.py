import customtkinter as ctk
from PIL import Image
from utils.helpers import resource_path
from utils.workers import process_ui_queue, process_ai_response_worker
import threading
from utils.session_manager import list_sessions,load_session,rename_session,create_session,delete_session,save_session
from datetime import datetime

# App-level state
STATE = {
    "current_session_id": None,
    "current_session_obj": None
}

def setup_ui(client):
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    window = ctk.CTk()
    window.geometry("1400x900")
    window.title("AI Chat")
    window.resizable(False, False)

    try:
        window.iconbitmap(resource_path("assets/Llama.ico"))
    except Exception:
        pass

    try:
        send_icon = ctk.CTkImage(light_image=Image.open(resource_path("assets/send.ico")), size=(40, 40))
    except Exception:
        send_icon = None

    # ---------------- Sidebar top controls ----------------
    # top bar with New Chat (width/height must be constructor args)
    sidebar_top = ctk.CTkFrame(window, width=300, height=60)
    sidebar_top.place(x=10, y=10)
    # new button
    new_btn = ctk.CTkButton(sidebar_top, text="+ New Chat", width=100, command=lambda: new_chat_wrapper())
    new_btn.place(x=12, y=12)

    # --- Sidebar container (left pane) --- (below the top)
    sidebar_container = ctk.CTkScrollableFrame(window, width=300, height=820)
    sidebar_container.place(x=10, y=10 + 60 + 8)  # place below sidebar_top with small gap

    # Chatbox
    chatbox = ctk.CTkTextbox(
        window, width=760, height=500, fg_color="#222222",
        text_color="white", font=("Inter", 16), wrap="word"
    )
    chatbox.place(x=420, y=129)
    chatbox.configure(state="disabled")

    # Input box
    input_box = ctk.CTkTextbox(
        window, width=620, height=50, fg_color="#222222",
        text_color="white", font=("Inter", 16), wrap="word"
    )
    input_box.place(x=460, y=707)

    # Send button
    send_button = ctk.CTkButton(
        window, width=50, image=send_icon, height=40, fg_color="#181818",
        hover_color="#333333", text="", command=lambda: send_message()
    )
    send_button.place(x=1090, y=707)

    # text tags
    chatbox.tag_config("ai", foreground="#00FFFF")
    chatbox.tag_config("user", foreground="lime")
    chatbox.tag_config("system", foreground="#AAAAAA")

    # ---------------- Sidebar / session functions ----------------
    import tkinter as tk
    from tkinter import simpledialog, messagebox
    def render_sidebar(container):
        for w in container.winfo_children():
            w.destroy()
        idx = list_sessions()
        order = idx.get("order", [])
        meta = idx.get("meta", {})

        for sid in order:
            info = meta.get(sid, {})
            name = info.get("name", sid) or sid
            preview = info.get("preview", "") or ""
            display_name = (name[:36] + "...") if len(name) > 40 else name
            display_preview = (preview[:70] + "...") if len(preview) > 73 else preview

            # Frame for one session row
            row = ctk.CTkFrame(container, fg_color="#222222")
            row.pack(fill="x", padx=6, pady=6)

            row.grid_columnconfigure(0, weight=1)   # session name area expands
            row.grid_columnconfigure(1, weight=0)   # rename button
            row.grid_columnconfigure(2, weight=0)   # delete button

            # Left: click area (select session)
            sel_btn = ctk.CTkButton(
                row,
                text=f"{display_name}\n{display_preview}",
                anchor="w",
                fg_color="#2a2a2a",
                hover_color="#333333",
                command=lambda s=sid: on_select_session(s)
            )
            sel_btn.grid(row=0, column=0, sticky="nsew", padx=(6,8), pady=6)

            # Rename button
            ren_btn = ctk.CTkButton(
                row, text="✎", width=32, height=32,
                fg_color="#444444", hover_color="#555555",
                command=lambda s=sid: rename_session_prompt(s)
            )
            ren_btn.grid(row=0, column=1, padx=(0,6), pady=6)

            # Delete button
            del_btn = ctk.CTkButton(
                row, text="✖", width=32, height=32,
                fg_color="#550000", hover_color="#770000",
                command=lambda s=sid: delete_session_and_refresh(s)
            )
            del_btn.grid(row=0, column=2, padx=(0,6), pady=6)


    def rename_session_prompt(session_id):
        # load current name
        try:
            sess = load_session(session_id)
        except FileNotFoundError:
            return
        current_name = sess.get("name", "")

        # simple dialog using tkinter.simpledialog
        new_name = simpledialog.askstring("Rename chat", "Enter new name:", initialvalue=current_name, parent=window)
        if new_name is None:
            return  # user cancelled
        new_name = new_name.strip() or current_name
        # update session file and index
        rename_session(session_id, new_name)
        # if currently open session, update in-memory object too
        if STATE.get("current_session_id") == session_id and STATE.get("current_session_obj"):
            STATE["current_session_obj"]["name"] = new_name
        render_sidebar(sidebar_container)

    def delete_session_and_refresh(session_id):
        # confirm
        if not messagebox.askyesno("Delete chat", "Delete this chat session? This action cannot be undone.", parent=window):
            return
        # perform delete
        delete_session(session_id)
        # if deleted session was current, pick next one or clear UI
        if STATE.get("current_session_id") == session_id:
            STATE["current_session_id"] = None
            STATE["current_session_obj"] = None
            # clear chatbox
            chatbox.configure(state="normal")
            chatbox.delete("1.0", "end")
            chatbox.configure(state="disabled")
            # try to load most recent remaining session
            idx = list_sessions()
            order = idx.get("order", [])
            if order:
                on_select_session(order[0])
        # refresh sidebar
        render_sidebar(sidebar_container)

    def on_select_session(session_id):
        try:
            obj = load_session(session_id)
        except FileNotFoundError:
            return
        STATE["current_session_id"] = session_id
        STATE["current_session_obj"] = obj

        # clear chatbox then display messages
        chatbox.configure(state="normal")
        chatbox.delete("1.0", "end")
        for m in obj.get("messages", []):
            role = m.get("role")
            text = m.get("text", "")
            if role == "user":
                chatbox.insert("end", f"You: {text}\n", "user")
            elif role == "assistant":
                chatbox.insert("end", f"🤖: {text}\n", "ai")
            else:
                chatbox.insert("end", f"[system]: {text}\n", "system")
        chatbox.configure(state="disabled")
        chatbox.see("end")

    def new_chat():
        obj = create_session(name=None, system_prompt="")
        on_select_session(obj["id"])
        render_sidebar(sidebar_container)

    # wrapper used by top-level button to avoid forward reference
    def new_chat_wrapper():
        new_chat()

    # ---------------- UI helpers ----------------
    def append_to_chatbox(text: str, tag: str = None, newline: bool = False):
        chatbox.configure(state="normal")
        if tag:
            chatbox.insert("end", text, tag)
        else:
            chatbox.insert("end", text)
        if newline:
            chatbox.insert("end", "\n")
        chatbox.configure(state="disabled")
        chatbox.see("end")

    def stream_ai_response_on_main(ai_text: str, speed_ms: int = 6):
        idx = {"i": 0}
        def step():
            i = idx["i"]
            if i < len(ai_text):
                append_to_chatbox(ai_text[i], "ai", newline=False)
                idx["i"] += 1
                window.after(speed_ms, step)
            else:
                append_to_chatbox("\n", None, newline=False)
        step()

    # ---------------- Send message flow (updated to use sessions) ----------------
    def send_message(client=client, chatbox=chatbox, input_box=input_box, window=window):
        user_input = input_box.get("1.0", "end").strip()
        if not user_input:
            return

        # UI + log
        append_to_chatbox(f"You: {user_input}\n", "user", newline=False)

        # Ensure a current session exists
        if STATE["current_session_obj"] is None:
            new_obj = create_session(name=None, system_prompt="")
            STATE["current_session_obj"] = new_obj
            STATE["current_session_id"] = new_obj["id"]
            render_sidebar(sidebar_container)

        # Append to in-memory session object
        now_iso = datetime.utcnow().isoformat()
        STATE["current_session_obj"].setdefault("messages", []).append({
            "role": "user", "text": user_input, "time": now_iso
        })

        # Persist the session (atomic, updates index preview)
        save_session(STATE["current_session_obj"])
        # refresh sidebar so preview and ordering update
        render_sidebar(sidebar_container)

        # clear input and start worker
        input_box.delete("1.0", "end")
        t = threading.Thread(target=process_ai_response_worker,
                             args=(client, user_input, append_to_chatbox, stream_ai_response_on_main),
                             daemon=True)
        t.start()

    # Enter / Shift+Enter behavior
    def handle_input(event):
        if event.keysym == "Return" and not (event.state & 0x0001):
            send_message()
            return "break"

    input_box.bind("<KeyPress-Return>", handle_input)

    # start UI queue processor (workers will queue UI calls)
    process_ui_queue(window)

    # load small history preview into chatbox (optional)
    def history_callback(role, text):
        if role == "user":
            append_to_chatbox(f"You (prev): {text}\n", "user", newline=False)
        elif role == "assistant":
            append_to_chatbox(f"🤖 (prev): {text}\n", "ai", newline=False)
        else:
            append_to_chatbox(f"[system]: {text}\n", "system", newline=False)

    # initial sidebar render
    render_sidebar(sidebar_container)

    # auto-load the most recent session (if exists)
    idx = list_sessions()
    order = idx.get("order", [])
    if order:
        on_select_session(order[0])

    return window, append_to_chatbox
