import os
import joblib

from src.preprocess import clean_text


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models")

MODEL_DISPLAY_NAMES = {
    "lr": "Logistic Regression",
    "nb": "Naive Bayes",
    "svm": "Linear SVM",
}

_vectorizer = None
_models = {}


def _load_all():
    """Load vectorizer và tất cả models (gọi 1 lần khi import)."""
    global _vectorizer, _models

    vec_path = os.path.join(MODEL_DIR, "vectorizer.pkl")
    if not os.path.exists(vec_path):
        raise FileNotFoundError(
            "❌ Chưa tìm thấy model. Vui lòng chạy: python -m src.train"
        )

    _vectorizer = joblib.load(vec_path)

    for key in ["lr", "nb", "svm"]:
        path = os.path.join(MODEL_DIR, f"model_{key}.pkl")
        if os.path.exists(path):
            _models[key] = joblib.load(path)


# Load khi import module
try:
    _load_all()
except FileNotFoundError:
    pass  # Sẽ bị báo lỗi khi gọi predict lần đầu


def _ensure_loaded():
    if not _models or _vectorizer is None:
        _load_all()


def predict_news(title: str, text: str, model_key: str = "lr"):
    """
    Dự đoán một bài báo với model được chỉ định.
    Trả về (label, probability).
    """
    _ensure_loaded()

    if model_key not in _models:
        raise ValueError(f"Model '{model_key}' không tồn tại. Chọn: lr, nb, svm")

    content = f"{title} {text}"
    clean = clean_text(content)
    vector = _vectorizer.transform([clean])

    model = _models[model_key]
    prediction = model.predict(vector)[0]
    proba = model.predict_proba(vector)[0]
    classes = list(model.classes_)
    probability = float(proba[classes.index(prediction)])

    return prediction, probability


def predict_all_models(title: str, text: str) -> dict:
    """
    Dự đoán với tất cả 3 mô hình.
    Trả về dict {model_key: {label, probability, display, model_name}}.
    """
    _ensure_loaded()

    results = {}
    for key, display in MODEL_DISPLAY_NAMES.items():
        if key not in _models:
            continue
        label, prob = predict_news(title, text, key)
        results[key] = {
            "model_name": display,
            "label": label,
            "probability": round(prob * 100, 2),
            "display": (
                "Tin đáng tin cậy" if label == "reliable"
                else "Tin có dấu hiệu không đáng tin cậy"
            ),
            "badge": "real" if label == "reliable" else "fake",
        }
    return results


def get_available_models() -> list:
    """Trả về danh sách model key đang có sẵn."""
    return list(_models.keys())
