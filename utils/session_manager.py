import json
import os
import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from utils.helpers import resource_path

SESSIONS_DIR = Path(resource_path("sessions"))
INDEX_FILE = SESSIONS_DIR / "index.json"
LOCK = threading.Lock()

def _now_iso():
    return datetime.utcnow().isoformat() + "Z"

def initialize():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_FILE.exists():
        _write_index({"order": [], "meta": {}})

def _read_index() -> Dict[str, Any]:
    if not INDEX_FILE.exists():
        return {"order": [], "meta": {}}
    return json.loads(INDEX_FILE.read_text(encoding="utf-8"))

def _write_index(obj: dict):
    tmp = INDEX_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(INDEX_FILE))

def _session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"

def _atomic_write(path: Path, obj: dict):
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(path))

# --- API ---
def create_session(name: str = None, system_prompt: str = "") -> dict:
    with LOCK:
        initialize()
        sid = f"{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:6]}"
        name = name or f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        obj = {
            "id": sid,
            "name": name,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "pinned": False,
            "tags": [],
            "system_prompt": system_prompt or "",
            "messages": [{"role":"system","text":system_prompt or "", "time": _now_iso()}] if system_prompt else []
        }
        path = _session_path(sid)
        _atomic_write(path, obj)

        idx = _read_index()
        idx["meta"][sid] = {"name": name, "preview": "", "updated_at": obj["updated_at"], "pinned": False}
        if sid in idx["order"]:
            idx["order"].remove(sid)
        idx["order"].insert(0, sid)
        _write_index(idx)
        return obj

def load_session(session_id: str) -> dict:
    path = _session_path(session_id)
    if not path.exists():
        raise FileNotFoundError(session_id)
    return json.loads(path.read_text(encoding="utf-8"))

def save_session(session_obj: dict):
    with LOCK:
        sid = session_obj["id"]
        session_obj["updated_at"] = _now_iso()
        _atomic_write(_session_path(sid), session_obj)
        # update index preview
        preview = ""
        if session_obj.get("messages"):
            # choose last non-system message as preview
            for m in reversed(session_obj["messages"]):
                if m.get("role") != "system":
                    preview = m.get("text","")[:120]
                    break
        idx = _read_index()
        idx["meta"].setdefault(sid, {})["preview"] = preview
        # ensure name remains exactly what the session stores (no accidental concatenation)
        idx_name = session_obj.get("name")
        if idx_name is None:
            idx_name = idx["meta"].get(sid, {}).get("name", "")
        idx["meta"][sid]["name"] = str(idx_name)

        idx["meta"][sid]["updated_at"] = session_obj["updated_at"]
        if sid in idx["order"]:
            idx["order"].remove(sid)
        idx["order"].insert(0, sid)
        _write_index(idx)

def delete_session(session_id: str):
    with LOCK:
        path = _session_path(session_id)
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass
        idx = _read_index()
        if session_id in idx["order"]:
            idx["order"].remove(session_id)
        idx["meta"].pop(session_id, None)
        _write_index(idx)

def list_sessions() -> dict:
    initialize()
    return _read_index()

def rename_session(session_id: str, new_name: str):
    with LOCK:
        s = load_session(session_id)
        s["name"] = new_name
        s["updated_at"] = _now_iso()
        _atomic_write(_session_path(session_id), s)
        idx = _read_index()
        if session_id in idx["meta"]:
            idx["meta"][session_id]["name"] = new_name
            idx["meta"][session_id]["updated_at"] = s["updated_at"]
            _write_index(idx)
