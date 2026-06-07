"""
Script chup anh toan bo cac trang cua TrustCheck AI.
Chup bang Playwright, luu vao thu muc screenshots/.
"""
import os
import sys
import io
import time

# Fix encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5000"
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")

# Danh sách các trang cần chụp
PAGES = [
    {
        "name": "homepage",
        "url": "/",
        "desc": "Trang chủ TrustCheck AI",
        "wait_ms": 2000,
    },
    {
        "name": "analyzer",
        "url": "/analyzer",
        "desc": "Trang phân tích tin tức",
        "wait_ms": 2000,
    },
    {
        "name": "dashboard",
        "url": "/dashboard",
        "desc": "Dashboard hiệu suất mô hình ML",
        "wait_ms": 3000,
    },
    {
        "name": "history",
        "url": "/history",
        "desc": "Trang lịch sử dự đoán",
        "wait_ms": 2000,
    },
    {
        "name": "ai_assistant",
        "url": "/ai-assistant",
        "desc": "Trang Trợ lý AI Kiểm Chứng",
        "wait_ms": 2000,
    },
]


def capture_all():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1.5,
        )

        for page_info in PAGES:
            page = context.new_page()
            url = BASE_URL + page_info["url"]
            print(f"📸 Đang chụp: {page_info['desc']} ({url})")

            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(page_info["wait_ms"])

            filepath = os.path.join(SCREENSHOT_DIR, f"{page_info['name']}.png")
            page.screenshot(path=filepath, full_page=True)
            print(f"   ✅ Lưu: {filepath}")
            page.close()

        # Chụp trang kết quả phân tích: cần submit form trước
        print(f"\n📸 Đang chụp: Trang kết quả phân tích (cần submit form)")
        page = context.new_page()
        page.goto(BASE_URL + "/analyzer", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Điền form với tin mẫu giả
        try:
            # Click vào button "Tin giả mẫu" 
            fake_sample_btn = page.locator("text=Tin giả mẫu").first
            if fake_sample_btn.is_visible():
                fake_sample_btn.click()
                page.wait_for_timeout(1000)
                print("   ✅ Đã điền tin giả mẫu")
            else:
                # Nếu không tìm thấy button, điền thủ công
                title_input = page.locator('input[name="title"], #title, [placeholder*="tiêu đề"], [placeholder*="Ví dụ"]').first
                if title_input.is_visible():
                    title_input.fill("Uống nước chanh ấm mỗi sáng chữa khỏi ung thư giai đoạn cuối")

                content_input = page.locator('textarea[name="content"], #content, [placeholder*="nội dung"], [placeholder*="Dán"]').first
                if content_input.is_visible():
                    content_input.fill(
                        "Theo nghiên cứu mới nhất từ Viện Y học Quốc tế Harvard, "
                        "uống nước chanh ấm mỗi sáng có thể chữa khỏi hoàn toàn bệnh ung thư giai đoạn cuối. "
                        "Hàng nghìn người đã được chữa khỏi bằng phương pháp đơn giản này. "
                        "Các bác sĩ cho biết đây là bước đột phá lớn nhất trong lịch sử y học. "
                        "Tuy nhiên các hãng dược phẩm lớn đang cố che giấu thông tin này."
                    )
        except Exception as e:
            print(f"   ⚠️ Lỗi điền form: {e}")

        # Submit form
        try:
            submit_btn = page.locator('button[type="submit"], #btn-submit, .btn-primary:has-text("Phân tích")').first
            if submit_btn.is_visible():
                submit_btn.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)
                print("   ✅ Đã submit form và chờ kết quả")
        except Exception as e:
            print(f"   ⚠️ Lỗi submit: {e}")

        # Chụp trang kết quả
        filepath = os.path.join(SCREENSHOT_DIR, "check_result.png")
        page.screenshot(path=filepath, full_page=True)
        print(f"   ✅ Lưu: {filepath}")
        page.close()

        browser.close()

    print("\n🎉 Đã chụp xong tất cả screenshots!")


if __name__ == "__main__":
    capture_all()
