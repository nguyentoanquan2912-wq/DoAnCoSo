import json
import os
import uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "history.json")


def _load():
    os.makedirs(DB_DIR, exist_ok=True)
    if not os.path.exists(DB_PATH):
        return []
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save(data):
    os.makedirs(DB_DIR, exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_to_history(title: str, content: str, results: dict, model_used: str) -> dict:
    """Thêm một kết quả dự đoán vào lịch sử."""
    data = _load()

    # Lấy kết quả primary (model đầu tiên hoặc model duy nhất)
    primary_key = list(results.keys())[0]
    primary_result = results[primary_key]

    entry = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now().isoformat(),
        "title": title[:200] if title else "",
        "content_preview": content[:300] if content else "",
        "model_used": model_used,
        "results": results,
        "primary_label": primary_result.get("label", ""),
        "primary_probability": primary_result.get("probability", 0),
    }

    data.insert(0, entry)

    # Giới hạn lịch sử tối đa 500 mục
    if len(data) > 500:
        data = data[:500]

    _save(data)
    return entry


def get_history() -> list:
    """Lấy toàn bộ lịch sử dự đoán."""
    return _load()


def delete_from_history(hist_id: str) -> bool:
    """Xoá một mục lịch sử theo ID. Trả về True nếu thành công."""
    data = _load()
    original_len = len(data)
    data = [item for item in data if item.get("id") != hist_id]
    if len(data) == original_len:
        return False
    _save(data)
    return True


def clear_history() -> int:
    """Xoá toàn bộ lịch sử. Trả về số mục đã xoá."""
    data = _load()
    count = len(data)
    _save([])
    return count
