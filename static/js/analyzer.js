/* ═══════════════════════════════════
   ANALYZER PAGE LOGIC
═══════════════════════════════════ */

let selectedModel = 'svm';

/* ─── Quick fill buttons ─────── */
function fillExample(type) {
  const examples = {
    fake: {
      title: 'Thuốc bí truyền chữa ung thư 100% trong 3 ngày',
      content: 'Một bài đăng trên mạng xã hội quảng cáo loại thuốc bí truyền có thể chữa ung thư hoàn toàn trong ba ngày mà không cần xạ trị hay hóa trị, được nhiều người chia sẻ rộng rãi.'
    },
    real: {
      title: 'Ngân hàng Nhà nước công bố điều chỉnh lãi suất điều hành',
      content: 'Ngân hàng Nhà nước Việt Nam vừa ban hành quyết định điều chỉnh lãi suất điều hành nhằm hỗ trợ nền kinh tế phục hồi, có hiệu lực từ ngày ký theo thông báo chính thức.'
    }
  };
  const ex = examples[type];
  if (ex) {
    document.getElementById('title').value = ex.title;
    document.getElementById('content').value = ex.content;
  }
}

function clearForm() {
  document.getElementById('title').value = '';
  document.getElementById('content').value = '';
  const urlInput = document.getElementById('url-input');
  if (urlInput) urlInput.value = '';
}

/* ─── URL Fetch (Crawler — tự động tải nội dung khi dán) ────── */
async function fetchUrlContent(url) {
  const urlInput = document.getElementById('url-input');
  if (urlInput) urlInput.value = url;

  showLoading('Đang tự động tải nội dung từ liên kết...');
  try {
    const res = await fetch('/api/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    const data = await res.json();
    
    if (!res.ok) throw new Error(data.error || 'Không thể cào dữ liệu URL');
    
    document.getElementById('title').value = data.data.title;
    document.getElementById('content').value = data.data.content;
    showToast('Đã tải thành công nội dung bài báo!', 'success');
  } catch (err) {
    showToast('Lỗi tải bài báo: ' + err.message, 'error');
  } finally {
    hideLoading();
  }
}

const btnFetchUrl = document.getElementById('btn-fetch-url');
if (btnFetchUrl) {
  btnFetchUrl.addEventListener('click', () => {
    const url = document.getElementById('url-input').value.trim();
    if (!url) {
      showToast('Vui lòng nhập đường dẫn URL', 'warning');
      return;
    }
    fetchUrlContent(url);
  });
}

// Tự động nhận diện URL dán vào ô Tiêu đề, Nội dung hoặc Link
function handleUrlPaste(e) {
  const pastedText = e.clipboardData?.getData('text');
  if (pastedText && (pastedText.startsWith('http://') || pastedText.startsWith('https://'))) {
    e.preventDefault();
    fetchUrlContent(pastedText.trim());
  }
}

// Gắn sự kiện khi DOM load xong
document.addEventListener('DOMContentLoaded', () => {
  const titleEl = document.getElementById('title');
  const contentEl = document.getElementById('content');
  const urlEl = document.getElementById('url-input');

  if (titleEl) titleEl.addEventListener('paste', handleUrlPaste);
  if (contentEl) contentEl.addEventListener('paste', handleUrlPaste);
  if (urlEl) urlEl.addEventListener('paste', handleUrlPaste);
});

/* ─── Form submit — chuyển sang POST /check ────────────── */
document.getElementById('analyze-form').addEventListener('submit', (e) => {
  const title = document.getElementById('title').value.trim();
  const content = document.getElementById('content').value.trim();
  const url = document.getElementById('url-input') ? document.getElementById('url-input').value.trim() : '';

  // Validate: cần ít nhất 1 trong 3 trường
  if (!title && !content && !url) {
    e.preventDefault();
    showToast('Vui lòng nhập tiêu đề, nội dung hoặc URL bài báo.', 'warning');
    return;
  }

  // Hiệu ứng loading khi submit
  const btn = document.getElementById('submit-btn');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Đang phân tích...';

  // Cho form submit tự nhiên (POST /check)
});

// Expose globals
window.fillExample = fillExample;
window.clearForm = clearForm;

/* ═══════════════════════════════════════════
   IMAGE PASTE / DROP / UPLOAD + GEMINI VISION
   ═══════════════════════════════════════════ */
(function () {
  const pasteZone    = document.getElementById('img-paste-zone');
  const fileInput    = document.getElementById('img-file-input');
  const previewWrap  = document.getElementById('img-preview-wrap');
  const previewImg   = document.getElementById('img-preview');
  const removeBtn    = document.getElementById('img-remove-btn');
  const extractAct   = document.getElementById('img-extract-actions');
  const extractBtn   = document.getElementById('btn-extract-image');
  const extractBtnIcon = document.getElementById('extract-btn-icon');
  const extractResult = document.getElementById('img-extract-result');
  const reextractBtn  = document.getElementById('btn-reextract');

  if (!pasteZone) return;

  let currentImageBase64 = null;
  let currentMimeType = 'image/jpeg';

  // ─── Xử lý file ảnh ─────────────────────
  function handleImageFile(file) {
    if (!file || !file.type.startsWith('image/')) {
      showToast('Vui lòng chọn file ảnh hợp lệ (PNG, JPG, WEBP...)', 'warning');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      showToast('Ảnh quá lớn (tối đa 10MB)', 'warning');
      return;
    }

    currentMimeType = file.type;
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target.result;
      // Tách phần base64 thuần (bỏ prefix data:...)
      const parts = dataUrl.split(',');
      currentImageBase64 = parts[1];

      // Hiện preview
      previewImg.src = dataUrl;
      pasteZone.classList.add('has-image');
      previewWrap.style.display = 'block';
      extractAct.style.display = 'block';
      extractResult.style.display = 'none';
      showToast('Đã tải ảnh thành công! Đang tự động trích xuất nội dung bằng AI...', 'success');
      
      // Tự động gọi trích xuất văn bản từ ảnh
      setTimeout(doExtract, 350);
    };
    reader.readAsDataURL(file);
  }

  // ─── Click vào zone → mở file picker ────
  pasteZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) handleImageFile(e.target.files[0]);
    fileInput.value = '';
  });

  // ─── Paste ảnh (Ctrl+V) ──────────────────
  document.addEventListener('paste', (e) => {
    // 1. Kiểm tra e.clipboardData.files trước (cho file ảnh copy từ File Explorer)
    const files = e.clipboardData?.files;
    if (files && files.length > 0) {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file.type.startsWith('image/')) {
          e.preventDefault();
          handleImageFile(file);
          if (pasteZone) pasteZone.scrollIntoView({ behavior: 'smooth', block: 'center' });
          return;
        }
      }
    }

    // 2. Kiểm tra e.clipboardData.items (cho chụp màn hình/ảnh copy trên web)
    const items = e.clipboardData?.items;
    if (items) {
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.type.startsWith('image/')) {
          const file = item.getAsFile();
          if (file) {
            e.preventDefault();
            handleImageFile(file);
            if (pasteZone) pasteZone.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
          }
        }
      }
    }
  });

  // ─── Drag & Drop ─────────────────────────
  pasteZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    pasteZone.classList.add('dragover');
  });
  pasteZone.addEventListener('dragleave', () => pasteZone.classList.remove('dragover'));
  pasteZone.addEventListener('drop', (e) => {
    e.preventDefault();
    pasteZone.classList.remove('dragover');
    const file = e.dataTransfer?.files[0];
    if (file) handleImageFile(file);
  });

  // ─── Xóa ảnh ─────────────────────────────
  removeBtn.addEventListener('click', () => {
    currentImageBase64 = null;
    previewImg.src = '';
    previewWrap.style.display = 'none';
    extractAct.style.display = 'none';
    extractResult.style.display = 'none';
    pasteZone.classList.remove('has-image');
    showToast('Đã xóa ảnh.', 'info');
  });

  // ─── Trích xuất văn bản bằng EasyOCR cục bộ + SVM Analysis ─
  async function doExtract() {
    if (!currentImageBase64) {
      showToast('Chưa có ảnh nào được chọn.', 'warning');
      return;
    }

    // UI loading
    extractBtn.disabled = true;
    extractBtnIcon.textContent = '⏳';
    extractBtn.innerHTML = '<span id="extract-btn-icon">⏳</span> Đang phân tích ảnh bằng OCR...';

    try {
      const res = await fetch('/api/extract-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_base64: currentImageBase64,
          mime_type: currentMimeType
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Không thể trích xuất văn bản từ ảnh.');

      // Điền vào form
      const titleEl = document.getElementById('title');
      const contentEl = document.getElementById('content');
      if (data.title) titleEl.value = data.title;
      if (data.content) contentEl.value = data.content;

      // Hiện kết quả
      extractAct.style.display = 'none';
      extractResult.style.display = 'flex';

      // ─── Hiển thị mini SVM Analysis ───
      let analysisEl = document.getElementById('img-svm-analysis');
      if (!analysisEl) {
        analysisEl = document.createElement('div');
        analysisEl.id = 'img-svm-analysis';
        extractResult.parentElement.appendChild(analysisEl);
      }

      if (data.svm_analysis) {
        const a = data.svm_analysis;
        const isReal = a.label === 'reliable';
        const badgeColor = isReal
          ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)';
        const borderColor = isReal
          ? 'rgba(16,185,129,0.5)' : 'rgba(239,68,68,0.5)';
        const textColor = isReal
          ? 'var(--success-light)' : 'var(--danger-light)';
        const icon = isReal ? '✅' : '⚠️';

        analysisEl.innerHTML = `
          <div style="margin-top:16px; padding:16px 20px; background:${badgeColor}; border:1px solid ${borderColor}; border-radius:var(--radius-md); animation: fadeSlideUp 0.4s ease;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
              <span style="font-size:24px;">${icon}</span>
              <div>
                <div style="font-weight:700; color:${textColor}; font-size:15px;">${a.display}</div>
                <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">Phân tích tự động bằng Linear SVM</div>
              </div>
              <div style="margin-left:auto; text-align:right;">
                <div style="font-size:28px; font-weight:800; color:${textColor};">${a.probability}%</div>
                <div style="font-size:11px; color:var(--text-muted);">Độ tin cậy</div>
              </div>
            </div>
            <div style="height:6px; background:rgba(255,255,255,0.06); border-radius:10px; overflow:hidden; margin-top:8px;">
              <div style="height:100%; width:${a.probability}%; background:${textColor}; border-radius:10px; transition:width 0.6s ease;"></div>
            </div>
            <div style="font-size:12px; color:var(--text-muted); margin-top:10px; text-align:center;">
              💡 Nhấn <strong style="color:var(--primary-light);">Phân tích tin tức</strong> bên dưới để xem báo cáo đầy đủ
            </div>
          </div>`;
        analysisEl.style.display = 'block';
      } else {
        analysisEl.style.display = 'none';
      }

      showToast('✅ Đã trích xuất văn bản từ ảnh thành công!', 'success');

      // Scroll đến form
      titleEl.scrollIntoView({ behavior: 'smooth', block: 'center' });

    } catch (err) {
      showToast('❌ ' + err.message, 'error');
    } finally {
      extractBtn.disabled = false;
      extractBtn.innerHTML = '<span id="extract-btn-icon">🔍</span> Trích xuất văn bản từ ảnh bằng OCR';
    }
  }

  extractBtn.addEventListener('click', doExtract);
  reextractBtn.addEventListener('click', () => {
    extractResult.style.display = 'none';
    extractAct.style.display = 'block';
    const sEl = document.getElementById('img-svm-analysis');
    if (sEl) sEl.style.display = 'none';
    doExtract();
  });
})();

