import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def extract_news_from_url(url: str) -> dict:
    """
    Quét và trích xuất nội dung bài báo mạng + siêu dữ liệu (metadata) từ URL.
    Trả về dict: { "title", "content", "image", "description", "author", "pub_date" }
    """
    if not url or not url.startswith("http"):
        raise ValueError("URL không hợp lệ. Vui lòng bắt đầu bằng http:// hoặc https://")

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

        # --- TÌM THEO TÊN MIỀN CHUYÊN BIỆT (DOMAIN-SPECIFIC SELECTORS) ---
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        domain_title = ""
        domain_desc = ""
        domain_content = ""
        domain_author = ""
        domain_pub_date = ""

        # Selector cho các báo lớn Việt Nam
        if "vnexpress.net" in domain:
            t_tag = soup.select_one('h1.title-detail')
            if t_tag: domain_title = t_tag.get_text(strip=True)
            d_tag = soup.select_one('p.description')
            if d_tag: domain_desc = d_tag.get_text(strip=True)
            p_tags = soup.select('article.fck_detail p.Normal')
            if p_tags: domain_content = "\n".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 15])
            a_tag = soup.select_one('p.Normal[style*="text-align:right"], p.author_mail')
            if a_tag: domain_author = a_tag.get_text(strip=True)
            date_tag = soup.select_one('span.date')
            if date_tag: domain_pub_date = date_tag.get_text(strip=True)
            
        elif "tuoitre.vn" in domain:
            t_tag = soup.select_one('h1.article-title')
            if t_tag: domain_title = t_tag.get_text(strip=True)
            d_tag = soup.select_one('h2.sapo')
            if d_tag: domain_desc = d_tag.get_text(strip=True)
            p_tags = soup.select('div.fck-content p, div#main-detail-body p')
            if p_tags: domain_content = "\n".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 15])
            a_tag = soup.select_one('.author, div.author-info')
            if a_tag: domain_author = a_tag.get_text(strip=True)
            
        elif "thanhnien.vn" in domain:
            t_tag = soup.select_one('h1.details__headline, h1.article-title')
            if t_tag: domain_title = t_tag.get_text(strip=True)
            d_tag = soup.select_one('h2.sapo, div.sapo')
            if d_tag: domain_desc = d_tag.get_text(strip=True)
            p_tags = soup.select('div.details__content p, div#cms-body p')
            if p_tags: domain_content = "\n".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 15])
            a_tag = soup.select_one('.details__author, div.author')
            if a_tag: domain_author = a_tag.get_text(strip=True)
            
        elif "dantri.com.vn" in domain:
            t_tag = soup.select_one('h1.title-page, h1.dt-news__title')
            if t_tag: domain_title = t_tag.get_text(strip=True)
            d_tag = soup.select_one('h2.sapo, h2.singular-sapo')
            if d_tag: domain_desc = d_tag.get_text(strip=True)
            p_tags = soup.select('div.singular-content p, div.dt-news__content p')
            if p_tags: domain_content = "\n".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 15])
            a_tag = soup.select_one('.author-name, div.author')
            if a_tag: domain_author = a_tag.get_text(strip=True)
            
        elif "vietnamnet.vn" in domain:
            t_tag = soup.select_one('h1.content-detail-title, h1.title')
            if t_tag: domain_title = t_tag.get_text(strip=True)
            d_tag = soup.select_one('div.content-detail-sapo, .sapo')
            if d_tag: domain_desc = d_tag.get_text(strip=True)
            p_tags = soup.select('div.maincontent p, div#maincontent p')
            if p_tags: domain_content = "\n".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 15])

        elif "laodong.vn" in domain:
            t_tag = soup.select_one('h1.article-title, h1.title')
            if t_tag: domain_title = t_tag.get_text(strip=True)
            d_tag = soup.select_one('p.sapo, div.sapo')
            if d_tag: domain_desc = d_tag.get_text(strip=True)
            p_tags = soup.select('div.article-content p, div.content p')
            if p_tags: domain_content = "\n".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 15])
            a_tag = soup.select_one('.author, div.author')
            if a_tag: domain_author = a_tag.get_text(strip=True)

        elif "kenh14.vn" in domain:
            t_tag = soup.select_one('h1.kbuc-title, h1.title-detail')
            if t_tag: domain_title = t_tag.get_text(strip=True)
            d_tag = soup.select_one('h2.knc-sapo, .sapo')
            if d_tag: domain_desc = d_tag.get_text(strip=True)
            p_tags = soup.select('div.knc-content p, div.kbuc-content p')
            if p_tags: domain_content = "\n".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 15])
            a_tag = soup.select_one('.kb-author, .author')
            if a_tag: domain_author = a_tag.get_text(strip=True)

        elif "vtcnews.vn" in domain or "vtc.vn" in domain:
            t_tag = soup.select_one('h1.font28, h1.title-detail, .article-title')
            if t_tag: domain_title = t_tag.get_text(strip=True)
            d_tag = soup.select_one('h2.sapo, h2.font16')
            if d_tag: domain_desc = d_tag.get_text(strip=True)
            p_tags = soup.select('div.content-wrapper p, div.article-content p, div.content p')
            if p_tags: domain_content = "\n".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 15])
            a_tag = soup.select_one('.author, div.author')
            if a_tag: domain_author = a_tag.get_text(strip=True)

        elif "vietnamplus.vn" in domain:
            t_tag = soup.select_one('h1.details__headline, h1.article-title')
            if t_tag: domain_title = t_tag.get_text(strip=True)
            d_tag = soup.select_one('h2.sapo')
            if d_tag: domain_desc = d_tag.get_text(strip=True)
            p_tags = soup.select('div.article-body p, div.details__content p')
            if p_tags: domain_content = "\n".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 15])
            a_tag = soup.select_one('.details__author, div.author')
            if a_tag: domain_author = a_tag.get_text(strip=True)

        elif "baomoi.com" in domain:
            t_tag = soup.select_one('h1.article__header, h1.title')
            if t_tag: domain_title = t_tag.get_text(strip=True)
            d_tag = soup.select_one('div.article__sapo, .sapo')
            if d_tag: domain_desc = d_tag.get_text(strip=True)
            p_tags = soup.select('div.article__body p, div.content p')
            if p_tags: domain_content = "\n".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 15])

        # --- TRÍCH XUẤT SIÊU DỮ LIỆU CHUNG (FALLBACK) ---
        image = ""
        meta_image = soup.find('meta', property='og:image') or soup.find('meta', attrs={"name": "twitter:image"})
        if meta_image and meta_image.get('content'):
            image = meta_image['content']

        description = domain_desc
        if not description:
            meta_desc = soup.find('meta', property='og:description') or soup.find('meta', attrs={"name": "description"})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc['content'].strip()

        author = domain_author
        if not author:
            meta_author = soup.find('meta', attrs={"name": "author"}) or soup.find('meta', property='og:author') or soup.find('meta', property='article:author')
            if meta_author and meta_author.get('content'):
                author = meta_author['content'].strip()
            else:
                author_tag = soup.find(class_=lambda x: x and 'author' in x.lower())
                if author_tag:
                    author = author_tag.get_text(strip=True)

        pub_date = domain_pub_date
        if not pub_date:
            meta_time = soup.find('meta', property='article:published_time') or soup.find('meta', attrs={"name": "pubdate"}) or soup.find('meta', property='og:pubdate')
            if meta_time and meta_time.get('content'):
                pub_date = meta_time['content'].strip()
                if len(pub_date) > 16:
                    pub_date = pub_date.replace('T', ' ').split('+')[0][:16]
            else:
                time_tag = soup.find('time')
                if time_tag:
                    pub_date = time_tag.get_text(strip=True)

        title = domain_title
        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(separator=' ', strip=True)
            if not title:
                og_title = soup.find('meta', property='og:title')
                if og_title and og_title.get('content'):
                    title = og_title['content']
                elif soup.title:
                    title = soup.title.string.strip()

        content = domain_content
        if not content:
            # Xoá các tag không cần thiết trước khi quét text chính
            for junk in soup(["script", "style", "noscript", "meta", "link", "header", "footer", "nav", "aside"]):
                junk.extract()
            
            paragraphs = []
            article_elem = soup.find('article')
            if article_elem:
                p_tags = article_elem.find_all('p')
                for p in p_tags:
                    text = p.get_text(separator=' ', strip=True)
                    if len(text) > 20:
                        paragraphs.append(text)
            if not paragraphs:
                for p in soup.find_all('p'):
                    text = p.get_text(separator=' ', strip=True)
                    if len(text) > 30:
                        paragraphs.append(text)
            content = "\n".join(paragraphs)

        return {
            "title": title,
            "content": content,
            "image": image,
            "description": description,
            "author": author,
            "pub_date": pub_date
        }

    except requests.exceptions.RequestException as e:
        raise Exception(f"Không thể tải đường dẫn: {str(e)}")
    except Exception as e:
        raise Exception(f"Lỗi khi trích xuất dữ liệu: {str(e)}")
