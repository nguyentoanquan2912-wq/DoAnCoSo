@echo off
title TrustCheck AI - Fake News Detection Server
color 0B

echo ==========================================================
echo         TRUSTCHECK AI - HETHONG PHAN TICH TIN GIA
echo ==========================================================
echo.
echo [*] Dang khoi dong may chu Backend (Flask)...
echo [*] Trang web se tu dong mo ra trong giay lat.
echo.

:: Mở sẵn trình duyệt (Đợi 3s cho server kịp bật)
start "" http://127.0.0.1:5000

:: Cấu hình UTF-8 cho Windows console
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: Chạy server (sử dụng môi trường ảo)
.\.venv\Scripts\python.exe app.py

:: Nếu có lỗi, màn hình sẽ dừng lại để bạn xem lỗi
pause
