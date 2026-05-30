@echo off
title TrustCheck AI - Training Machine Learning Models
color 0A

echo ==========================================================
echo   TRUSTCHECK AI - HUAN LUYEN LAI MO HINH MACHINE LEARNING
echo ==========================================================
echo.
echo [*] Tim thay: data/news.csv
echo [*] Dang tien hanh tien xu ly va hoc may (Gom Logistic Regression, Naive Bayes, SVM)...
echo.

:: Cấu hình UTF-8 cho Windows console
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: Huấn luyện mô hình
.\.venv\Scripts\python.exe -m src.train

echo.
echo [!] Qua trinh huan luyen da hoan tat! 
echo [!] Bay gio ban co the chay file Start_Web.bat de bat dau kiem thu.
pause
