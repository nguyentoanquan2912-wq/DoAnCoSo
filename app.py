import json
import os

from flask import Flask, jsonify, redirect, render_template, request, url_for

from src.history import (
    add_to_history,
    clear_history,
    delete_from_history,
    get_history,
)
from src.predict import analyze_news, predict_news
from src.crawler import extract_news_from_url
from src.chatbot import chat_response
from src.db import insert_prediction

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METRICS_PATH = os.path.join(BASE_DIR, "models", "metrics.json")

MODEL_DISPLAY = {
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


@app.route("/ai-assistant")
def ai_assistant():
    return render_template("ai_assistant.html")


@app.route("/check", methods=["GET", "POST"])
def check():
    """
    POST /check — Nhận dữ liệu từ form analyzer, chạy model nội bộ,
    tính điểm tổng hợp, lưu lịch sử, và render check.html.
    """
    if request.method == "GET":
        # Nếu truy cập trực tiếp bằng GET mà không có dữ liệu
        title = request.args.get("title", "").strip()
        content = request.args.get("content", "").strip()
        url = request.args.get("url", "").strip()
        model_used = request.args.get("model", "all").strip().lower()
        if not title and not content and not url:
            return redirect(url_for("analyzer"))
    else:
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        url = request.form.get("url", "").strip()
        model_used = request.form.get("model", "all").strip().lower()

    if model_used not in ["svm", "all"]:
        model_used = "all"

    crawled_metadata = {
        "image": "",
        "description": "",
        "author": "",
        "pub_date": ""
    }

    # Nếu có URL, tiến hành cào dữ liệu và thông tin bổ sung
    if url:
        try:
            crawled = extract_news_from_url(url)
            if not title:
                title = crawled.get("title", "")
            if not content:
                content = crawled.get("content", "")
            crawled_metadata = {
                "image": crawled.get("image", ""),
                "description": crawled.get("description", ""),
                "author": crawled.get("author", ""),
                "pub_date": crawled.get("pub_date", "")
            }
        except Exception as e:
            if not content:
                return render_template(
                    "check.html",
                    error=f"Không thể tải nội dung từ URL. Vui lòng kiểm tra lại đường dẫn: {str(e)}",
                    model_used=model_used,
                )

    if not title and not content:
        return render_template(
            "check.html",
            error="Vui lòng nhập tiêu đề hoặc nội dung tin tức.",
            model_used=model_used,
        )

    try:
        # Chạy phân tích nội bộ (3 model + scoring)
        analysis = analyze_news(title, content, url, metadata=crawled_metadata)

        # Lưu vào lịch sử
        entry = insert_prediction(
            title=title,
            content=content,
            results=analysis["results"],
            model_used=model_used,
            scoring=analysis["scoring"],
            url=url,
            image=crawled_metadata["image"],
            description=crawled_metadata["description"],
            author=crawled_metadata["author"],
            pub_date=crawled_metadata["pub_date"]
        )

        return render_template(
            "check.html",
            analysis=analysis,
            history_id=entry["id"],
            model_used=model_used,
        )

    except FileNotFoundError as e:
        return render_template(
            "check.html",
            error=f"Chưa tìm thấy model. Vui lòng chạy: python -m src.train — {e}",
        )
    except Exception as e:
        return render_template(
            "check.html",
            error=f"Lỗi xử lý: {str(e)}",
        )


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
    model_key = data.get("model", "svm").strip().lower()
    if model_key != "svm":
        model_key = "svm"

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
    """POST /api/chat — Chat với engine AI nội bộ"""
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "Không có nội dung tin nhắn."}), 400

    try:
        reply = chat_response(message, history)
        return jsonify({"success": True, "reply": reply})
    except Exception as e:
        import traceback
        with open("chat_error.log", "a", encoding="utf-8") as f:
            f.write(f"=== ERROR ===\n{traceback.format_exc()}\n")
        return jsonify({"error": str(e)}), 500


@app.route("/api/extract-image", methods=["POST"])
def api_extract_image():
    """POST /api/extract-image — Dùng EasyOCR cục bộ trích xuất văn bản từ ảnh + tự động phân tích SVM"""
    from src.chatbot import extract_text_from_image

    data = request.get_json(force=True, silent=True) or {}
    image_base64 = data.get("image_base64", "").strip()
    mime_type = data.get("mime_type", "image/jpeg").strip()

    if not image_base64:
        return jsonify({"error": "Không có dữ liệu ảnh được gửi lên."}), 400

    try:
        result = extract_text_from_image(image_base64, mime_type)
        title = result.get("title", "")
        content = result.get("content", "")

        # Tự động phân tích bằng Linear SVM nếu có nội dung
        svm_analysis = None
        if title or content:
            try:
                label, prob = predict_news(title or "", content or "", "svm")
                svm_analysis = {
                    "label": label,
                    "probability": round(prob * 100, 2),
                    "display": "Tin đáng tin cậy" if label == "reliable" else "Tin có dấu hiệu không đáng tin cậy",
                    "badge": "real" if label == "reliable" else "fake",
                }
            except Exception:
                pass  # Nếu model chưa load thì bỏ qua

        return jsonify({
            "success": True,
            "title": title,
            "content": content,
            "svm_analysis": svm_analysis,
        })
    except Exception as e:
        import traceback
        with open("chat_error.log", "a", encoding="utf-8") as f:
            f.write(f"=== OCR ERROR ===\n{traceback.format_exc()}\n")
        return jsonify({"error": str(e)}), 500


@app.route("/api/ai-audit", methods=["POST"])
def api_ai_audit():
    """POST /api/ai-audit — Thẩm định chuyên sâu bằng AI nội bộ"""
    data = request.get_json(force=True, silent=True) or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()

    if not title and not content:
        return jsonify({"error": "Vui lòng nhập tiêu đề hoặc nội dung tin tức để thẩm định."}), 400

    try:
        audit_text = f"{title}. {content}" if title and content else (title or content)
        reply = chat_response(audit_text)
        return jsonify({"success": True, "report": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── API Đóng Góp & Tự Động Huấn Luyện Lại (Hot-Reload) ──────────────────────────

import threading

_training_lock = threading.Lock()
_training_in_progress = False
_training_error = None


@app.route("/api/dataset/add", methods=["POST"])
def api_dataset_add():
    """POST /api/dataset/add — Thêm tin tức mới vào tập dữ liệu data/news.csv"""
    data = request.get_json(force=True, silent=True) or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    label = data.get("label", "").strip().lower()

    if not title or not content:
        return jsonify({"error": "Tiêu đề và nội dung là bắt buộc."}), 400
    if label not in ["reliable", "unreliable"]:
        return jsonify({"error": "Nhãn không hợp lệ. Chọn 'reliable' hoặc 'unreliable'."}), 400

    import csv
    csv_path = os.path.join(BASE_DIR, "data", "news.csv")
    try:
        # Làm sạch chuỗi trước khi viết (xóa ký tự dòng mới thừa thãi)
        clean_title = title.replace("\r", "").replace("\n", " ")
        clean_content = content.replace("\r", "").replace("\n", " ")

        # Mở file ghi tiếp (append)
        file_exists = os.path.exists(csv_path)
        with open(csv_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["title", "text", "label"])
            writer.writerow([clean_title, clean_content, label])

        # Đọc lại tổng số mẫu
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            total_rows = sum(1 for row in reader) - 1

        return jsonify({
            "success": True, 
            "message": f"Đã thêm bài viết thành công vào tập dữ liệu (Tổng số mẫu hiện tại: {total_rows}).",
            "total_samples": total_rows
        })
    except Exception as e:
        return jsonify({"error": f"Lỗi ghi file dữ liệu: {str(e)}"}), 500


@app.route("/api/train", methods=["POST"])
def api_train():
    """POST /api/train — Kích hoạt huấn luyện lại mô hình trong luồng nền"""
    global _training_in_progress, _training_error
    
    with _training_lock:
        if _training_in_progress:
            return jsonify({"error": "Hệ thống đang tiến hành huấn luyện rồi, vui lòng đợi."}), 400
        _training_in_progress = True
        _training_error = None

    def run_training_thread():
        global _training_in_progress, _training_error
        try:
            # Thiết lập môi trường UTF-8 trong luồng
            os.environ["PYTHONIOENCODING"] = "utf-8"
            os.environ["PYTHONUTF8"] = "1"
            from src.train import main as train_main
            train_main()
            print("🤖 [AI Train Thread] Huấn luyện lại hoàn tất thành công!")
        except Exception as e:
            import traceback
            _training_error = str(e)
            print(f"❌ [AI Train Thread] Lỗi huấn luyện: {traceback.format_exc()}")
        finally:
            with _training_lock:
                _training_in_progress = False

    t = threading.Thread(target=run_training_thread)
    t.daemon = True
    t.start()

    return jsonify({
        "success": True, 
        "message": "Đã bắt đầu huấn luyện lại mô hình AI trong nền. Quá trình này mất khoảng 5-10 giây."
    })


@app.route("/api/train/status", methods=["GET"])
def api_train_status():
    """GET /api/train/status — Kiểm tra trạng thái huấn luyện"""
    global _training_in_progress, _training_error
    return jsonify({
        "in_progress": _training_in_progress,
        "error": _training_error,
        "success": (not _training_in_progress and _training_error is None)
    })


# ─── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
