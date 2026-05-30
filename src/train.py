import os
import json
import joblib
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB, ComplementNB
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report,
)

from src.preprocess import clean_text


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "news.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")

MODEL_DISPLAY_NAMES = {
    "svm":      "Linear SVM",
}


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    print("📂 Đang tải dữ liệu...")
    df = pd.read_csv(DATA_PATH)
    df["title"]   = df["title"].fillna("")
    df["text"]    = df["text"].fillna("")
    # Kết hợp tiêu đề (nhân đôi trọng số) + nội dung
    df["content"] = df["title"] + " " + df["title"] + " " + df["text"]

    print(f"   ✅ Tổng mẫu: {len(df)} (reliable: {(df['label']=='reliable').sum()}, unreliable: {(df['label']=='unreliable').sum()})")

    print("🔄 Đang tiền xử lý văn bản...")
    df["clean_content"] = df["content"].apply(clean_text)

    X = df["clean_content"]
    y = df["label"].map({"reliable": 1, "unreliable": 0})
    classes = sorted(y.unique().tolist())

    # ── Train/Test Split (stratified) ──────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"   ✅ Train: {len(X_train)} | Test: {len(X_test)}")

    # ── TF-IDF Vector hóa ──────────────────────────────────────────
    print("\n📊 Vector hóa TF-IDF nâng cao (unigram + bigram + trigram)...")
    vectorizer = TfidfVectorizer(
        max_features=20000,
        ngram_range=(1, 3),        # unigram, bigram, trigram
        sublinear_tf=True,         # log TF để giảm ảnh hưởng từ xuất hiện nhiều
        min_df=2,                  # bỏ từ chỉ xuất hiện 1 lần
        max_df=0.95,               # bỏ từ xuất hiện > 95% tài liệu
        analyzer="word",
        strip_accents=None,        # Giữ dấu tiếng Việt
        token_pattern=r"(?u)\b\w+\b",
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec  = vectorizer.transform(X_test)
    print(f"   ✅ Feature shape: {X_train_vec.shape}")

    # ── Định nghĩa các model ───────────────────────────────────────
    svm = CalibratedClassifierCV(
        LinearSVC(max_iter=3000, C=2.0, class_weight="balanced", random_state=42),
        cv=3
    )

    models_def = {
        "svm":      svm,
    }

    metrics = {}

    for key, model in models_def.items():
        display = MODEL_DISPLAY_NAMES[key]
        print(f"\n🤖 Huấn luyện {display}...")

        model.fit(X_train_vec, y_train)
        y_pred = model.predict(X_test_vec)

        acc  = accuracy_score(y_test, y_pred)
        prec, rec, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average="weighted", zero_division=0
        )
        cm = confusion_matrix(y_test, y_pred, labels=classes).tolist()

        # Cross-validation (5-fold) để đánh giá ổn định
        try:
            cv_scores = cross_val_score(model, X_train_vec, y_train, cv=5, scoring="f1_weighted", n_jobs=-1)
            cv_mean   = round(float(np.mean(cv_scores)) * 100, 2)
            cv_std    = round(float(np.std(cv_scores)) * 100, 2)
        except Exception:
            cv_mean, cv_std = 0.0, 0.0

        metrics[key] = {
            "model_name":       display,
            "accuracy":         round(acc  * 100, 2),
            "precision":        round(prec * 100, 2),
            "recall":           round(rec  * 100, 2),
            "f1":               round(f1   * 100, 2),
            "cv_f1_mean":       cv_mean,
            "cv_f1_std":        cv_std,
            "confusion_matrix": cm,
            "classes":          classes,
        }

        print(f"   Accuracy:   {acc  * 100:.2f}%")
        print(f"   Precision:  {prec * 100:.2f}%")
        print(f"   Recall:     {rec  * 100:.2f}%")
        print(f"   F1-Score:   {f1   * 100:.2f}%")
        print(f"   CV F1 (5-fold): {cv_mean:.2f}% ± {cv_std:.2f}%")
        print(classification_report(y_test, y_pred, target_names=["unreliable", "reliable"], zero_division=0))

        joblib.dump(model, os.path.join(MODEL_DIR, f"model_{key}.pkl"))

    # ── Thống kê dataset ───────────────────────────────────────────
    metrics["dataset"] = {
        "total":      int(len(df)),
        "reliable":   int((df["label"] == "reliable").sum()),
        "unreliable": int((df["label"] == "unreliable").sum()),
        "train_size": int(len(X_train)),
        "test_size":  int(len(X_test)),
    }

    # ── Lưu vectorizer và metrics ──────────────────────────────────
    joblib.dump(vectorizer, os.path.join(MODEL_DIR, "vectorizer.pkl"))

    # Xóa selector.pkl cũ nếu có (không dùng SelectKBest nữa)
    sel_path = os.path.join(MODEL_DIR, "selector.pkl")
    if os.path.exists(sel_path):
        os.remove(sel_path)
        print("\n🗑️  Đã xóa selector.pkl cũ (không cần thiết nữa).")

    metrics_path = os.path.join(MODEL_DIR, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print("\n✅ Đã huấn luyện xong mô hình Linear SVM!")
    print(f"✅ Đã lưu model, vectorizer và metrics vào: {MODEL_DIR}")

    # Tóm tắt kết quả
    print("\n" + "="*60)
    print("📊 TÓM TẮT HIỆU SUẤT CÁC MÔ HÌNH")
    print("="*60)
    for key in ["svm"]:
        if key in metrics:
            m = metrics[key]
            print(f"  {m['model_name']:40s} Acc={m['accuracy']:6.2f}%  F1={m['f1']:6.2f}%")
    print("="*60)


if __name__ == "__main__":
    main()
