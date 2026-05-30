"""
src/db.py — Lấy / lưu dữ liệu nội bộ (history SQLite + seed CSV).
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
SQLITE_PATH = os.path.join(DB_DIR, "history.db")
JSON_PATH = os.path.join(DB_DIR, "history.json")
BAK_PATH = JSON_PATH + ".bak"
DATA_DIR = os.path.join(BASE_DIR, "data")


def _get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    return sqlite3.connect(SQLITE_PATH)


def _ensure_db():
    """Tạo bảng SQLite nếu chưa có và tự động migrate từ history.json (.bak) nếu tồn tại."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_history (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                title TEXT,
                content_preview TEXT,
                url TEXT,
                model_used TEXT,
                results TEXT,
                primary_label TEXT,
                primary_probability REAL,
                scoring TEXT,
                image TEXT,
                description TEXT,
                author TEXT,
                pub_date TEXT
            )
        """
        )
        conn.commit()

        # Tự động migrate dữ liệu cũ từ JSON hoặc BAK
        migrate_src = None
        if os.path.exists(JSON_PATH):
            migrate_src = JSON_PATH
        elif os.path.exists(BAK_PATH):
            migrate_src = BAK_PATH

        if migrate_src:
            try:
                with open(migrate_src, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                
                if isinstance(old_data, list):
                    for item in old_data:
                        # Đảm bảo không trùng ID
                        cursor.execute("SELECT 1 FROM prediction_history WHERE id = ?", (item.get("id"),))
                        if not cursor.fetchone():
                            cursor.execute(
                                """
                                INSERT INTO prediction_history (
                                    id, created_at, title, content_preview, url, 
                                    model_used, results, primary_label, primary_probability, scoring,
                                    image, description, author, pub_date
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    item.get("id"),
                                    item.get("created_at"),
                                    item.get("title", ""),
                                    item.get("content_preview", ""),
                                    item.get("url", ""),
                                    item.get("model_used", "all"),
                                    json.dumps(item.get("results", {}), ensure_ascii=False),
                                    item.get("primary_label", ""),
                                    float(item.get("primary_probability", 0)),
                                    json.dumps(item.get("scoring"), ensure_ascii=False) if item.get("scoring") else None,
                                    item.get("image", ""),
                                    item.get("description", ""),
                                    item.get("author", ""),
                                    item.get("pub_date", "")
                                )
                            )
                    conn.commit()
                
                # Sau khi migrate xong, đảm bảo lưu tại .bak và xóa .json
                if migrate_src == JSON_PATH:
                    if os.path.exists(BAK_PATH):
                        try:
                            os.remove(BAK_PATH)
                        except Exception:
                            pass
                    os.rename(JSON_PATH, BAK_PATH)
                    print(f"📦 Đã di chuyển lịch sử sang SQLite thành công! Backup lưu tại: {BAK_PATH}")
            except Exception as e:
                print(f"⚠️ Lỗi khi migrate sang SQLite: {e}")
    finally:
        conn.close()

# Khởi tạo DB khi load module
_ensure_db()


def load_history() -> list:
    """Đọc toàn bộ lịch sử dự đoán từ SQLite."""
    conn = _get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prediction_history ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
        history = []
        for r in rows:
            item = {
                "id": r["id"],
                "created_at": r["created_at"],
                "title": r["title"],
                "content_preview": r["content_preview"],
                "url": r["url"],
                "model_used": r["model_used"],
                "primary_label": r["primary_label"],
                "primary_probability": r["primary_probability"],
                "image": r["image"] or "",
                "description": r["description"] or "",
                "author": r["author"] or "",
                "pub_date": r["pub_date"] or "",
            }
            try:
                item["results"] = json.loads(r["results"]) if r["results"] else {}
            except Exception:
                item["results"] = {}
                
            if r["scoring"]:
                try:
                    item["scoring"] = json.loads(r["scoring"])
                except Exception:
                    item["scoring"] = None
            else:
                item["scoring"] = None
                
            history.append(item)
        return history
    finally:
        conn.close()


def insert_prediction(
    title: str,
    content: str,
    results: dict,
    model_used: str,
    scoring: dict | None = None,
    url: str = "",
    image: str = "",
    description: str = "",
    author: str = "",
    pub_date: str = "",
) -> dict:
    """Thêm một kết quả dự đoán vào CSDL SQLite."""
    _ensure_db()
    
    if scoring:
        primary_label = scoring.get("consensus_label", "")
        primary_prob = float(scoring.get("avg_probability", 0))
    else:
        primary_key = list(results.keys())[0] if results else ""
        primary_result = results[primary_key] if primary_key else {}
        primary_label = primary_result.get("label", "")
        primary_prob = float(primary_result.get("probability", 0))

    hist_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    title_val = title[:200] if title else ""
    content_val = content[:300] if content else ""
    
    results_str = json.dumps(results, ensure_ascii=False)
    scoring_str = json.dumps(scoring, ensure_ascii=False) if scoring else None
    
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO prediction_history (
                id, created_at, title, content_preview, url, 
                model_used, results, primary_label, primary_probability, scoring,
                image, description, author, pub_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                hist_id,
                created_at,
                title_val,
                content_val,
                url,
                model_used,
                results_str,
                primary_label,
                primary_prob,
                scoring_str,
                image,
                description,
                author,
                pub_date
            )
        )
        
        # Giới hạn lịch sử tối đa 500 mục
        cursor.execute("SELECT COUNT(*) FROM prediction_history")
        count = cursor.fetchone()[0]
        if count > 500:
            cursor.execute("SELECT id FROM prediction_history ORDER BY created_at ASC LIMIT ?", (count - 500,))
            ids_to_delete = [r[0] for r in cursor.fetchall()]
            for d_id in ids_to_delete:
                cursor.execute("DELETE FROM prediction_history WHERE id = ?", (d_id,))
                
        conn.commit()
        
        entry = {
            "id": hist_id,
            "created_at": created_at,
            "title": title_val,
            "content_preview": content_val,
            "url": url,
            "model_used": model_used,
            "results": results,
            "primary_label": primary_label,
            "primary_probability": primary_prob,
            "image": image,
            "description": description,
            "author": author,
            "pub_date": pub_date,
        }
        if scoring:
            entry["scoring"] = scoring
            
        return entry
    finally:
        conn.close()


def delete_prediction(hist_id: str) -> bool:
    """Xoá một mục lịch sử theo ID."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prediction_history WHERE id = ?", (hist_id,))
        rows_deleted = cursor.rowcount
        conn.commit()
        return rows_deleted > 0
    finally:
        conn.close()


def clear_all_history() -> int:
    """Xoá toàn bộ lịch sử. Trả về số mục đã xoá."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM prediction_history")
        count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM prediction_history")
        conn.commit()
        return count
    finally:
        conn.close()


def search_history_keywords(keywords_list: list) -> list:
    """
    Tìm kiếm các bản ghi lịch sử trùng khớp từ khóa trong tiêu đề hoặc nội dung.
    Trả về danh sách tối đa 3 bản ghi phù hợp nhất.
    """
    if not keywords_list:
        return []
    conn = _get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Chỉ lấy tối đa 10 từ khóa hàng đầu để tránh câu lệnh SQL quá dài
        unique_kws = list(set(keywords_list))[:10]
        
        conditions = []
        params = []
        for kw in unique_kws:
            conditions.append("(title LIKE ? OR content_preview LIKE ?)")
            params.append(f"%{kw}%")
            params.append(f"%{kw}%")
            
        if not conditions:
            return []
            
        query = "SELECT * FROM prediction_history WHERE " + " OR ".join(conditions) + " ORDER BY created_at DESC LIMIT 3"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        matches = []
        for r in rows:
            scoring = None
            if r["scoring"]:
                try:
                    scoring = json.loads(r["scoring"])
                except Exception:
                    pass
            matches.append({
                "title": r["title"],
                "content_preview": r["content_preview"],
                "primary_label": r["primary_label"],
                "primary_probability": r["primary_probability"],
                "scoring": scoring
            })
        return matches
    except Exception:
        return []
    finally:
        conn.close()


def load_seed_news() -> list:
    """
    Đọc dữ liệu demo/seed từ data/news.csv.
    Trả về list[dict] với keys: title, text, label.
    """
    import csv

    csv_path = os.path.join(DATA_DIR, "news.csv")
    if not os.path.exists(csv_path):
        return []

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows
