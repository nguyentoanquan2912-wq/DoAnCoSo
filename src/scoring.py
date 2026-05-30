"""
src/scoring.py — Tính điểm tổng hợp (consensus) từ kết quả của tất cả mô hình.
Cải tiến: weighted voting, ưu tiên ensemble & SVM, phân loại tin tức rõ ràng hơn.
"""


# Trọng số ưu tiên từng model (cao hơn = tin tưởng hơn)
MODEL_WEIGHTS = {
    "svm": 2.0,
}


def compute_consensus(results: dict, text: str = "") -> dict:
    """
    Nhận dict kết quả từ predict_all_models() và tính điểm tổng hợp
    bằng weighted voting (có trọng số theo độ tin cậy của từng model).

    Parameters
    ----------
    results : dict
        Ví dụ: {
            "lr":  {"label": "reliable",   "probability": 92.5, ...},
            "nb":  {"label": "unreliable", "probability": 78.3, ...},
            "svm": {"label": "reliable",   "probability": 88.1, ...},
        }
    text : str
        Văn bản gốc để thực hiện trích xuất dấu hiệu trực tiếp.

    Returns
    -------
    dict với các key:
        - consensus_label         : "reliable" hoặc "unreliable"
        - consensus_display       : chuỗi hiển thị tiếng Việt
        - consensus_badge         : "real" hoặc "fake"
        - avg_probability         : điểm tổng hợp có trọng số (0-100)
        - votes_reliable          : số phiếu có trọng số về reliable
        - votes_unreliable        : số phiếu có trọng số về unreliable
        - total_models            : tổng số model tham gia
        - confidence_level        : mức độ chắc chắn ("cao", "trung bình", "thấp")
        - reliability_score       : điểm tin cậy tổng hợp (0-100)
    """
    if not results:
        return {
            "consensus_label":   "unknown",
            "consensus_display": "Không có dữ liệu",
            "consensus_badge":   "unknown",
            "avg_probability":   0,
            "votes_reliable":    0,
            "votes_unreliable":  0,
            "total_models":      0,
            "confidence_level":  "thấp",
            "reliability_score": 0,
        }

    # ── Weighted voting ──────────────────────────────────────────────
    score_reliable   = 0.0
    score_unreliable = 0.0
    total_weight     = 0.0

    weighted_probs_reliable   = []
    weighted_probs_unreliable = []

    for key, r in results.items():
        w     = MODEL_WEIGHTS.get(key, 1.0)
        label = r.get("label", "unreliable")
        prob  = r.get("probability", 50.0)   # đã ở dạng %

        if label == "reliable":
            score_reliable   += w
            weighted_probs_reliable.append(prob * w)
        else:
            score_unreliable += w
            weighted_probs_unreliable.append(prob * w)

        total_weight += w

    # ── Tỉ lệ phiếu có trọng số ────────────────────────────────────
    ratio_reliable   = score_reliable   / total_weight if total_weight else 0.5
    ratio_unreliable = score_unreliable / total_weight if total_weight else 0.5

    # ── Xác định nhãn chiến thắng ──────────────────────────────────
    is_reliable = ratio_reliable > ratio_unreliable

    # ── Tính điểm xác suất trung bình có trọng số ──────────────────
    if is_reliable and weighted_probs_reliable:
        avg_prob = round(sum(weighted_probs_reliable) / score_reliable, 2)
    elif not is_reliable and weighted_probs_unreliable:
        avg_prob = round(sum(weighted_probs_unreliable) / score_unreliable, 2)
    else:
        # Fallback: trung bình đơn giản
        all_probs = [r.get("probability", 50.0) for r in results.values()]
        avg_prob  = round(sum(all_probs) / len(all_probs), 2)

    # ── Tính reliability_score tổng hợp ────────────────────────────
    # Dựa vào mức độ đồng thuận và điểm xác suất
    consensus_ratio = max(ratio_reliable, ratio_unreliable)  # 0.5 - 1.0
    # Kết hợp: 60% từ xác suất TB + 40% từ tỷ lệ đồng thuận
    reliability_score = round(avg_prob * 0.6 + consensus_ratio * 100 * 0.4, 2)

    # ── Mức độ tự tin ──────────────────────────────────────────────
    if consensus_ratio >= 0.85 and avg_prob >= 80:
        confidence_level = "cao"
    elif consensus_ratio >= 0.65 and avg_prob >= 60:
        confidence_level = "trung bình"
    else:
        confidence_level = "thấp"

    # ── Số model đơn (không trọng số) cho hiển thị ─────────────────
    votes_reliable_raw   = sum(1 for r in results.values() if r.get("label") == "reliable")
    votes_unreliable_raw = sum(1 for r in results.values() if r.get("label") == "unreliable")

    if is_reliable:
        consensus_label   = "reliable"
        consensus_display = "Tin đáng tin cậy"
        consensus_badge   = "real"
    else:
        consensus_label   = "unreliable"
        consensus_display = "Tin có dấu hiệu không đáng tin cậy"
        consensus_badge   = "fake"

    scoring_data = {
        "consensus_label":   consensus_label,
        "consensus_display": consensus_display,
        "consensus_badge":   consensus_badge,
        "avg_probability":   avg_prob,
        "votes_reliable":    votes_reliable_raw,
        "votes_unreliable":  votes_unreliable_raw,
        "total_models":      len(results),
        "confidence_level":  confidence_level,
        "reliability_score": reliability_score,
    }

    # Sinh phần giải thích lý do
    scoring_data["reasoning"] = generate_reasoning(results, scoring_data, text)

    return scoring_data


def generate_reasoning(results: dict, scoring: dict, text: str = "") -> dict:
    """
    Sinh ra phần giải thích lý do tại sao bài viết được phân loại tin thật/giả.
    Trả về dict:
      - summary: str — Tóm tắt lý do kết luận
      - factors: list[dict] — Danh sách các yếu tố phân tích
        Mỗi factor: {icon, title, description, type: 'positive'|'negative'|'neutral'}
      - model_agreement: str — Mô tả mức đồng thuận
      - confidence_explanation: str — Giải thích mức độ tự tin
      - signs: list[dict] — Các dấu hiệu phát hiện
        Mỗi sign: {text, detected: bool}
    """
    total        = scoring.get("total_models", 0)
    reliable     = scoring.get("votes_reliable", 0)
    unreliable   = scoring.get("votes_unreliable", 0)
    avg_prob     = scoring.get("avg_probability", 0)
    conf_level   = scoring.get("confidence_level", "thấp")
    rel_score    = scoring.get("reliability_score", 0)
    label        = scoring.get("consensus_label", "unknown")

    is_reliable = (label == "reliable")
    label_vi    = "tin đáng tin cậy" if is_reliable else "tin không đáng tin cậy"
    majority    = reliable if is_reliable else unreliable

    # ── 1. Summary ──────────────────────────────────────────────────
    summary = (
        f"Bài viết được {majority}/{total} mô hình đánh giá là {label_vi} "
        f"với xác suất trung bình {avg_prob}%. "
        f"Mức độ tự tin của hệ thống: {conf_level}."
    )

    # ── 2. Factors ──────────────────────────────────────────────────
    factors = []

    # Factor 1: Kết quả mô hình Linear SVM
    if avg_prob >= 85:
        factors.append({
            "icon": "✅",
            "title": "Mô hình Linear SVM rất tự tin",
            "description": f"Mô hình Linear SVM đưa ra dự đoán với xác suất {avg_prob}%.",
            "type": "positive",
        })
    elif avg_prob >= 70:
        factors.append({
            "icon": "⚠️",
            "title": "Mô hình Linear SVM khá tự tin",
            "description": f"Mô hình Linear SVM đưa ra dự đoán với xác suất {avg_prob}% — mức chấp nhận được.",
            "type": "neutral",
        })
    else:
        factors.append({
            "icon": "❌",
            "title": "Mô hình Linear SVM ít tự tin",
            "description": f"Xác suất dự đoán chỉ {avg_prob}% — kết quả chưa chắc chắn.",
            "type": "negative",
        })

    # Factor 2: Xác suất trung bình
    if avg_prob >= 85:
        factors.append({
            "icon": "📊",
            "title": "Xác suất dự đoán rất cao",
            "description": f"Xác suất trung bình đạt {avg_prob}%, cho thấy mô hình rất tự tin.",
            "type": "positive",
        })
    elif avg_prob >= 70:
        factors.append({
            "icon": "📊",
            "title": "Xác suất dự đoán khá",
            "description": f"Xác suất trung bình {avg_prob}% — mức độ tin cậy chấp nhận được.",
            "type": "neutral",
        })
    else:
        factors.append({
            "icon": "📊",
            "title": "Xác suất dự đoán thấp",
            "description": f"Xác suất trung bình chỉ {avg_prob}% — cần thận trọng với kết quả.",
            "type": "negative",
        })

    # Factor 3: Reliability score
    if rel_score >= 80:
        factors.append({
            "icon": "🛡️",
            "title": "Điểm tin cậy cao",
            "description": f"Điểm tin cậy tổng hợp: {rel_score}/100.",
            "type": "positive",
        })
    elif rel_score >= 60:
        factors.append({
            "icon": "🛡️",
            "title": "Điểm tin cậy trung bình",
            "description": f"Điểm tin cậy tổng hợp: {rel_score}/100 — mức chấp nhận được.",
            "type": "neutral",
        })
    else:
        factors.append({
            "icon": "🛡️",
            "title": "Điểm tin cậy thấp",
            "description": f"Điểm tin cậy tổng hợp: {rel_score}/100 — cần kiểm chứng thêm.",
            "type": "negative",
        })

    # Factor 4: Mô hình duy nhất
    factors.append({
        "icon": "🤖",
        "title": "Phân tích bởi Linear SVM",
        "description": "Kết quả được đưa ra bởi mô hình Linear SVM — mô hình phân loại văn bản hiệu quả cao.",
        "type": "positive",
    })

    # ── 3. Model agreement ──────────────────────────────────────────
    model_agreement = f"Mô hình Linear SVM đánh giá đây là {label_vi}"

    # ── 4. Confidence explanation ───────────────────────────────────
    if conf_level == "cao":
        confidence_explanation = (
            "Hệ thống có độ tự tin CAO với kết luận này. "
            "Đa số mô hình đồng thuận và xác suất dự đoán vượt ngưỡng tin cậy."
        )
    elif conf_level == "trung bình":
        confidence_explanation = (
            "Hệ thống có độ tự tin TRUNG BÌNH. "
            "Kết quả khá nhất quán nhưng một số mô hình có xác suất không quá cao. "
            "Nên tham khảo thêm nguồn tin khác."
        )
    else:
        confidence_explanation = (
            "Hệ thống có độ tự tin THẤP với kết luận này. "
            "Các mô hình có ý kiến khác nhau hoặc xác suất dự đoán không cao. "
            "Khuyến nghị kiểm chứng bài viết qua nhiều nguồn uy tín."
        )

    # ── 5. Signs (phân tích thực tế dấu hiệu tin giả từ văn bản) ───
    text_lower = text.lower() if text else ""

    # 1. Giọng văn giật gân, cường điệu
    sensational_words = ["sốc", "kinh hoàng", "cực sốc", "rúng động", "cực độ", "bật mí", "tuyệt mật", "sự thật đằng sau", "không thể tin nổi", "vạch trần"]
    has_sensational = any(w in text_lower for w in sensational_words)
    
    # 2. Thiếu nguồn trích dẫn cụ thể
    citation_words = ["theo báo", "cho biết", "phát biểu", "trích dẫn", "nguồn tin", "dẫn lời", "văn bản số", "công văn", "quyết định"]
    has_citation = any(w in text_lower for w in citation_words) or ("http://" in text_lower or "https://" in text_lower)
    
    # 3. Thông tin phản khoa học
    pseudoscience_words = ["thần dược", "bách bệnh", "ung thư hoàn toàn", "chữa khỏi 100%", "bí truyền", "không cần hóa trị", "không cần đi viện", "chữa khỏi hẳn ung thư", "thần y"]
    has_pseudoscience = any(w in text_lower for w in pseudoscience_words)
    
    # 4. Kêu gọi hành động khẩn cấp (share/like)
    urgency_words = ["hãy chia sẻ", "chia sẻ ngay", "share gấp", "chia sẻ rộng rãi", "cứu người", "khẩn cấp", "gấp gấp", "lan tỏa", "đừng im lặng"]
    has_urgency = any(w in text_lower for w in urgency_words)
    
    # 5. Dùng nhiều dấu chấm than/hoa thị
    has_exclamation = ("!!!" in text_lower or text_lower.count("!") >= 3)
    
    # 6. Nguồn tin không rõ ràng
    trusted_sources = ["vtv", "vnexpress", "tuổi trẻ", "tuoi tre", "nhân dân", "nhan dan", "thanh niên", "thanh nien", "dân trí", "dan tri", "chính phủ", "chinh phu", "vietnamnet", "lao động", "lao dong", "vtc", "vietnamplus"]
    has_trusted_source = any(w in text_lower for w in trusted_sources)

    signs = [
        {"text": "Giọng văn giật gân, cường điệu", "detected": has_sensational or (label == "unreliable" and conf_level == "thấp")},
        {"text": "Thiếu nguồn trích dẫn cụ thể", "detected": not has_citation},
        {"text": "Thông tin phản khoa học", "detected": has_pseudoscience},
        {"text": "Kêu gọi hành động khẩn cấp (share/like)", "detected": has_urgency},
        {"text": "Dùng nhiều dấu chấm than/hoa thị", "detected": has_exclamation},
        {"text": "Nguồn tin không rõ ràng", "detected": not has_trusted_source},
    ]

    return {
        "summary":                summary,
        "factors":                factors,
        "model_agreement":        model_agreement,
        "confidence_explanation": confidence_explanation,
        "signs":                  signs,
    }
