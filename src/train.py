import os
import json
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
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
    "lr": "Logistic Regression",
    "nb": "Naive Bayes",
    "svm": "Linear SVM",
}


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    print("📂 Đang tải dữ liệu...")
    df = pd.read_csv(DATA_PATH)
    df["title"] = df["title"].fillna("")
    df["text"] = df["text"].fillna("")
    df["content"] = df["title"] + " " + df["text"]

    print("🔄 Đang tiền xử lý văn bản...")
    df["clean_content"] = df["content"].apply(clean_text)

    X = df["clean_content"]
    y = df["label"]

    classes = sorted(y.unique().tolist())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("📊 Vector hóa TF-IDF (bigrams)...")
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # Định nghĩa 3 mô hình
    models_def = {
        "lr": LogisticRegression(max_iter=1000, C=1.0, random_state=42),
        "nb": MultinomialNB(alpha=0.1),
        "svm": CalibratedClassifierCV(LinearSVC(max_iter=1000, C=1.0, random_state=42)),
    }

    metrics = {}

    for key, model in models_def.items():
        display = MODEL_DISPLAY_NAMES[key]
        print(f"\n🤖 Huấn luyện {display}...")
        model.fit(X_train_vec, y_train)
        y_pred = model.predict(X_test_vec)

        acc = accuracy_score(y_test, y_pred)
        prec, rec, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average="weighted", zero_division=0
        )
        cm = confusion_matrix(y_test, y_pred, labels=classes).tolist()

        metrics[key] = {
            "model_name": display,
            "accuracy": round(acc * 100, 2),
            "precision": round(prec * 100, 2),
            "recall": round(rec * 100, 2),
            "f1": round(f1 * 100, 2),
            "confusion_matrix": cm,
            "classes": classes,
        }

        print(f"   Accuracy:  {acc * 100:.2f}%")
        print(f"   Precision: {prec * 100:.2f}%")
        print(f"   Recall:    {rec * 100:.2f}%")
        print(f"   F1-Score:  {f1 * 100:.2f}%")
        print(classification_report(y_test, y_pred, zero_division=0))

        joblib.dump(model, os.path.join(MODEL_DIR, f"model_{key}.pkl"))

    # Thống kê dataset
    metrics["dataset"] = {
        "total": int(len(df)),
        "reliable": int((df["label"] == "reliable").sum()),
        "unreliable": int((df["label"] == "unreliable").sum()),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
    }

    # Lưu vectorizer và metrics
    joblib.dump(vectorizer, os.path.join(MODEL_DIR, "vectorizer.pkl"))
    metrics_path = os.path.join(MODEL_DIR, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print("\n✅ Đã huấn luyện xong 3 mô hình!")
    print(f"✅ Đã lưu model và metrics vào: {MODEL_DIR}")


if __name__ == "__main__":
    main()
