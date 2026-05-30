"""
src/history.py — API tương thích ngược cho lịch sử dự đoán.
Thực tế ủy quyền mọi thao tác cho src/db.py.
"""

from src.db import (
    insert_prediction,
    load_history,
    delete_prediction,
    clear_all_history,
)


def add_to_history(title: str, content: str, results: dict, model_used: str) -> dict:
    """Thêm một kết quả dự đoán vào lịch sử."""
    return insert_prediction(title, content, results, model_used)


def get_history() -> list:
    """Lấy toàn bộ lịch sử dự đoán."""
    return load_history()


def delete_from_history(hist_id: str) -> bool:
    """Xoá một mục lịch sử theo ID. Trả về True nếu thành công."""
    return delete_prediction(hist_id)


def clear_history() -> int:
    """Xoá toàn bộ lịch sử. Trả về số mục đã xoá."""
    return clear_all_history()
