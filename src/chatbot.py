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
        import torch
        gpu_available = torch.cuda.is_available()
        _ocr_reader = easyocr.Reader(['vi', 'en'], gpu=gpu_available, verbose=False)
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



# ─── Intent Detection & Smart Conversation ─────────────────────────────────

# Patterns cho nhận diện ý định
GREETING_PATTERNS = [
    r"^(xin\s*)?ch[aà]o", r"^hi\b", r"^hello", r"^hey", r"^alo",
    r"^chào bạn", r"^chào bot", r"^chào ai", r"^bạn ơi",
    r"^ê\b", r"^ơi\b", r"^helu", r"^yo\b",
]

FAREWELL_PATTERNS = [
    r"tạm biệt", r"bye", r"goodbye", r"hẹn gặp lại", r"chào nhé",
    r"cảm ơn.*nhé", r"thanks.*bye", r"thôi nhé", r"kết thúc",
]

THANKS_PATTERNS = [
    r"cảm ơn", r"cám ơn", r"thank", r"tks", r"tkx",
    r"cả?m ơn bạn", r"tuyệt vời", r"hay quá", r"tốt lắm",
    r"giỏi quá", r"ok.*cảm ơn", r"rất hữu ích",
]

HELP_PATTERNS = [
    r"(bạn|bot|ai).*giúp.*gì", r"(bạn|bot|ai).*làm.*gì",
    r"(bạn|bot|ai).*biết.*gì", r"(bạn|bot|ai).*có thể",
    r"hướng dẫn", r"cách (sử dụng|dùng)", r"help",
    r"(bạn|mày).*là.*ai", r"giới thiệu.*bản thân",
]

SYSTEM_QUESTION_PATTERNS = [
    r"(hệ thống|website|trang web|app|ứng dụng).*hoạt động",
    r"(mô hình|model|svm|linear svm).*là gì",
    r"(nlp|xử lý ngôn ngữ).*là gì",
    r"(tf-idf|tfidf).*là gì",
    r"(độ chính xác|accuracy).*bao nhiêu",
    r"dùng.*công nghệ.*gì", r"thuật toán.*gì",
    r"(máy học|machine learning).*là gì",
    r"trustcheck.*là gì",
]

FAKE_NEWS_QUESTION_PATTERNS = [
    r"(tin giả|fake news).*là gì",
    r"(nhận biết|phát hiện|phân biệt).*tin (giả|thật)",
    r"(dấu hiệu|cách).*tin giả",
    r"(tại sao|vì sao).*tin giả",
    r"làm (thế nào|sao).*tin giả",
    r"(kiểm chứng|xác minh).*thông tin",
    r"(lừa đảo|scam).*nhận biết",
    r"nguồn tin.*uy tín",
    r"(báo|trang).*đáng tin",
]

ANALYSIS_TRIGGER_PATTERNS = [
    r"(kiểm tra|phân tích|đánh giá|kiểm chứng|xác minh|thẩm định)",
    r"(tin này|bài này|bài viết|thông tin này).*(?:thật|giả|đáng tin|tin cậy)",
    r"(?:đây|này).*(?:tin thật|tin giả|đáng tin|lừa đảo)",
    r"(tin tức|bài báo|thông tin).*(?:sau|này|trên)",
]

GUIDE_ANALYZE_PATTERNS = [
    r"(cách|hướng dẫn|làm sao|thế nào).*phân tích",
    r"(cách|hướng dẫn|làm sao|thế nào).*kiểm (tra|chứng)",
    r"phân tích.*tin",
    r"làm sao.*kiểm tra",
    r"hướng dẫn.*sử dụng",
    r"cách dùng.*hệ thống",
]

EXPLAIN_SCORE_PATTERNS = [
    r"điểm.*tin cậy",
    r"giải thích.*điểm",
    r"trust.*score",
    r"chỉ số.*tin cậy",
    r"score.*tin cậy",
    r"điểm số.*đánh giá",
    r"tính.*điểm",
]

EXPLAIN_RESULT_PATTERNS = [
    r"(reliable|unreliable)",
    r"(tin thật|tin giả|đáng tin|không đáng tin).*(là gì|nghĩa|ý nghĩa|là sao|phân biệt)",
    r"kết quả.*(có nghĩa|là sao|hiểu|giải thích)",
    r"(tại sao|vì sao).*(tin thật|tin giả|reliable|unreliable)",
]

OCR_HELP_PATTERNS = [
    r"ocr",
    r"quét.*ảnh",
    r"nhận dạng.*chữ",
    r"trích.*(chữ|văn bản).*ảnh",
    r"đọc.*chữ.*ảnh",
    r"tải.*ảnh",
    r"gửi.*ảnh",
    r"chụp.*ảnh",
]

URL_HELP_PATTERNS = [
    r"url",
    r"đường (link|dẫn)",
    r"dán.*link",
    r"dán.*url",
    r"cào.*tin",
]

DASHBOARD_HELP_PATTERNS = [
    r"dashboard",
    r"bảng điều khiển",
    r"thống kê",
    r"biểu đồ",
    r"hiệu suất.*mô hình",
]

HISTORY_HELP_PATTERNS = [
    r"lịch sử",
    r"history",
    r"bài.*đã phân tích",
    r"tin.*đã phân tích",
    r"kết quả.*trước",
]

FACT_CHECK_TIPS_PATTERNS = [
    r"mẹo",
    r"tip",
    r"gợi ý.*kiểm chứng",
    r"lời khuyên.*kiểm chứng",
    r"cách.*xác minh",
    r"phân biệt.*tin thật.*tin giả",
    r"kiểm chứng.*nhanh",
]

FACT_CHECK_CLAIM_PATTERNS = [
    # Tin đồn y tế / chữa bệnh thần kỳ
    r"(chữa|trị|khỏi|hết).*(bệnh|ung thư|covid|tiểu đường|huyết áp|ung bướu)",
    r"(uống|ăn|dùng).*(chữa|trị|khỏi|hết|ngừa|phòng).*(bệnh|ung thư)",
    r"(thần dược|bí truyền|chữa bách bệnh|chữa khỏi 100%|không cần (hóa trị|xạ trị|đi viện))",
    r"(vaccine|vắc xin|vắc-xin).*(gây|nguy hiểm|tự kỷ|chết|tác dụng phụ|chip)",
    r"(thuốc|thảo dược|lá|nước).*(chữa|trị|khỏi|tiêu diệt).*(100%|hoàn toàn|tuyệt đối)",
    r"(bệnh|ung thư|covid).*(chữa|trị).*(bằng|nhờ|với).*(chanh|tỏi|gừng|lá|thảo|rau)",
    
    # Tin đồn tài chính / đầu tư
    r"(bitcoin|crypto|tiền ảo|coin).*(lên|tăng|giảm|sập|triệu|tỷ)",
    r"(đầu tư|kiếm tiền|làm giàu).*(nhanh|dễ|100%|chắc chắn|không rủi ro|triệu|tỷ)",
    r"(trúng thưởng|trúng số|nhận thưởng|nhận tiền).*(miễn phí|ngay|click|link)",
    
    # Tin đồn xã hội giật gân
    r"(sốc|kinh hoàng|rúng động|cực sốc|tuyệt mật|bí mật|vạch trần)",
    r"(share gấp|chia sẻ ngay|lan truyền|đừng im lặng|cứu người|cảnh báo khẩn)",
    
    # Câu hỏi xác minh (có thật không / đúng không)
    r"(có thật|có đúng|có phải|thực sự|thực hư|đúng không|thật không|có thật không)",
    r"(tin này|thông tin này|bài này).*(thật|giả|đúng|sai|tin được|đáng tin)",
]

OUT_OF_SCOPE_PATTERNS = [
    r"(tình yêu|crush|người yêu|bồ|hẹn hò)",         # Bỏ "yêu" đơn lẻ để tránh false positive
    r"(code|lập trình|python|javascript|java|bug|debug)",
    r"(nấu ăn|công thức|recipe|món ăn)",
    r"(thể thao|bóng đá|world cup|ngoại hạng)",
    r"(phim|nhạc|game|anime|manga)",
    r"(toán|lý|hóa|văn|sử|địa|sinh).*lớp",
    r"(viết|soạn|tạo).*(thơ|văn|email|cv|đơn)",
]

SMALLTALK_RESPONSES = {
    "weather": [
        r"thời tiết", r"trời.*nắng", r"trời.*mưa", r"nóng quá", r"lạnh quá",
    ],
    "joke": [
        r"kể.*chuyện.*cười", r"joke", r"hài", r"vui.*đi", r"cười.*đi",
    ],
    "age": [
        r"(bạn|mày|bot).*bao nhiêu tuổi", r"(bạn|mày|bot).*mấy tuổi",
        r"sinh.*năm nào", r"tuổi.*bao nhiêu",
    ],
    "name": [
        r"(bạn|mày|bot).*tên.*gì", r"tên.*bạn", r"(bạn|mày|bot).*là ai",
    ],
}


def _detect_intent(message: str, history: list = None) -> str:
    """Phát hiện ý định của tin nhắn người dùng."""
    msg_lower = message.lower().strip()
    
    # 1. Kiểm tra các ý định kiểm chứng tin đồn / y khoa / tài chính ưu tiên hàng đầu
    for pattern in FACT_CHECK_CLAIM_PATTERNS:
        if re.search(pattern, msg_lower):
            return "analysis"
            
    # 2. Kiểm tra các ý định chuyên sâu khác
    # Hướng dẫn phân tích
    for pattern in GUIDE_ANALYZE_PATTERNS:
        if re.search(pattern, msg_lower):
            return "guide_analyze"
    
    # Giải thích điểm tin cậy
    for pattern in EXPLAIN_SCORE_PATTERNS:
        if re.search(pattern, msg_lower):
            return "explain_score"
    
    # Giải thích reliable/unreliable
    for pattern in EXPLAIN_RESULT_PATTERNS:
        if re.search(pattern, msg_lower):
            return "explain_result"
    
    # Hướng dẫn OCR
    for pattern in OCR_HELP_PATTERNS:
        if re.search(pattern, msg_lower):
            return "ocr_help"
    
    # Hướng dẫn URL
    for pattern in URL_HELP_PATTERNS:
        if re.search(pattern, msg_lower):
            return "url_help"
    
    # Dashboard
    for pattern in DASHBOARD_HELP_PATTERNS:
        if re.search(pattern, msg_lower):
            return "dashboard_help"
    
    # Lịch sử
    for pattern in HISTORY_HELP_PATTERNS:
        if re.search(pattern, msg_lower):
            return "history_help"
    
    # Gợi ý kiểm chứng
    for pattern in FACT_CHECK_TIPS_PATTERNS:
        if re.search(pattern, msg_lower):
            return "fact_check_tips"
            
    # Câu hỏi về hệ thống
    for pattern in SYSTEM_QUESTION_PATTERNS:
        if re.search(pattern, msg_lower):
            return "system_question"
    
    # Câu hỏi về tin giả
    for pattern in FAKE_NEWS_QUESTION_PATTERNS:
        if re.search(pattern, msg_lower):
            return "fake_news_question"

    # 3. Kiểm tra ngoài phạm vi (chỉ khi không phải các ý định cụ thể trên)
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, msg_lower):
            return "out_of_scope"

    # 4. Kiểm tra chào hỏi / tạm biệt / cảm ơn / giúp đỡ (general conversation)
    for pattern in GREETING_PATTERNS:
        if re.search(pattern, msg_lower):
            # Nếu chào + kèm nội dung dài và không khớp các ý định trên → có thể là tin phân tích
            if len(msg_lower) > 50:
                return "analysis"
            return "greeting"
            
    for pattern in FAREWELL_PATTERNS:
        if re.search(pattern, msg_lower):
            return "farewell"
            
    for pattern in THANKS_PATTERNS:
        if re.search(pattern, msg_lower):
            return "thanks"
            
    for pattern in HELP_PATTERNS:
        if re.search(pattern, msg_lower):
            return "help"
            
    # 5. Smalltalk
    for category, patterns in SMALLTALK_RESPONSES.items():
        for pattern in patterns:
            if re.search(pattern, msg_lower):
                return f"smalltalk_{category}"
    
    # 6. Yêu cầu phân tích rõ ràng
    for pattern in ANALYSIS_TRIGGER_PATTERNS:
        if re.search(pattern, msg_lower):
            return "analysis"
    
    # Nếu tin nhắn dài (>80 ký tự) → khả năng cao là nội dung cần phân tích
    if len(message) > 80:
        return "analysis"
    
    # Nếu là câu hỏi ngắn → trả lời tự nhiên
    if msg_lower.endswith("?") or msg_lower.startswith(("tại sao", "vì sao", "làm sao", "thế nào", "khi nào", "ở đâu", "ai ", "gì ")):
        return "general_question"
    
    # Mặc định: nếu ngắn thì hội thoại, nếu dài thì phân tích
    if len(message) <= 50:
        return "general_question"
    return "analysis"


def _get_greeting_response(message: str, history: list = None) -> str:
    """Tạo phản hồi chào hỏi tự nhiên."""
    import random
    
    is_returning = history and len(history) > 0
    
    greetings = [
        "Xin chào bạn! 👋 Tôi là **Trợ lý AI TrustCheck**, rất vui được gặp bạn!\n\nTôi có thể giúp bạn:\n- 🔍 **Kiểm chứng tin tức** — dán bài viết bất kỳ\n- 🧠 **Giải đáp thắc mắc** về tin giả, cách nhận biết\n- 📊 **Phân tích ngôn ngữ** — phát hiện văn phong giật gân\n\nBạn cần tôi hỗ trợ gì nào? 😊",
        "Chào bạn! 😊 Tôi là **TrustCheck AI** — trợ lý kiểm chứng tin tức thông minh.\n\nBạn có thể:\n- Dán nội dung bài báo để tôi **phân tích độ tin cậy**\n- Hỏi tôi bất kỳ câu hỏi nào về **tin giả, lừa đảo**\n- Nhờ tôi **giải thích** cách phát hiện thông tin sai lệch\n\nHãy bắt đầu thôi nào! 🚀",
        "Hello! 🤖 Tôi là trợ lý AI của TrustCheck, sẵn sàng giúp bạn kiểm chứng thông tin!\n\nCứ thoải mái gửi bài viết, tin nhắn đáng ngờ, hay hỏi bất kỳ câu hỏi gì — tôi sẽ giúp bạn phân tích nhé! 💪",
    ]
    
    returning_greetings = [
        "Chào bạn quay lại! 😊 Rất vui được gặp lại bạn. Hôm nay tôi có thể giúp gì cho bạn?",
        "Welcome back! 🤖 Bạn cần tôi kiểm chứng thông tin gì mới không?",
        "Chào lại bạn nhé! 👋 Sẵn sàng hỗ trợ bạn tiếp. Có gì cần giúp không?",
    ]
    
    if is_returning:
        return random.choice(returning_greetings)
    return random.choice(greetings)


def _get_farewell_response() -> str:
    """Tạo phản hồi tạm biệt."""
    import random
    responses = [
        "Tạm biệt bạn! 👋 Nhớ quay lại nếu cần kiểm chứng thông tin nhé. Chúc bạn một ngày tuyệt vời! 😊",
        "Bye bye! 🤗 Hẹn gặp lại bạn. Luôn nhớ **kiểm chứng trước khi chia sẻ** nhé! 🛡️",
        "Chào bạn nhé! 👋 Rất vui đã được hỗ trợ. Nếu có bài viết nào cần kiểm tra, cứ quay lại nha! 💪",
    ]
    return random.choice(responses)


def _get_thanks_response() -> str:
    """Tạo phản hồi cảm ơn."""
    import random
    responses = [
        "Không có gì đâu bạn! 😊 Rất vui vì đã giúp được bạn. Nếu cần gì thêm thì cứ hỏi nhé!",
        "Cảm ơn bạn đã sử dụng TrustCheck! 🙏 Tôi luôn sẵn sàng hỗ trợ bạn. Cứ thoải mái hỏi bất cứ lúc nào!",
        "Hehe, vui lắm! 😄 Nếu bạn thấy có ích thì nhớ chia sẻ TrustCheck cho bạn bè nhé. Mỗi người kiểm chứng thông tin là góp phần vào một cộng đồng tốt hơn! 🌟",
    ]
    return random.choice(responses)


def _get_help_response() -> str:
    """Tạo phản hồi hướng dẫn sử dụng."""
    return """### 🤖 Tôi là Trợ lý AI TrustCheck — đây là những gì tôi có thể giúp bạn:

**1. 🔍 Kiểm chứng tin tức**
Dán tiêu đề hoặc nội dung bài viết bất kỳ, tôi sẽ phân tích:
- Độ tin cậy bằng mô hình **Linear SVM**
- Phát hiện từ ngữ **giật gân, cường điệu**
- Đối chiếu **cơ sở dữ liệu** lịch sử

**2. 💬 Hỏi đáp tự nhiên**
Bạn có thể hỏi tôi bất kỳ điều gì, ví dụ:
- *"Tin giả là gì?"*
- *"Làm sao nhận biết tin lừa đảo?"*
- *"Website này hoạt động như thế nào?"*

**3. 🧠 Tư vấn chuyên sâu**
- Phân tích **văn phong báo chí** vs **tin đồn**
- Hướng dẫn **kiểm chứng chéo** từ nhiều nguồn
- Giải thích các **dấu hiệu** của thông tin sai lệch

**💡 Mẹo:** Bạn cũng có thể sử dụng trang [Phân tích tin tức](/analyzer) để nhận kết quả chi tiết hơn với biểu đồ và báo cáo đầy đủ!"""


def _get_system_answer(message: str) -> str:
    """Trả lời câu hỏi về hệ thống."""
    msg_lower = message.lower()
    
    if re.search(r"(mô hình|model|svm|linear svm)", msg_lower):
        return """### 🤖 Về mô hình Linear SVM

**Linear SVM** (Support Vector Machine tuyến tính) là thuật toán Máy học (Machine Learning) được TrustCheck sử dụng để phân loại tin tức.

**Cách hoạt động:**
1. Văn bản được **tiền xử lý** bằng NLP tiếng Việt (underthesea) — tách từ, loại bỏ từ dừng
2. Chuyển đổi thành vector số bằng **TF-IDF** (Term Frequency - Inverse Document Frequency)
3. Mô hình **Linear SVM** phân loại dựa trên siêu phẳng tối ưu trong không gian đặc trưng

**Tại sao chọn Linear SVM?**
- 🎯 Hiệu suất **cao nhất** trong phân loại văn bản tiếng Việt
- ⚡ Tốc độ **nhanh**, phù hợp cho ứng dụng thời gian thực
- 📊 Xử lý tốt **không gian đặc trưng thưa thớt** (nhiều từ, ít tần suất)

Bạn muốn biết thêm chi tiết nào không? 😊"""
    
    if re.search(r"(nlp|xử lý ngôn ngữ)", msg_lower):
        return """### 📝 NLP — Xử lý Ngôn ngữ Tự nhiên

**NLP** (Natural Language Processing) là công nghệ giúp máy tính **hiểu và phân tích ngôn ngữ** con người.

**TrustCheck sử dụng NLP cho:**
- **Tách từ tiếng Việt** (word segmentation) bằng thư viện *underthesea*
- **Loại bỏ từ dừng** (stop words) — những từ không mang nghĩa phân loại
- **Phân tích ngữ nghĩa** — phát hiện cấu trúc câu, từ khóa giật gân
- **Vector hóa TF-IDF** — chuyển văn bản thành dạng số để mô hình ML xử lý

**Ví dụ:**
- Câu *"KHẨN CẤP!!! Share ngay kẻo muộn!!!"* → NLP phát hiện: từ giật gân, nhiều dấu chấm than
- Câu *"Theo Bộ Y tế cho biết, kết quả nghiên cứu..."* → NLP phát hiện: có trích dẫn nguồn uy tín

Cần giải thích thêm gì không bạn? 🤓"""
    
    if re.search(r"(tf-idf|tfidf)", msg_lower):
        return """### 📊 TF-IDF là gì?

**TF-IDF** (Term Frequency - Inverse Document Frequency) là phương pháp chuyển đổi văn bản thành **vector số** để mô hình ML có thể xử lý.

**Công thức đơn giản:**
- **TF** (Term Frequency): Từ xuất hiện **bao nhiêu lần** trong bài viết?
- **IDF** (Inverse Document Frequency): Từ đó **hiếm** hay **phổ biến** trong toàn bộ tập dữ liệu?
- **TF-IDF = TF × IDF** → Từ quan trọng có giá trị cao

**Ý nghĩa:**
- Từ xuất hiện nhiều trong bài NHƯNG hiếm trong tập dữ liệu → **rất quan trọng** (TF-IDF cao)
- Từ phổ biến như "và", "là", "của" → **ít quan trọng** (TF-IDF thấp)

Nhờ TF-IDF, mô hình Linear SVM có thể nhận ra **pattern đặc trưng** của tin giả vs tin thật! 🎯"""
    
    if re.search(r"(độ chính xác|accuracy|bao nhiêu phần trăm)", msg_lower):
        return """### 📈 Độ chính xác của TrustCheck

Mô hình **Linear SVM** của TrustCheck đạt hiệu suất:
- 🎯 **Accuracy**: ~93-95% trên tập test
- 📊 **Precision**: Tỷ lệ dự đoán đúng cao
- 🔄 **Recall**: Phát hiện được phần lớn tin giả

**Lưu ý quan trọng:**
- Kết quả phân tích chỉ mang tính **tham khảo**
- Nên **đối chiếu chéo** với nhiều nguồn báo chính thống
- Mô hình hoạt động tốt nhất với **tin tức tiếng Việt**

Bạn có thể xem chi tiết hiệu suất mô hình tại trang [Dashboard](/dashboard) 📊"""
    
    if re.search(r"(trustcheck|hệ thống|website|trang web).*(?:là gì|hoạt động|về)", msg_lower):
        return """### 🛡️ Giới thiệu TrustCheck AI

**TrustCheck AI** là hệ thống **phát hiện tin giả tiếng Việt** sử dụng trí tuệ nhân tạo.

**Quy trình hoạt động:**
1. 📝 Bạn nhập **tiêu đề/nội dung** bài viết, hoặc **URL bài báo**
2. 🤖 Hệ thống xử lý bằng **NLP tiếng Việt** (underthesea + TF-IDF)
3. ⚡ Mô hình **Linear SVM** phân loại tin thật/giả
4. 📋 Trả về kết quả kèm **giải thích lý do chi tiết**

**Tính năng nổi bật:**
- 🔍 Phân tích bài viết bằng ML
- 🌐 Cào nội dung tự động từ URL (VNExpress, Tuổi Trẻ...)
- 🖼️ Trích xuất văn bản từ ảnh bằng EasyOCR
- 📊 Dashboard thống kê hiệu suất
- 💬 Trợ lý AI hỗ trợ kiểm chứng (chính là tôi đây! 😊)

**Hoàn toàn nội bộ** — không gửi dữ liệu ra bên ngoài! 🔒"""
    
    # Câu hỏi chung về công nghệ
    return """### ⚙️ Công nghệ sử dụng trong TrustCheck

TrustCheck AI được xây dựng trên nền tảng:
- **Python** + **Flask** — Backend web framework
- **scikit-learn** — Thư viện Máy học, bao gồm Linear SVM
- **underthesea** — NLP cho tiếng Việt (tách từ, nhận dạng thực thể)
- **TF-IDF** — Vector hóa văn bản
- **EasyOCR** — Trích xuất văn bản từ ảnh
- **SQLite** — Cơ sở dữ liệu lưu lịch sử
- **BeautifulSoup** — Cào dữ liệu từ trang web

Tất cả chạy **hoàn toàn cục bộ** trên máy chủ nội bộ, không cần API Key bên ngoài! 🔒

Bạn muốn tìm hiểu sâu hơn về phần nào? 🤓"""


def _get_fake_news_answer(message: str) -> str:
    """Trả lời câu hỏi liên quan đến tin giả."""
    msg_lower = message.lower()
    
    if re.search(r"(tin giả|fake news).*là gì", msg_lower):
        return """### 🚨 Tin giả (Fake News) là gì?

**Tin giả** là thông tin **sai sự thật** được tạo ra và lan truyền có chủ đích, thường nhằm mục đích:
- 💰 **Lợi nhuận** — câu view, click quảng cáo
- 🎭 **Thao túng** — định hướng dư luận, gây hoang mang
- 😈 **Lừa đảo** — chiếm đoạt tài sản, thông tin cá nhân

**Các dạng tin giả phổ biến:**
1. **Tin bịa đặt hoàn toàn** — không có cơ sở thực tế
2. **Tin xuyên tạc** — lấy sự kiện thật nhưng bóp méo chi tiết
3. **Tin cắt ghép** — ghép ảnh/video không liên quan với tiêu đề giật gân
4. **Tin đồn y tế** — "thuốc thần", "chữa bách bệnh" không có căn cứ khoa học
5. **Lừa đảo tài chính** — "trúng thưởng", "đầu tư siêu lợi nhuận"

**Tác hại:**
- Gây hoang mang xã hội
- Thiệt hại tài chính cho nạn nhân
- Ảnh hưởng sức khỏe cộng đồng
- Xói mòn niềm tin vào báo chí

Bạn muốn biết cách nhận biết tin giả không? 🔍"""
    
    if re.search(r"(nhận biết|phát hiện|phân biệt|dấu hiệu).*tin (giả|thật|lừa|sai)", msg_lower):
        return """### 🔍 Cách nhận biết tin giả

**10 dấu hiệu phổ biến của tin giả:**

**📝 Về nội dung:**
1. **Tiêu đề giật gân** — "CỰC SỐC!!!", "CHIA SẺ NGAY!!!", "KHÔNG THỂ TIN NỔI"
2. **Thiếu nguồn dẫn** — không trích dẫn cơ quan, chuyên gia cụ thể
3. **Ngôn từ cảm tính** — kêu gọi sợ hãi, tức giận, hoang mang
4. **Thông tin phi logic** — "chữa khỏi 100% ung thư bằng tỏi"
5. **Hứa hẹn phi thực tế** — "làm giàu nhanh", "trúng thưởng miễn phí"

**🌐 Về nguồn gốc:**
6. **Trang web lạ** — tên miền giả mạo, không phải báo chính thống
7. **Không có tác giả** — bài viết ẩn danh, không rõ ai viết
8. **Chỉ lan truyền trên MXH** — không thấy trên báo chính thống nào
9. **Ảnh/video cắt ghép** — hình ảnh không khớp với nội dung
10. **Yêu cầu hành động gấp** — "share ngay", "chuyển tiền ngay"

**✅ Cách kiểm chứng:**
- Tìm tiêu đề trên **Google** xem có báo nào đưa tin
- Đối chiếu ít nhất **2-3 nguồn** báo chính thống
- Kiểm tra trang web nguồn có phải **báo chính thức** không
- Sử dụng **TrustCheck AI** để phân tích tự động! 🤖

Bạn có bài viết nào cần kiểm tra không? Cứ dán vào đây nhé! 💪"""
    
    if re.search(r"(lừa đảo|scam).*nhận biết", msg_lower):
        return """### 🚨 Nhận biết tin lừa đảo trực tuyến

**Các kiểu lừa đảo phổ biến:**

**1. 🎁 Lừa trúng thưởng**
- "Chúc mừng bạn trúng iPhone 15 Pro Max!"
- Yêu cầu nhập thông tin tài khoản, mã OTP
- ➡️ **Dấu hiệu**: Không có cuộc thi nào, link lạ, yêu cầu phí nhận giải

**2. 🏦 Giả danh ngân hàng/cơ quan**
- "Tài khoản của bạn bị khóa, click vào đây..."
- ➡️ **Dấu hiệu**: Link không phải tên miền chính thức, đe dọa

**3. 💰 Đầu tư siêu lợi nhuận**
- "Lãi suất 30%/tháng, không rủi ro"
- ➡️ **Dấu hiệu**: Lợi nhuận phi thực tế, kêu gọi nạp tiền gấp

**4. 💊 Thuốc thần/chữa bách bệnh**
- "Uống nước lá X chữa khỏi ung thư giai đoạn cuối"
- ➡️ **Dấu hiệu**: Không có nghiên cứu khoa học, bán hàng kèm theo

**🛡️ Nguyên tắc bảo vệ bản thân:**
- ❌ **Không click** link lạ
- ❌ **Không chia sẻ** mã OTP, số thẻ, mật khẩu
- ❌ **Không chuyển tiền** cho người lạ
- ✅ **Luôn kiểm chứng** trước khi tin

Gửi tin nhắn đáng ngờ cho tôi phân tích nhé! 🔍"""
    
    if re.search(r"nguồn tin.*uy tín|báo.*đáng tin", msg_lower):
        return """### 📰 Nguồn tin uy tín tại Việt Nam

**Báo chính thống:**
- 📺 **VTV** — Đài Truyền hình Việt Nam
- 📰 **VNExpress** — vnexpress.net
- 📰 **Tuổi Trẻ** — tuoitre.vn
- 📰 **Thanh Niên** — thanhnien.vn
- 📰 **Nhân Dân** — nhandan.vn
- 📰 **Dân Trí** — dantri.com.vn
- 📰 **VietnamNet** — vietnamnet.vn

**Cơ quan nhà nước:**
- 🏛️ **Cổng TTĐT Chính phủ** — chinhphu.vn
- 🏥 **Bộ Y tế** — moh.gov.vn
- 🔒 **Bộ Công an** — bocongan.gov.vn

**Nguồn quốc tế uy tín:**
- 🌍 **Reuters**, **BBC**, **AP News**
- 🏥 **WHO** (Tổ chức Y tế Thế giới)

**⚠️ Nguồn KHÔNG uy tín:**
- Group Facebook cá nhân
- Kênh TikTok, YouTube không xác minh
- Trang blog, diễn đàn ẩn danh
- Tin nhắn Zalo lan truyền

Khi đọc tin, hãy luôn kiểm tra **nguồn gốc** trước nhé! 🛡️"""
    
    # Trả lời chung về tin giả
    return """### 💡 Về vấn đề tin giả

Tin giả là vấn đề nghiêm trọng trong thời đại số. Một vài điều cần biết:

- 📊 **70-80%** tin giả lan truyền qua mạng xã hội
- ⚡ Tin giả lan truyền **nhanh gấp 6 lần** so với tin thật
- 🧠 Tin giả thường đánh vào **cảm xúc** — sợ hãi, phẫn nộ, tò mò

**Cách bảo vệ bản thân:**
1. Luôn **kiểm chứng** trước khi chia sẻ
2. Đối chiếu với **nhiều nguồn** báo chính thống
3. Cẩn thận với tiêu đề **giật gân, cảm xúc**
4. Sử dụng **TrustCheck AI** để phân tích nhanh! 🤖

Bạn cần hỏi cụ thể hơn về vấn đề gì? Tôi sẵn sàng giúp! 😊"""


def _get_smalltalk_response(category: str) -> str:
    """Trả lời các câu hỏi smalltalk."""
    import random
    
    responses = {
        "weather": [
            "Haha, tôi là AI nên không cảm nhận được thời tiết đâu bạn ơi! 😄 Nhưng tôi có thể giúp bạn **kiểm chứng tin tức** — đó mới là sở trường của tôi! 🔍",
            "Tôi sống trong server nên không biết thời tiết bên ngoài thế nào 😅 Nhưng nếu bạn thấy tin \"Bão cấp 15 đổ bộ ngày mai\" thì hãy gửi cho tôi kiểm tra nhé! 🌪️",
        ],
        "joke": [
            "Để tôi kể nhé: *\"Tại sao AI không bao giờ buồn? Vì nó luôn xử lý mọi thứ một cách... logic!\"* 😄\n\nOk, joke của AI hơi khô, nhưng tôi phân tích tin giả thì rất giỏi đó nha! 🤖",
            "Hmm, tôi kể chuyện cười thì không giỏi lắm, nhưng tôi có thể khiến tin giả \"khóc\" vì bị phát hiện! 😎 Gửi bài viết đáng ngờ cho tôi nhé!",
        ],
        "age": [
            "Tôi là AI nên không có tuổi theo nghĩa thông thường 😊 Nhưng TrustCheck được phát triển từ năm 2024, nên tôi cũng còn khá \"trẻ\" đó! 🤖\n\nCòn bạn, có tin tức nào cần kiểm chứng không?",
        ],
        "name": [
            "Tôi là **TrustCheck AI** — trợ lý kiểm chứng tin tức thông minh! 🤖\n\nNhiệm vụ của tôi là giúp bạn phân biệt **tin thật** và **tin giả** bằng công nghệ Máy học và NLP tiếng Việt.\n\nRất vui được làm quen! Bạn tên gì nè? 😊",
        ],
    }
    
    return random.choice(responses.get(category, ["Hmm, câu hỏi thú vị! 🤔 Nhưng chuyên môn của tôi là kiểm chứng tin tức. Bạn có bài viết nào cần phân tích không?"]))


def _get_guide_analyze_response() -> str:
    """Hướng dẫn cách phân tích tin tức."""
    import random
    responses = [
        "Để phân tích một bài viết, bạn có thể làm theo các bước sau:\n\n1. 📝 Truy cập trang [Phân tích tin tức](/analyzer)\n2. 📋 Dán **tiêu đề** và **nội dung** bài viết vào form\n3. 🔗 Hoặc dán **URL bài báo** để hệ thống tự động cào nội dung\n4. ⚡ Nhấn **Phân tích** — hệ thống sẽ trả về kết quả chi tiết\n\nBạn cũng có thể dán trực tiếp nội dung vào đây, mình sẽ phân tích ngay cho bạn! 😊",
        "Mình hướng dẫn bạn nhé! Có 3 cách để kiểm chứng tin tức:\n\n1. 📋 **Dán nội dung** bài viết trực tiếp vào đây hoặc trang [Phân tích](/analyzer)\n2. 🔗 **Dán đường link** bài báo — hệ thống sẽ tự cào nội dung\n3. 🖼️ **Gửi ảnh** chứa văn bản — hệ thống dùng OCR để đọc\n\nSau khi phân tích, bạn sẽ nhận được điểm tin cậy và giải thích chi tiết. Thử ngay nhé! 💪",
    ]
    return random.choice(responses)


def _get_explain_score_response() -> str:
    """Giải thích điểm tin cậy."""
    return """**Điểm tin cậy** là chỉ số đánh giá mức độ đáng tin của một bài viết, tính trên thang **0–100%**.

- 🟢 **70–100%**: Đáng tin cậy — bài viết có nguồn rõ ràng, văn phong khách quan
- 🟡 **45–69%**: Chưa xác minh — cần kiểm chứng thêm từ nguồn khác
- 🔴 **Dưới 45%**: Có dấu hiệu tin giả — phát hiện từ ngữ giật gân, thiếu nguồn dẫn

Điểm được tính dựa trên: từ khóa giật gân, nguồn trích dẫn, độ dài bài viết, và mô hình ML. Bạn muốn thử phân tích một bài viết không? 😊"""


def _get_explain_result_response() -> str:
    """Giải thích kết quả reliable/unreliable."""
    return """Kết quả phân tích của TrustCheck gồm 2 nhãn chính:

- ✅ **Reliable (Đáng tin cậy)**: Bài viết có cấu trúc rõ ràng, trích dẫn nguồn uy tín, văn phong khách quan và không có dấu hiệu giật gân.
- 🚨 **Unreliable (Không đáng tin)**: Bài viết chứa từ ngữ cảm tính, thiếu nguồn dẫn, hoặc có dấu hiệu thao túng thông tin.

Kết quả chỉ mang tính **tham khảo** — bạn nên đối chiếu thêm với 2–3 nguồn báo chính thống để chắc chắn hơn nhé! 🔍"""


def _get_ocr_help_response() -> str:
    """Hướng dẫn sử dụng OCR."""
    return """Tính năng **OCR (Nhận dạng ký tự quang học)** giúp bạn trích xuất văn bản từ ảnh để phân tích.

Cách sử dụng:
1. 📸 Chụp ảnh hoặc screenshot bài viết cần kiểm chứng
2. 🖼️ Vào trang [Phân tích tin tức](/analyzer), chọn tab **OCR ảnh**
3. 📤 Tải ảnh lên — hệ thống sẽ tự động đọc văn bản bằng **EasyOCR**
4. ⚡ Sau khi trích xuất, nội dung sẽ được phân tích độ tin cậy ngay

Hệ thống hỗ trợ tiếng Việt và tiếng Anh, xử lý hoàn toàn cục bộ trên máy chủ. Thử gửi ảnh nhé! 📷"""


def _get_url_help_response() -> str:
    """Hướng dẫn phân tích URL."""
    return """Để phân tích một bài báo từ đường link, bạn làm như sau:

1. 🔗 Sao chép **URL** bài báo (ví dụ: `https://vnexpress.net/...`)
2. 📋 Dán vào ô **URL bài báo** trên trang [Phân tích tin tức](/analyzer)
3. ⚡ Nhấn **Phân tích** — hệ thống sẽ tự động cào tiêu đề và nội dung
4. 📊 Kết quả phân tích sẽ hiển thị ngay sau vài giây

Hệ thống hỗ trợ các trang báo phổ biến như VNExpress, Tuổi Trẻ, Thanh Niên, Dân Trí và nhiều trang khác. Bạn thử dán link bài báo vào đây cũng được nhé! 🔍"""


def _get_dashboard_help_response() -> str:
    """Giải thích Dashboard."""
    return """Trang [Dashboard](/dashboard) hiển thị thống kê tổng quan về hệ thống TrustCheck:

- 📊 **Hiệu suất mô hình**: Accuracy, Precision, Recall, F1-score của Linear SVM
- 📈 **Biểu đồ phân bố**: Tỷ lệ tin thật vs tin giả trong dữ liệu huấn luyện
- 🔄 **Ma trận nhầm lẫn**: Chi tiết phân loại đúng/sai của mô hình

Bạn có thể truy cập Dashboard bất cứ lúc nào để theo dõi hiệu suất phân tích. Cần mình giải thích thêm chỉ số nào không? 😊"""


def _get_history_help_response() -> str:
    """Hướng dẫn xem lịch sử."""
    return """Trang [Lịch sử](/history) lưu lại tất cả các bài viết bạn đã phân tích trước đó.

Tại đây bạn có thể:
- 📋 **Xem lại** kết quả phân tích cũ
- 🔍 **Tìm kiếm** theo tiêu đề hoặc nội dung
- 🗑️ **Xoá** từng mục hoặc toàn bộ lịch sử

Dữ liệu lịch sử được lưu trong cơ sở dữ liệu SQLite nội bộ, hoàn toàn riêng tư. Truy cập ngay tại [đây](/history) nhé! 📂"""


def _get_fact_check_tips_response() -> str:
    """Gợi ý cách kiểm chứng nguồn tin."""
    import random
    responses = [
        "Đây là **5 bước kiểm chứng nhanh** mà mình khuyên bạn:\n\n1. 🔍 **Google tiêu đề** — xem có báo chính thống nào đưa tin không\n2. 📰 **Đối chiếu 2–3 nguồn** — VTV, VNExpress, Tuổi Trẻ, Thanh Niên\n3. 👤 **Kiểm tra tác giả** — bài viết có ghi rõ người viết không?\n4. 📅 **Xem ngày đăng** — tin cũ đôi khi bị chia sẻ lại gây hiểu lầm\n5. 🤖 **Dùng TrustCheck** — dán nội dung vào [Phân tích](/analyzer) để AI đánh giá\n\nNhớ: *Kiểm chứng trước, chia sẻ sau* nhé! 🛡️",
        "Mình chia sẻ vài mẹo kiểm chứng tin tức nhé:\n\n- ⚠️ **Cẩn thận tiêu đề giật gân** — nếu quá sốc, có thể là bẫy click\n- 🔗 **Kiểm tra nguồn gốc** — tin đến từ đâu? Facebook, Zalo hay báo chính thống?\n- 🖼️ **Tra ảnh ngược** — dùng Google Images để kiểm tra ảnh có bị cắt ghép\n- 📊 **Dùng TrustCheck** — dán bài viết vào đây, mình phân tích ngay cho bạn\n\nBạn có bài viết nào đang nghi ngờ không? Gửi cho mình nhé! 💪",
    ]
    return random.choice(responses)


def _get_out_of_scope_response() -> str:
    """Trả lời câu hỏi ngoài phạm vi."""
    import random
    responses = [
        "Cảm ơn bạn đã hỏi, nhưng mình chuyên về **kiểm chứng tin tức** thôi nè! 😊 Nếu bạn đang đọc được một tin tức nào đó đáng ngờ, hãy gửi cho mình để phân tích nhé.",
        "Hmm, câu hỏi này nằm ngoài chuyên môn của mình rồi 😅 Mình là trợ lý kiểm chứng tin tức — nếu bạn muốn kiểm tra độ tin cậy của một bài viết, cứ dán nội dung hoặc link vào đây nhé!",
        "Mình không rành lĩnh vực này lắm, nhưng mình rất giỏi **phân tích tin tức** đó! 🤖 Bạn có bài viết nào cần kiểm chứng không? Gửi cho mình nha.",
        "Câu hỏi thú vị, nhưng mình tập trung vào việc **đánh giá độ tin cậy tin tức** thôi bạn nhé. Thử gửi một bài báo hoặc tin đồn để mình phân tích xem sao! 🔍",
    ]
    return random.choice(responses)


def _get_general_response(message: str, history: list = None) -> str:
    """Trả lời câu hỏi chung dựa trên ngữ cảnh."""
    msg_lower = message.lower().strip()
    
    # Câu hỏi có/không đơn giản
    if msg_lower in ["có", "không", "ok", "ừ", "ờ", "đúng", "sai", "được", "oke"]:
        if history and len(history) >= 2:
            last_bot = history[-1].get("content", "") if history[-1].get("role") == "assistant" else ""
            if "bạn muốn" in last_bot.lower() or "bạn cần" in last_bot.lower():
                if msg_lower in ["có", "ừ", "ờ", "đúng", "được", "ok", "oke"]:
                    return "Tuyệt vời! Hãy gửi nội dung bài viết hoặc câu hỏi cho tôi nhé! 😊"
                else:
                    return "OK bạn! Nếu cần gì thì cứ hỏi tôi bất cứ lúc nào nhé! 🤖"
        return "Bạn có thể nói rõ hơn được không? Tôi sẵn sàng hỗ trợ bạn! 😊"
    
    # Câu hỏi về khả năng
    if re.search(r"(bạn|bot|ai).*có.*thể", msg_lower):
        return _get_help_response()
    
    # Nhận xét/bình luận
    if re.search(r"(hay|tốt|giỏi|tuyệt|đỉnh|ghê|pro)", msg_lower):
        return "Cảm ơn bạn! 😊 Tôi luôn cố gắng hỗ trợ tốt nhất. Nếu có bài viết nào cần kiểm chứng, cứ gửi cho tôi nhé! 💪"
    
    # Không hiểu → fallback tự nhiên
    import random
    fallback_responses = [
        "Mình có thể hỗ trợ bạn kiểm tra độ tin cậy của tin tức. Bạn có thể gửi nội dung bài viết, URL hoặc ảnh chứa văn bản để mình phân tích nhé! 🔍",
        "Nếu bạn đang muốn kiểm chứng một tin tức, hãy dán nội dung hoặc đường link bài báo để hệ thống phân tích. Mình sẵn sàng hỗ trợ! 😊",
        "Mình chưa rõ ý bạn lắm, nhưng nếu bạn cần kiểm chứng thông tin, cứ gửi tiêu đề, nội dung hoặc nguồn bài viết cho mình nhé! 📝",
        "Bạn ơi, mình chuyên về kiểm chứng tin tức nè! Thử dán một bài viết, link bài báo, hoặc hỏi mình về cách phân biệt tin thật — tin giả xem sao? 🤖",
        "Mình có thể giúp bạn phân tích độ tin cậy của bất kỳ bài viết nào. Bạn muốn bắt đầu với nội dung nào không? 💪",
    ]
    return random.choice(fallback_responses)


def chat_response(message: str, history: list = None) -> str:
    """
    Xử lý chat thông minh — phát hiện ý định và phản hồi tự nhiên.
    Sử dụng hoàn toàn engine NLP cục bộ, không cần API Key bên ngoài.
    """
    if not message or not message.strip():
        return "Bạn chưa nhập nội dung tin nhắn. Hãy gửi bài viết hoặc câu hỏi cho tôi nhé! 😊"
    
    # Phát hiện ý định
    intent = _detect_intent(message, history)
    
    # Phản hồi theo ý định
    if intent == "greeting":
        return _get_greeting_response(message, history)
    
    if intent == "farewell":
        return _get_farewell_response()
    
    if intent == "thanks":
        return _get_thanks_response()
    
    if intent == "help":
        return _get_help_response()
    
    if intent == "guide_analyze":
        return _get_guide_analyze_response()
    
    if intent == "explain_score":
        return _get_explain_score_response()
    
    if intent == "explain_result":
        return _get_explain_result_response()
    
    if intent == "ocr_help":
        return _get_ocr_help_response()
    
    if intent == "url_help":
        return _get_url_help_response()
    
    if intent == "dashboard_help":
        return _get_dashboard_help_response()
    
    if intent == "history_help":
        return _get_history_help_response()
    
    if intent == "fact_check_tips":
        return _get_fact_check_tips_response()
    
    if intent == "out_of_scope":
        return _get_out_of_scope_response()
    
    if intent == "system_question":
        return _get_system_answer(message)
    
    if intent == "fake_news_question":
        return _get_fake_news_answer(message)
    
    if intent.startswith("smalltalk_"):
        category = intent.replace("smalltalk_", "")
        return _get_smalltalk_response(category)
    
    if intent == "general_question":
        return _get_general_response(message, history)
    
    # ═══ PHÂN TÍCH TIN TỨC (intent == "analysis") ═══
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
    
    # Tối ưu kích thước ảnh (giới hạn tối đa 1200px) để tăng tốc độ xử lý OCR
    max_size = 1200
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            resample_filter = Image.LANCZOS
        image = image.resize(new_size, resample_filter)
    
    # Chuyển PIL Image → numpy array
    import numpy as np
    image_np = np.array(image)
    
    # OCR bằng EasyOCR với các tham số tối ưu tốc độ
    reader = _get_ocr_reader()
    results = reader.readtext(image_np, detail=1, canvas_size=1200, adjust_contrast=False)
    
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
