import re

try:
    from underthesea import word_tokenize
    UNDERTHESEA_AVAILABLE = True
except Exception:
    UNDERTHESEA_AVAILABLE = False


def clean_text(text: str) -> str:
    """
    Tiền xử lý văn bản tiếng Việt:
    - Lowercase
    - Xoá URL, số, ký tự đặc biệt
    - Tokenize bằng underthesea (nếu có)
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

    return text
