import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def extract_news_from_url(url: str) -> dict:
    """
    Quét và trích xuất nội dung bài báo mạng từ URL.
    Trả về dict { "title": str, "content": str }
    """
    if not url or not url.startswith("http"):
        raise ValueError("URL không hợp lệ. Vui lòng bắt đầu bằng http:// hoặc https://")

    # Sử dụng User-Agent thông dụng để không bị chặn bởi các firewall đơn giản
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # BS4 hỗ trợ lấy HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Xoá các tag không cần thiết (script, style)
        for junk in soup(["script", "style", "noscript", "meta", "link", "header", "footer", "nav", "aside"]):
            junk.extract()

        # --- TÌM TITLE ---
        title = ""
        # 1. Thử kiếm thẻ h1 đầu tiên (thường là tiêu đề báo)
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(separator=' ', strip=True)
        # 2. Rớt qua thẻ title hoặc og:title nếu không thấy H1
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title['content']
            elif soup.title:
                title = soup.title.string.strip()

        # --- TÌM NỘI DUNG CHÍNH ---
        paragraphs = []
        
        # Chiến lược 1: Tìm vùng nội dung chính dựa vào article tag
        article_elem = soup.find('article')
        if article_elem:
            p_tags = article_elem.find_all('p')
            for p in p_tags:
                text = p.get_text(separator=' ', strip=True)
                if len(text) > 20: # Lọc những câu quá ngắn
                    paragraphs.append(text)

        # Chiến lược 2: Nếu thẻ article rỗng, quệt quét tất cả thẻ p trên trang
        if not paragraphs:
            for p in soup.find_all('p'):
                text = p.get_text(separator=' ', strip=True)
                if len(text) > 30: # Báo vnexpress, tuoitre... thường mỗi p khá dài
                    paragraphs.append(text)

        content = "\n".join(paragraphs)

        return {
            "title": title,
            "content": content
        }

    except requests.exceptions.RequestException as e:
        raise Exception(f"Không thể tải đường dẫn: {str(e)}")
    except Exception as e:
        raise Exception(f"Lỗi khi trích xuất dữ liệu: {str(e)}")
