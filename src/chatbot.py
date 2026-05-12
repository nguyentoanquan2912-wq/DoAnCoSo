from google import genai
from google.genai import types

# Prompt chỉ dẫn chung về cách đóng vai
SYSTEM_INSTRUCTION = (
    "Bạn là một CHUYÊN GIA ĐÁNH GIÁ TIN TỨC VÀ AI, đóng vai trò là trợ lý ảo hỗ trợ người dùng "
    "của trang web \"TrustCheck AI - Phát Hiện Tin Giả\". "
    "Bạn giao tiếp bằng tiếng Việt một cách tự nhiên, lịch sự, và chuyên nghiệp.\n\n"
    "NHIỆM VỤ CỦA BẠN:\n"
    "1. Giải đáp các thắc mắc của người dùng về một bản tin, bài báo, tiêu đề tin tức.\n"
    "2. Cung cấp việc \"kiểm chứng thông tin (Fact-check)\": nếu bạn biết thông tin người dùng "
    "đưa là thật hay hư cấu, hãy nói thẳng theo hiểu biết của bạn.\n"
    "3. Giải thích logic của việc tin đó có đáng tin cậy hay không (quan sát giọng văn, tính giật "
    "gân, thiếu nguồn trích dẫn, phản khoa học, v.v.).\n"
    "4. Nếu người dùng hỏi các câu không liên quan đến máy học, AI hoặc tin tức, hãy từ chối "
    "khéo léo và hướng họ về lĩnh vực chuyên môn của hệ thống."
)

# Danh sách model chuẩn (theo tài liệu Google AI Studio mới nhất)
MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]


def _is_retryable_error(error_msg: str) -> bool:
    """Kiểm tra xem lỗi có thể thử lại với model khác không."""
    retryable_keywords = [
        "404", "not found", "not supported", "deprecated",
        "429", "resource_exhausted", "quota", "rate limit",
        "unavailable", "503", "overloaded",
    ]
    error_lower = error_msg.lower()
    return any(kw in error_lower for kw in retryable_keywords)


def chat_with_gemini(message: str, api_key: str, history: list = None) -> str:
    if not api_key:
        raise ValueError("Google Gemini API Key là bắt buộc để sử dụng trợ lý AI này.")
    if len(api_key) < 20 or not api_key.startswith("AIza"):
        raise ValueError("Khóa API không đúng định dạng (phải bắt đầu bằng 'AIza').")

    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'}) # Ép SDK dùng v1alpha hỗ trợ mô hình mới nhất

    contents = []
    if history:
        for item in history:
            role = item.get("role", "user")
            if role == "assistant":
                role = "model"
            content_text = item.get("content", "")
            if content_text:
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part(text=content_text)]
                ))

    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=message)]
    ))

    generate_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.7,
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
        ]
    )

    all_errors = []

    for model_name in MODEL_CANDIDATES:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=generate_config,
            )
            return response.text
        except Exception as e:
            error_msg = str(e)
            
            # Lỗi API key sai => ném ngay
            if "API_KEY_INVALID" in error_msg or "INVALID_API_KEY" in error_msg or "api key not valid" in error_msg.lower():
                raise ValueError("Khóa API không hợp lệ. Vui lòng kiểm tra lại tại AI Studio.")

            # Ghi nhận lỗi của mô hình này
            all_errors.append(f"[{model_name} thất bại: {error_msg}]")

            # Nếu lỗi retry được (như Quota, Not Found), thử model tiếp
            if _is_retryable_error(error_msg):
                continue

            # Các lỗi hệ thống khác => ném ngay
            raise Exception(f"Lỗi hệ thống Gemini ({model_name}): {error_msg}")

    # Nếu chạy hết vòng lặp mà vẫn lỗi
    error_summary = " | ".join(all_errors)
    raise Exception(f"Tất cả model đều không khả dụng. Chi tiết: {error_summary}")
