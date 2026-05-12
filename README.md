# FAKE_NEWS_PROJECT

## Cách chạy project

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

### 4. Chạy website
```powershell
python app.py
```

Mở trình duyệt tại:
```text
http://127.0.0.1:5000
```
