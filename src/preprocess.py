import re

try:
    from underthesea import word_tokenize
    UNDERTHESEA_AVAILABLE = True
except Exception:
    UNDERTHESEA_AVAILABLE = False


# Tập hợp từ dừng (stopwords) tiếng Việt phổ biến để giảm nhiễu dữ liệu
VIETNAMESE_STOPWORDS = {
    "và", "là", "mà", "ở", "tại", "những", "các", "của", "cho", "trong",
    "bằng", "với", "ra", "vào", "được", "bị", "để", "như", "nhưng", "tuy",
    "vì", "nên", "thì", "do", "đó", "này", "kia", "ấy", "nào", "sự",
    "cuộc", "việc", "cái", "con", "người", "đã", "đang", "sẽ", "cũng", "vẫn",
    "đều", "tự", "lại", "qua", "theo", "trước", "sau", "trên", "dưới", "ngoài",
    "giữa", "ra", "này", "nọ", "kia"
}


def clean_text(text: str) -> str:
    """
    Tiền xử lý văn bản tiếng Việt:
    - Lowercase
    - Xoá URL, số, ký tự đặc biệt
    - Tokenize bằng underthesea (nếu có)
    - Loại bỏ từ dừng (stopwords)
    """
    if not text or not isinstance(text, str):
        return ""

    text = text.lower()
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if UNDERTHESEA_AVAILABLE and text:
        try:
            text = word_tokenize(text, format="text")
        except Exception:
            pass

    # Loại bỏ từ dừng
    words = text.split()
    filtered_words = [w for w in words if w.replace("_", " ") not in VIETNAMESE_STOPWORDS and w not in VIETNAMESE_STOPWORDS]
    text = " ".join(filtered_words)

    return text
