import json
import os

from flask import Flask, jsonify, render_template, request

from src.history import (
    add_to_history,
    clear_history,
    delete_from_history,
    get_history,
)
from src.predict import predict_all_models, predict_news
from src.crawler import extract_news_from_url
from src.chatbot import chat_with_gemini

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METRICS_PATH = os.path.join(BASE_DIR, "models", "metrics.json")

MODEL_DISPLAY = {
    "lr": "Logistic Regression",
    "nb": "Naive Bayes",
    "svm": "Linear SVM",
}

# ─── Page Routes ────────────────────────────────────────────────────────────


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyzer")
def analyzer():
    return render_template("analyzer.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/history")
def history():
    return render_template("history.html")


# ─── API Routes ─────────────────────────────────────────────────────────────


@app.route("/api/predict", methods=["POST"])
def api_predict():
    """
    POST /api/predict
    Body JSON: { "title": str, "content": str, "model": "lr"|"nb"|"svm"|"all" }
    """
    data = request.get_json(force=True, silent=True) or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    model_key = data.get("model", "lr").strip().lower()

    if not title and not content:
        return jsonify({"error": "Vui lòng nhập tiêu đề hoặc nội dung tin tức."}), 400

    try:
        if model_key == "all":
            results = predict_all_models(title, content)
        else:
            if model_key not in MODEL_DISPLAY:
                return jsonify({"error": f"Model '{model_key}' không hợp lệ."}), 400
            label, prob = predict_news(title, content, model_key)
            results = {
                model_key: {
                    "model_name": MODEL_DISPLAY[model_key],
                    "label": label,
                    "probability": round(prob * 100, 2),
                    "display": (
                        "Tin đáng tin cậy"
                        if label == "reliable"
                        else "Tin có dấu hiệu không đáng tin cậy"
                    ),
                    "badge": "real" if label == "reliable" else "fake",
                }
            }

        entry = add_to_history(title, content, results, model_key)
        return jsonify({"success": True, "results": results, "history_id": entry["id"]})

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Lỗi xử lý: {str(e)}"}), 500


@app.route("/api/models", methods=["GET"])
def api_models():
    """GET /api/models — Trả về metrics của các model đã train."""
    if not os.path.exists(METRICS_PATH):
        return (
            jsonify(
                {"error": "Chưa có metrics. Vui lòng chạy: python -m src.train"}
            ),
            503,
        )
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    return jsonify(metrics)


@app.route("/api/history", methods=["GET"])
def api_history():
    """GET /api/history — Lấy toàn bộ lịch sử dự đoán."""
    return jsonify(get_history())


@app.route("/api/history/<hist_id>", methods=["DELETE"])
def api_delete_history(hist_id):
    """DELETE /api/history/<id> — Xoá 1 mục lịch sử."""
    success = delete_from_history(hist_id)
    if success:
        return jsonify({"success": True, "message": "Đã xoá thành công."})
    return jsonify({"error": "Không tìm thấy mục lịch sử này."}), 404


@app.route("/api/history/clear", methods=["DELETE"])
def api_clear_history():
    """DELETE /api/history/clear — Xoá toàn bộ lịch sử."""
    count = clear_history()
    return jsonify({"success": True, "deleted": count})


@app.route("/api/extract", methods=["POST"])
def api_extract():
    """POST /api/extract — Cào bài báo bằng BeautifulSoup"""
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "Vui lòng nhập đường dẫn bài báo."}), 400

    try:
        result = extract_news_from_url(url)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """POST /api/chat — Chat với Gemini"""
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "").strip()
    api_key = data.get("api_key", "").strip()
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "Không có nội dung tin nhắn."}), 400
    
    if not api_key:
        return jsonify({"error": "Google Gemini API Key là bắt buộc để sử dụng tính năng này."}), 401

    try:
        reply = chat_with_gemini(message, api_key, history)
        return jsonify({"success": True, "reply": reply})
    except Exception as e:
        import traceback
        with open("chat_error.log", "a", encoding="utf-8") as f:
            f.write(f"=== ERROR ===\n{traceback.format_exc()}\n")
        return jsonify({"error": str(e)}), 500


# ─── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
