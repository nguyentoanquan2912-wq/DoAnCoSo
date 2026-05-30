# 🔍 TrustCheck AI — Phát Hiện Tin Giả Tiếng Việt

> Hệ thống đánh giá độ tin cậy tin tức tiếng Việt sử dụng **mô hình Linear SVM**, **NLP nội bộ**, và **EasyOCR**.

---

## 📋 Giới thiệu

**TrustCheck AI** là một ứng dụng web giúp người dùng kiểm tra và đánh giá độ tin cậy của các bài báo, tin tức tiếng Việt. Hệ thống kết hợp nhiều kỹ thuật Machine Learning và Xử lý Ngôn ngữ Tự nhiên (NLP) để đưa ra kết luận chính xác, minh bạch, kèm **giải thích lý do chi tiết**.

## ✨ Tính năng chính

| Tính năng | Mô tả |
|-----------|-------|
| 🤖 **1 Mô hình AI** | Linear SVM |
| 📊 **Phân loại** | Sử dụng mô hình Linear SVM để phân loại tin thật/giả |
| 📋 **Giải thích lý do** | Hiển thị **tại sao** tin thật/giả: từ khóa ảnh hưởng, dấu hiệu, bằng chứng cụ thể |
| ✨ **NLP phân tích** | Phân tích đặc trưng văn bản bằng NLP nội bộ, tính điểm tin cậy |
| 🖼️ **OCR Vision** | Trích xuất văn bản từ ảnh chụp màn hình tin tức bằng EasyOCR |
| 🌐 **Cào báo tự động** | Nhập URL bài báo từ VNExpress, Thanh Niên, Tuổi Trẻ... hệ thống tự cào nội dung |
| 💬 **Trợ lý AI Chat** | Chatbot AI hỗ trợ kiểm chứng tin đồn, phân tích ngôn từ, trả lời câu hỏi |
| 📈 **Dashboard** | Biểu đồ so sánh Accuracy, Precision, Recall, F1-score của từng mô hình |
| 📥 **Đóng góp dữ liệu** | Người dùng đóng góp bài viết vào tập dữ liệu, hệ thống tự huấn luyện lại |
| 🔗 **REST API** | Backend Flask cung cấp API endpoint cho tích hợp và mở rộng |

## 🛠️ Công nghệ sử dụng

| Công nghệ | Vai trò |
|-----------|---------|
| **Python** | Ngôn ngữ lập trình chính |
| **Flask** | Web Framework |
| **scikit-learn** | Thư viện Machine Learning |
| **underthesea** | Xử lý Ngôn ngữ Tự nhiên tiếng Việt (tách từ, chuẩn hóa) |
| **EasyOCR** | Thư viện OCR trích xuất văn bản từ hình ảnh cục bộ |
| **TF-IDF** | Phương pháp vector hóa văn bản |
| **SQLite** | Cơ sở dữ liệu lưu trữ lịch sử |
| **BeautifulSoup** | Web Crawling / Cào dữ liệu bài báo |
| **HTML/CSS/JS** | Giao diện Frontend |

## 📁 Cấu trúc Dự án

```
fake_news_project_final/
├── app.py                  # Server Flask chính
├── requirements.txt        # Danh sách thư viện Python
├── data/
│   └── news.csv           # Tập dữ liệu huấn luyện
├── models/
│   ├── model_lr.pkl        # Logistic Regression
│   ├── model_nb.pkl        # Naive Bayes
│   ├── model_svm.pkl       # Linear SVM
│   ├── model_rf.pkl        # Random Forest
│   ├── model_mlp.pkl       # Multi-layer Perceptron
│   ├── model_ensemble.pkl  # Ensemble Voting
│   ├── vectorizer.pkl      # TF-IDF Vectorizer
│   └── metrics.json        # Chỉ số đánh giá mô hình
├── src/
│   ├── train.py            # Huấn luyện mô hình
│   ├── predict.py          # Dự đoán & trích xuất features
│   ├── scoring.py          # Tính điểm đồng thuận & sinh lý do
│   ├── preprocess.py       # Tiền xử lý NLP tiếng Việt
│   ├── chatbot.py          # Chatbot và OCR cục bộ (không cần API bên ngoài)
│   ├── crawler.py          # Cào dữ liệu bài báo
│   ├── db.py               # Quản lý SQLite database
│   └── history.py          # Quản lý lịch sử dự đoán
├── templates/              # HTML Jinja2 templates
├── static/
│   ├── css/                # Stylesheet
│   └── js/                 # JavaScript
├── database/
│   └── history.db          # SQLite database
├── Start_Web.bat           # Script chạy web (Windows)
└── Train_Model.bat         # Script huấn luyện (Windows)
```

## 🚀 Hướng dẫn Cài đặt & Chạy

### 1. Tạo môi trường ảo
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Cài thư viện
```powershell
pip install -r requirements.txt
```

### 3. Huấn luyện mô hình
```powershell
python -m src.train
```
> Quá trình huấn luyện sẽ train mô hình Linear SVM và lưu vào thư mục `models/`.

### 4. Chạy website
```powershell
python app.py
```

### 5. Mở trình duyệt
```
http://127.0.0.1:5000
```

## 🔑 Cấu hình hệ thống

Hệ thống hoạt động hoàn toàn **cục bộ (offline)** và **không cần bất kỳ API Key bên ngoài nào**. Tất cả các tính năng bao gồm phân loại bằng mô hình Linear SVM, trích xuất văn bản bằng EasyOCR và trợ lý ảo AI đều chạy trực tiếp trên máy chủ của bạn, bảo mật tuyệt đối dữ liệu.

## 📊 API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/predict` | Dự đoán tin thật/giả |
| GET | `/api/models` | Lấy metrics các mô hình |
| GET | `/api/history` | Lấy lịch sử dự đoán |
| DELETE | `/api/history/<id>` | Xoá 1 mục lịch sử |
| POST | `/api/extract` | Cào nội dung từ URL |
| POST | `/api/chat` | Chat với Trợ lý AI (NLP nội bộ) |
| POST | `/api/ai-audit` | Thẩm định chuyên sâu |
| POST | `/api/extract-image` | Trích xuất văn bản từ ảnh |
| POST | `/api/dataset/add` | Đóng góp dữ liệu |
| POST | `/api/train` | Huấn luyện lại mô hình |
| GET | `/api/train/status` | Kiểm tra trạng thái huấn luyện |

---

© 2024 – 2026 **TrustCheck AI** — Nghiên cứu & Xây dựng Website Đánh Giá Độ Tin Cậy Tin Tức bằng Machine Learning, NLP & AI.
