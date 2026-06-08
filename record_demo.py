import os
import subprocess
import time
import sys
import io

# Fix encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

def generate_test_image():
    """Tạo ảnh test_news_ocr.png chứa văn bản tiếng Việt để chạy thử OCR"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        print("[*] Đang tạo ảnh test chứa văn bản để test OCR...")
        img = Image.new("RGB", (1000, 500), color=(240, 244, 255))
        d = ImageDraw.Draw(img)
        
        # Arial là font chuẩn có sẵn trên Windows
        font_path = "C:\\Windows\\Fonts\\arial.ttf"
        try:
            font_title = ImageFont.truetype(font_path, 36)
            font_body = ImageFont.truetype(font_path, 22)
        except Exception:
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()
            
        # Tiêu đề ảnh
        d.rectangle([(0, 0), (1000, 80)], fill=(78, 124, 255))
        d.text((40, 20), "TIN PHÂN TÍCH KIỂM CHỨNG", fill=(255, 255, 255), font=font_title)
        
        # Nội dung tin giả mẫu
        lines = [
            "CỰC SỐC: Thần y bí truyền chữa khỏi hoàn toàn 100% bệnh ung thư!",
            "",
            "Một bài chia sẻ lan truyền chóng mặt trên Zalo và Facebook gần đây cho biết:",
            "Hợp chất tự nhiên chiết xuất từ lá cây trinh nữ hoàng cung phơi khô",
            "kết hợp nước chanh nóng ấm uống mỗi sáng sẽ tiêu diệt tế bào ung thư",
            "hoàn toàn chỉ sau 3 ngày mà không cần xạ trị hay hóa trị.",
            "Rất nhiều người đã hồi phục kỳ diệu. Hãy chia sẻ gấp để cứu người!!!",
        ]
        
        y = 120
        for line in lines:
            d.text((40, y), line, fill=(20, 20, 30), font=font_body)
            y += 40
            
        img.save("test_news_ocr.png")
        print("   ✅ Đã tạo xong ảnh test: test_news_ocr.png")
    except Exception as e:
        print(f"   ⚠️ Lỗi tạo ảnh test: {e}")

def run_demo_recording():
    # 1. Tạo ảnh test OCR
    generate_test_image()
    
    # 2. Khởi động Flask Server
    print("[*] Đang khởi động máy chủ Flask...")
    python_exe = os.path.join(".venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = "python"  # fallback nếu không có venv
        
    # Thiết lập biến môi trường UTF-8
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    
    server_proc = subprocess.Popen([python_exe, "app.py"], env=env)
    
    # Chờ server khởi động hoàn tất
    print("[*] Chờ Flask server sẵn sàng...")
    time.sleep(5)
    
    # 3. Sử dụng Playwright để tự động hóa và quay màn hình
    print("[*] Khởi động trình duyệt Playwright để quay video...")
    
    video_dir = os.path.join("static", "videos")
    os.makedirs(video_dir, exist_ok=True)
    
    with sync_playwright() as p:
        # Sử dụng Chromium headless
        browser = p.chromium.launch(headless=True)
        
        # Cấu hình quay video
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=video_dir,
            record_video_size={"width": 1280, "height": 720}
        )
        
        page = context.new_page()
        
        try:
            # ═══ BƯỚC 1: TRANG CHỦ ═══
            print("🎥 Bước 1: Mở Trang Chủ...")
            page.goto("http://127.0.0.1:5000", wait_until="networkidle")
            page.wait_for_timeout(3000)
            
            # Cuộn xuống nhẹ nhàng để xem giao diện
            page.evaluate("window.scrollTo({top: 400, behavior: 'smooth'})")
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo({top: 800, behavior: 'smooth'})")
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            page.wait_for_timeout(1500)
            
            # ═══ BƯỚC 2: PHÂN TÍCH & TEST ẢNH OCR ═══
            print("🎥 Bước 2: Truy cập trang Phân tích...")
            page.click("a.nav-link[href='/analyzer']")
            page.wait_for_timeout(2500)
            
            print("🎥 Bước 2b: Tải ảnh test OCR lên zone...")
            # Sử dụng set_input_files để chọn ảnh test
            page.set_input_files("#img-file-input", "test_news_ocr.png")
            
            # Đợi 1 giây để trigger auto-extract
            page.wait_for_timeout(1500)
            
            print("🎥 Bước 2c: Đang chờ EasyOCR trích xuất chữ và SVM phân tích...")
            # Chờ phần hiển thị phân tích SVM ảnh xuất hiện (tối đa 60s cho lần đầu tải model)
            try:
                page.wait_for_selector("#img-svm-analysis", state="visible", timeout=60000)
                print("   ✅ OCR đã hoàn thành!")
            except Exception as ocr_err:
                print(f"   ⚠️ OCR timeout hoặc lỗi: {ocr_err}")
                # Fallback: chờ ít nhất kết quả trích xuất
                try:
                    page.wait_for_selector("#img-extract-result", state="visible", timeout=30000)
                    print("   ✅ Ít nhất kết quả trích xuất đã hiện!")
                except Exception:
                    print("   ⚠️ Không thể chờ được OCR, tiếp tục...")
            
            page.wait_for_timeout(3000)
            
            # Cuộn xuống để xem form đã được điền tự động
            page.evaluate("document.getElementById('title').scrollIntoView({behavior: 'smooth', block: 'center'})")
            page.wait_for_timeout(2500)
            
            print("🎥 Bước 2d: Bấm nút Phân tích tin tức...")
            page.click("#submit-btn")
            
            # Chờ chuyển hướng sang trang kết quả
            try:
                page.wait_for_url("**/check", timeout=15000)
                print("   ✅ Đã chuyển hướng sang trang kết quả phân tích!")
            except Exception:
                print("   ⚠️ Không chuyển hướng được, tiếp tục...")
            
            page.wait_for_timeout(3000)
            
            # Cuộn xem kết quả chi tiết
            page.evaluate("window.scrollTo({top: 250, behavior: 'smooth'})")
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo({top: 550, behavior: 'smooth'})")
            page.wait_for_timeout(2500)
            page.evaluate("window.scrollTo({top: 900, behavior: 'smooth'})")
            page.wait_for_timeout(2500)
            page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            page.wait_for_timeout(1500)
            
            # ═══ BƯỚC 3: TRÒ CHUYỆN VỚI TRỢ LÝ AI (CHAT AL) ═══
            print("🎥 Bước 3: Chuyển sang trang Trợ lý AI...")
            page.click("a.nav-link[href='/ai-assistant']")
            page.wait_for_timeout(2500)
            
            print("🎥 Bước 3b: Gửi câu hỏi đầu tiên...")
            page.fill("#page-chat-textarea", "Xin chào! Bạn có thể giúp tôi phân biệt tin thật và tin giả thế nào?")
            page.wait_for_timeout(1000)
            page.click("#page-chat-send-btn")
            
            # Chờ AI trả lời (đợi tin nhắn bot xuất hiện)
            print("   ⏳ Đang chờ AI trả lời câu hỏi 1...")
            try:
                page.wait_for_selector(".assistant-msg.bot:nth-child(3)", timeout=15000)
            except Exception:
                pass  # Nếu selector không khớp, chờ thêm
            page.wait_for_timeout(5000)
            
            # Cuộn xuống chat
            page.evaluate("const el = document.getElementById('page-chat-messages'); if(el) el.scrollTop = el.scrollHeight;")
            page.wait_for_timeout(2000)
            
            print("🎥 Bước 3c: Gửi câu hỏi test chuyên sâu...")
            page.fill("#page-chat-textarea", "Uống nước chanh ấm mỗi sáng có thực sự chữa khỏi hoàn toàn 100% bệnh ung thư không?")
            page.wait_for_timeout(1000)
            page.click("#page-chat-send-btn")
            
            # Chờ AI phân tích RAG và phản hồi
            print("   ⏳ Đang chờ AI phân tích và trả lời câu hỏi 2...")
            page.wait_for_timeout(10000)
            
            # Cuộn xuống cuối chat
            page.evaluate("const el = document.getElementById('page-chat-messages'); if(el) el.scrollTop = el.scrollHeight;")
            page.wait_for_timeout(3000)
            
            # ═══ BƯỚC 4: DASHBOARD HIỆU SUẤT MÔ HÌNH ═══
            print("🎥 Bước 4: Mở Dashboard thống kê...")
            page.click("a.nav-link[href='/dashboard']")
            page.wait_for_timeout(4000)
            
            # Cuộn xuống xem chi tiết dashboard
            page.evaluate("window.scrollTo({top: 300, behavior: 'smooth'})")
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            page.wait_for_timeout(1500)
            
            # ═══ BƯỚC 5: LỊCH SỬ DỰ ĐOÁN ═══
            print("🎥 Bước 5: Mở trang Lịch sử...")
            page.click("a.nav-link[href='/history']")
            page.wait_for_timeout(3000)
            
            # Cuộn để xem lịch sử
            page.evaluate("window.scrollTo({top: 300, behavior: 'smooth'})")
            page.wait_for_timeout(2000)
            
            print("✅ Đã hoàn thành quay tất cả các bước demo!")
            
        except Exception as e:
            print(f"❌ Có lỗi xảy ra trong quá trình chạy script: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Lưu và đóng
            print("[*] Đóng trình duyệt...")
            context.close()
            
            # Đổi tên file video thành tên chuẩn
            video = page.video
            if video:
                orig_path = video.path()
                dest_path = os.path.join(video_dir, "demo_trustcheck.webm")
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                try:
                    os.rename(orig_path, dest_path)
                    print(f"🎉 THÀNH CÔNG! Video demo đã được quay và lưu tại: {dest_path}")
                except Exception as ex:
                    print(f"⚠️ Không thể đổi tên file video: {ex}. Video gốc lưu tại: {orig_path}")
            else:
                print("⚠️ Không quay được video nào.")
                
            browser.close()
            
    # Tắt Flask Server
    print("[*] Đang dừng máy chủ Flask...")
    server_proc.terminate()
    try:
        server_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_proc.kill()
    print("Done!")

if __name__ == "__main__":
    run_demo_recording()
