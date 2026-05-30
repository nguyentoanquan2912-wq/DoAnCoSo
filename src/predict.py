import os
import joblib

from src.preprocess import clean_text


BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models")

MODEL_DISPLAY_NAMES = {
    "svm": "Linear SVM",
}

_vectorizer = None
_models     = {}
_last_load_time = 0.0


def _load_all():
    """Load vectorizer và tất cả models (gọi 1 lần khi import)."""
    global _vectorizer, _models, _last_load_time

    vec_path = os.path.join(MODEL_DIR, "vectorizer.pkl")
    if not os.path.exists(vec_path):
        raise FileNotFoundError(
            "❌ Chưa tìm thấy model. Vui lòng chạy: python -m src.train"
        )

    _vectorizer = joblib.load(vec_path)
    _last_load_time = os.path.getmtime(vec_path)

    for key in ["svm"]:
        path = os.path.join(MODEL_DIR, f"model_{key}.pkl")
        if os.path.exists(path):
            _models[key] = joblib.load(path)


# Load khi import module
try:
    _load_all()
except FileNotFoundError:
    pass  # Sẽ bị báo lỗi khi gọi predict lần đầu


def _ensure_loaded():
    global _last_load_time

    vec_path = os.path.join(MODEL_DIR, "vectorizer.pkl")
    if not os.path.exists(vec_path):
        _load_all()
        return

    # Kiểm tra xem file model trên đĩa có mới hơn bản đang lưu ở RAM không
    mtime = os.path.getmtime(vec_path)
    if not _models or _vectorizer is None or mtime > _last_load_time:
        try:
            _load_all()
        except Exception as e:
            print(f"⚠️ Không thể nạp lại model tự động: {e}")


def predict_news(title: str, text: str, model_key: str = "lr"):
    """
    Dự đoán một bài báo với model được chỉ định.
    Trả về (label, probability).
    """
    _ensure_loaded()

    if model_key not in _models:
        raise ValueError(
            f"Model '{model_key}' không tồn tại. Hệ thống chỉ hỗ trợ: svm"
        )

    # Nhân đôi title để tăng trọng số (giống lúc train)
    content = f"{title} {title} {text}"
    clean   = clean_text(content)
    vector  = _vectorizer.transform([clean])

    model      = _models[model_key]
    prediction = model.predict(vector)[0]
    proba      = model.predict_proba(vector)[0]
    classes    = list(model.classes_)
    probability = float(proba[classes.index(prediction)])

    # Ánh xạ nhãn dạng số (1/0) về dạng chữ ('reliable'/'unreliable')
    if prediction == 1 or prediction == "reliable":
        pred_label = "reliable"
    else:
        pred_label = "unreliable"

    return pred_label, probability


def predict_all_models(title: str, text: str) -> dict:
    """
    Dự đoán với tất cả các mô hình có sẵn.
    Trả về dict {model_key: {label, probability, display, model_name}}.
    """
    _ensure_loaded()

    results = {}
    for key, display in MODEL_DISPLAY_NAMES.items():
        if key not in _models:
            continue
        label, prob = predict_news(title, text, key)
        results[key] = {
            "model_name":  display,
            "label":       label,
            "probability": round(prob * 100, 2),
            "display": (
                "Tin đáng tin cậy"
                if label == "reliable"
                else "Tin có dấu hiệu không đáng tin cậy"
            ),
            "badge": "real" if label == "reliable" else "fake",
        }
    return results


def analyze_news(title: str, content: str, url: str = "", metadata: dict = None) -> dict:
    """
    Phân tích tin tức bằng tất cả mô hình + tính điểm tổng hợp.

    Trả về dict:
        - title, content, url  : dữ liệu đầu vào
        - results              : dict kết quả từng model
        - scoring              : dict consensus từ scoring.py
        - metadata fields      : image, description, author, pub_date (nếu có)
    """
    from src.scoring import compute_consensus

    results = predict_all_models(title, content)
    scoring = compute_consensus(results, content)

    res = {
        "title":   title,
        "content": content,
        "url":     url,
        "results": results,
        "scoring": scoring,
        "top_features": get_top_features(title, content, "svm"),
    }
    if metadata:
        res.update(metadata)
    return res


def get_available_models() -> list:
    """Trả về danh sách model key đang có sẵn."""
    return list(_models.keys())


def get_top_features(title: str, text: str, model_key: str = "lr", top_n: int = 10) -> list:
    """
    Trích xuất top N từ khóa/đặc trưng ảnh hưởng nhất đến kết quả dự đoán.
    Chỉ hoạt động với model có coef_ (lr, svm) hoặc feature_importances_ (rf).
    Trả về list[dict]: [{word, weight, influence: 'positive'|'negative'}]
    """
    try:
        _ensure_loaded()

        if model_key not in _models:
            return []

        model = _models[model_key]

        # Kiểm tra model có hỗ trợ trích xuất feature không
        has_coef        = hasattr(model, "coef_")
        has_importances = hasattr(model, "feature_importances_")
        if not has_coef and not has_importances:
            return []  # MLP, ensemble... không hỗ trợ trực tiếp

        # Transform text thành TF-IDF vector
        content = f"{title} {title} {text}"
        clean   = clean_text(content)
        vector  = _vectorizer.transform([clean])

        feature_names = _vectorizer.get_feature_names_out()

        if has_coef:
            # LR / SVM: coef_[0] × tfidf_values = contribution per feature
            import numpy as np
            coef         = model.coef_[0]
            tfidf_values = vector.toarray()[0]
            contributions = coef * tfidf_values

            # Chỉ lấy các feature có giá trị TF-IDF > 0 (xuất hiện trong văn bản)
            nonzero_idx = tfidf_values.nonzero()[0]
            if len(nonzero_idx) == 0:
                return []

            scored = []
            for idx in nonzero_idx:
                scored.append({
                    "word":      str(feature_names[idx]),
                    "weight":    round(float(contributions[idx]), 4),
                    "influence": "positive" if contributions[idx] > 0 else "negative",
                })

            # Sort theo absolute value giảm dần, lấy top N
            scored.sort(key=lambda x: abs(x["weight"]), reverse=True)
            return scored[:top_n]

        else:
            # RF: feature_importances_ (global importance, không phụ thuộc sample)
            import numpy as np
            importances  = model.feature_importances_
            tfidf_values = vector.toarray()[0]

            # Chỉ lấy feature xuất hiện trong văn bản
            nonzero_idx = tfidf_values.nonzero()[0]
            if len(nonzero_idx) == 0:
                return []

            scored = []
            for idx in nonzero_idx:
                scored.append({
                    "word":      str(feature_names[idx]),
                    "weight":    round(float(importances[idx]), 4),
                    "influence": "positive",  # RF importance luôn dương
                })

            scored.sort(key=lambda x: abs(x["weight"]), reverse=True)
            return scored[:top_n]

    except Exception as e:
        print(f"⚠️ get_top_features error: {e}")
        return []
