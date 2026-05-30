"""src/chatbot.py — Chatbot nội bộ và OCR cục bộ (không cần API Key bên ngoài)."""

import base64
import io
import re

from src.preprocess import clean_text
from src.db import search_history_keywords

# ─── Lazy-loaded EasyOCR Reader ────────────────────────────────────────────
_ocr_reader = None


def _get_ocr_reader():
    """Khởi tạo EasyOCR reader (chỉ load 1 lần, cache global)."""
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        _ocr_reader = easyocr.Reader(['vi', 'en'], gpu=False, verbose=False)
    return _ocr_reader


# ─── Từ điển phân tích ─────────────────────────────────────────────────────
SENSATIONAL_WORDS = [
    "lừa đảo", "trúng thưởng", "bắt buộc", "ngay lập tức", "tiêu diệt",
    "khẩn cấp", "chữa bách bệnh", "ung thư hoàn toàn", "thần dược", "bí mật",
    "sốc", "kinh hoàng", "phản động", "chia sẻ ngay", "gấp gấp", "lan tỏa",
    "bí truyền", "cực sốc", "rúng động", "vạch trần", "tuyệt mật",
    "không thể tin nổi", "bật mí", "sự thật đằng sau", "cứu người",
    "share gấp", "đừng im lặng", "thần y", "chữa khỏi 100%",
    "không cần hóa trị", "không cần đi viện", "chữa khỏi hẳn",
    "cảnh báo khẩn", "hãy cẩn thận", "đặc biệt nguy hiểm",
]

TRUSTED_SOURCES = [
    "vtv", "vnexpress", "tuổi trẻ", "tuoi tre", "nhân dân", "nhan dan",
    "thanh niên", "thanh nien", "dân trí", "dan tri", "chính phủ",
    "chinh phu", "vietnamnet", "lao động", "lao dong", "vtc",
    "vietnamplus", "sức khỏe đời sống", "pháp luật", "công an",
    "quân đội nhân dân", "bộ y tế", "who", "reuters", "bbc",
]

CITATION_WORDS = [
    "theo báo", "cho biết", "phát biểu", "trích dẫn", "nguồn tin",
    "dẫn lời", "văn bản số", "công văn", "quyết định", "nghị định",
    "thông tư", "theo nghiên cứu", "theo thống kê",
]


def _analyze_text_features(text: str) -> dict:
    """Phân tích các đặc trưng ngôn ngữ của văn bản."""
    text_lower = text.lower()
    
    # Tìm từ giật gân
    found_sensational = [w for w in SENSATIONAL_WORDS if w in text_lower]
    
    # Tìm nguồn uy tín
    found_sources = [w for w in TRUSTED_SOURCES if w in text_lower]
    
    # Tìm trích dẫn
    found_citations = [w for w in CITATION_WORDS if w in text_lower]
    
    # Phân tích cấu trúc văn bản
    sentences = re.split(r'[.!?。]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    avg_sentence_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
    
    # Đếm dấu chấm than
    exclamation_count = text.count('!')
    question_count = text.count('?')
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    
    # Tokenize bằng underthesea
    try:
        from underthesea import word_tokenize
        tokens = word_tokenize(text)
        word_count = len(tokens)
    except Exception:
        word_count = len(text.split())
    
    return {
        "found_sensational": found_sensational,
        "found_sources": found_sources,
        "found_citations": found_citations,
        "sentence_count": len(sentences),
        "avg_sentence_len": avg_sentence_len,
        "exclamation_count": exclamation_count,
        "question_count": question_count,
        "caps_ratio": caps_ratio,
        "word_count": word_count,
        "has_url": bool(re.search(r'https?://', text)),
    }


def _compute_trust_score(features: dict) -> int:
    """Tính điểm tin cậy dựa trên phân tích đặc trưng."""
    score = 70  # Điểm khởi đầu trung tính
    
    # Giảm điểm: từ giật gân
    score -= min(40, len(features["found_sensational"]) * 10)
    
    # Tăng điểm: nguồn uy tín
    score += min(20, len(features["found_sources"]) * 8)
    
    # Tăng điểm: có trích dẫn
    score += min(10, len(features["found_citations"]) * 5)
    
    # Giảm điểm: quá nhiều dấu chấm than
    if features["exclamation_count"] >= 3:
        score -= min(15, features["exclamation_count"] * 3)
    
    # Giảm điểm: tỷ lệ chữ hoa cao (thường là giật gân)
    if features["caps_ratio"] > 0.3:
        score -= 10
    
    # Tăng điểm: văn bản dài, chi tiết (thường đáng tin hơn)
    if features["word_count"] > 100:
        score += 5
    if features["word_count"] > 300:
        score += 5
    
    # Tăng điểm: có URL nguồn
    if features["has_url"]:
        score += 5
    
    # Câu quá ngắn thường là tin đồn
    if features["avg_sentence_len"] < 20 and features["sentence_count"] <= 2:
        score -= 10
    
    return max(10, min(98, score))


def _search_dataset_csv(keywords: list) -> list:
    """Tìm kiếm trong dataset CSV huấn luyện để đối chiếu."""
    import os
    import csv
    
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "news.csv"
    )
    if not os.path.exists(csv_path):
        return []
    
    matches = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title_lower = (row.get("title", "") or "").lower()
                text_lower = (row.get("text", "") or "").lower()
                matched_kws = [kw for kw in keywords if kw in title_lower or kw in text_lower]
                if len(matched_kws) >= 2:
                    matches.append({
                        "title": row.get("title", "")[:100],
                        "label": row.get("label", ""),
                        "matched_keywords": matched_kws[:5],
                    })
                if len(matches) >= 3:
                    break
    except Exception:
        pass
    return matches


def get_vip_core_response(message: str, matches: list = None) -> str:
    """Tạo báo cáo thẩm định chuyên gia VIP Core dựa trên NLP và SQLite RAG cục bộ."""
    features = _analyze_text_features(message)
    score = _compute_trust_score(features)
    
    # Xác định nhãn
    if score < 45:
        label = "Có dấu hiệu Tin giả / Thiếu tin cậy (Unreliable)"
        label_emoji = "🚨"
    elif score < 70:
        label = "Tin đồn hoặc Chưa được kiểm chứng (Unverified)"
        label_emoji = "⚠️"
    else:
        label = "Đáng tin cậy (Reliable)"
        label_emoji = "✅"
    
    # Tìm thêm trong dataset CSV
    csv_matches = []
    try:
        cleaned = clean_text(message)
        keywords = [w.replace("_", " ") for w in cleaned.split() if len(w) > 2][:8]
        if keywords:
            csv_matches = _search_dataset_csv(keywords)
    except Exception:
        pass
    
    # ═══ XÂY DỰNG BÁO CÁO ═══
    response = "### 🛡️ BÁO CÁO THẨM ĐỊNH — TRUSTCHECK AI ENGINE\n\n"
    response += "> **Hệ thống phân tích**: Engine NLP cục bộ + SQLite RAG + Dataset đối chiếu\n"
    response += "> Không cần kết nối API bên ngoài — phân tích hoàn toàn trên máy chủ nội bộ.\n\n"
    
    # 1. Kết luận
    response += "### 1. Kết luận sơ bộ & Điểm tin cậy\n"
    response += f"- {label_emoji} **Nhận định**: **{label}**\n"
    response += f"- **Chỉ số tin cậy**: `{score}%`\n"
    
    if features["found_sensational"]:
        response += f"- **⚠️ Phát hiện từ ngữ giật gân**: *{', '.join(features['found_sensational'][:5])}*\n"
    if features["found_sources"]:
        response += f"- **✅ Nguồn tin uy tín**: *{', '.join(features['found_sources'][:5])}*\n"
    if features["found_citations"]:
        response += f"- **📎 Có trích dẫn/dẫn nguồn**: *{', '.join(features['found_citations'][:3])}*\n"
    
    # 2. Phân tích chi tiết
    response += "\n### 2. Phân tích Ngữ nghĩa & Đặc trưng Văn bản\n"
    
    response += f"- **Độ dài văn bản**: {features['word_count']} từ, {features['sentence_count']} câu\n"
    
    if features["exclamation_count"] >= 3:
        response += f"- **⚠️ Dấu chấm than**: Phát hiện {features['exclamation_count']} dấu '!' — dấu hiệu giật gân\n"
    
    if features["caps_ratio"] > 0.3:
        response += "- **⚠️ Tỷ lệ chữ hoa cao**: Phong cách viết giật gân, thu hút chú ý\n"
    
    if features["word_count"] < 50:
        response += "- **⚠️ Nội dung quá ngắn**: Bài viết thiếu chi tiết, khó kiểm chứng\n"
    elif features["word_count"] > 200:
        response += "- **✅ Nội dung chi tiết**: Bài viết có độ dài phù hợp để đánh giá\n"
    
    if not features["found_citations"] and not features["has_url"]:
        response += "- **⚠️ Thiếu nguồn dẫn**: Không tìm thấy trích dẫn hoặc đường dẫn nguồn\n"
    
    # 3. Đối chiếu dữ liệu
    if matches:
        response += "\n### 3. Đối chiếu Cơ sở Dữ liệu Lịch sử (SQLite RAG)\n"
        response += f"Tìm thấy **{len(matches)} bản ghi** kiểm chứng liên quan:\n\n"
        for idx, match in enumerate(matches, 1):
            label_display = "✅ Tin thật" if match["primary_label"] == "reliable" else "🚨 Tin giả"
            response += f"**#{idx}**: *\"{match['title']}\"*\n"
            response += f"  → Kết quả ML: `{label_display}` (Đồng thuận: `{match['primary_probability']}%`)\n\n"
    
    if csv_matches:
        response += "\n### 4. Đối chiếu Dataset Huấn luyện\n"
        response += f"Tìm thấy **{len(csv_matches)} bài viết** tương tự trong bộ dữ liệu huấn luyện:\n\n"
        for idx, cm in enumerate(csv_matches, 1):
            lbl = "✅ Reliable" if cm["label"] == "reliable" else "🚨 Unreliable"
            response += f"**#{idx}**: *\"{cm['title']}\"* → `{lbl}`\n"
    
    # Lời khuyên
    next_section = 5 if csv_matches else (4 if matches else 3)
    response += f"\n### {next_section}. Lời khuyên dành cho bạn\n"
    response += "1. 📰 **Kiểm tra nguồn**: Tìm tiêu đề tương tự trên *VTV, VNExpress, Tuổi Trẻ, Báo Nhân Dân*.\n"
    response += "2. 🔍 **Đối chiếu chéo**: So sánh thông tin với ít nhất 2-3 nguồn báo chí chính thống.\n"
    response += "3. 🔒 **Bảo mật**: Không click link lạ, không chuyển tiền, không chia sẻ mã OTP.\n"
    response += "4. 🤖 **Phân tích ML**: Sử dụng công cụ [Phân tích tin tức](/analyzer) để kiểm chứng bằng mô hình Linear SVM.\n"
    
    return response


def chat_response(message: str, history: list = None) -> str:
    """
    Xử lý chat — sử dụng hoàn toàn engine NLP cục bộ.
    Không cần API Key bên ngoài.
    """
    # Tìm kiếm đối chiếu trong SQLite
    matches = []
    try:
        cleaned_msg = clean_text(message)
        keywords = [w.replace("_", " ") for w in cleaned_msg.split() if len(w) > 2]
        if keywords:
            matches = search_history_keywords(keywords)
    except Exception:
        pass
    
    return get_vip_core_response(message, matches)


def extract_text_from_image(image_base64: str, mime_type: str) -> dict:
    """
    Dùng EasyOCR cục bộ để trích xuất văn bản từ ảnh.
    Không cần API Key bên ngoài.
    
    Returns:
        dict: {"title": str, "content": str}
    """
    from PIL import Image
    
    # Decode base64 → bytes → PIL Image
    image_bytes = base64.b64decode(image_base64)
    image = Image.open(io.BytesIO(image_bytes))
    
    # Chuyển sang RGB nếu cần (EasyOCR cần RGB)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Chuyển PIL Image → numpy array
    import numpy as np
    image_np = np.array(image)
    
    # OCR bằng EasyOCR
    reader = _get_ocr_reader()
    results = reader.readtext(image_np, detail=1)
    
    if not results:
        return {"title": "", "content": ""}
    
    # Sắp xếp theo vị trí (top → bottom, left → right)
    results.sort(key=lambda x: (x[0][0][1], x[0][0][0]))
    
    # Trích xuất text với thông tin vị trí
    all_texts = []
    for r in results:
        text = r[1].strip()
        if not text:
            continue
        bbox = r[0]
        y_top = bbox[0][1]
        y_bottom = bbox[2][1]
        height = abs(y_bottom - y_top)
        all_texts.append({"text": text, "y_top": y_top, "y_bottom": y_bottom, "height": height})
    
    if not all_texts:
        return {"title": "", "content": ""}
    
    # Tìm tiêu đề: text có font lớn nhất VÀ nằm ở 1/3 trên của ảnh
    img_height = image_np.shape[0]
    top_third = img_height / 3
    
    title_candidates = [t for t in all_texts if t["y_top"] < top_third]
    if not title_candidates:
        title_candidates = all_texts[:3]  # fallback: 3 dòng đầu
    
    # Chọn text có height lớn nhất trong vùng top
    title_item = max(title_candidates, key=lambda t: t["height"])
    title = title_item["text"]
    
    # Ghép nội dung: nhóm các dòng gần nhau thành đoạn văn
    content_items = [t for t in all_texts if t is not title_item]
    if not content_items:
        return {"title": title, "content": ""}
    
    paragraphs = []
    current_para = [content_items[0]["text"]]
    prev_bottom = content_items[0]["y_bottom"]
    
    for item in content_items[1:]:
        gap = item["y_top"] - prev_bottom
        avg_h = (item["height"] + content_items[0]["height"]) / 2
        
        if gap > avg_h * 1.2:  # Khoảng cách lớn → đoạn mới
            paragraphs.append(" ".join(current_para))
            current_para = [item["text"]]
        else:
            current_para.append(item["text"])
        prev_bottom = item["y_bottom"]
    
    if current_para:
        paragraphs.append(" ".join(current_para))
    
    content = "\n\n".join(paragraphs)
    
    return {
        "title": title,
        "content": content,
    }
