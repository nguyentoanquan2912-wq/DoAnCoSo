/* ═══════════════════════════════════
   ANALYZER PAGE LOGIC
═══════════════════════════════════ */

let selectedModel = 'lr';

/* ─── Model selector ─────────── */
document.querySelectorAll('.model-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.model-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedModel = btn.dataset.model;
  });
});

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
  document.getElementById('result-container').innerHTML = '';
}

/* ─── URL Fetch (Crawler) ────── */
const btnFetchUrl = document.getElementById('btn-fetch-url');
if (btnFetchUrl) {
  btnFetchUrl.addEventListener('click', async () => {
    const url = document.getElementById('url-input').value.trim();
    if (!url) {
      showToast('Vui lòng nhập đường dẫn URL', 'warning');
      return;
    }
    
    btnFetchUrl.disabled = true;
    const oldText = btnFetchUrl.innerHTML;
    btnFetchUrl.innerHTML = '<div class="spinner" style="width:14px;height:14px;border-width:2px;display:inline-block;vertical-align:middle;margin-right:6px;"></div> Tải...';

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
      showToast(err.message, 'error');
    } finally {
      btnFetchUrl.disabled = false;
      btnFetchUrl.innerHTML = oldText;
    }
  });
}

/* ─── Form submit ────────────── */
document.getElementById('analyze-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const title = document.getElementById('title').value.trim();
  const content = document.getElementById('content').value.trim();

  if (!title && !content) {
    showToast('Vui lòng nhập tiêu đề hoặc nội dung tin tức.', 'warning');
    return;
  }

  const btn = document.getElementById('submit-btn');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Đang phân tích...';

  const resultContainer = document.getElementById('result-container');
  resultContainer.innerHTML = '';

  try {
    const res = await fetch('/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content, model: selectedModel })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || 'Lỗi không xác định');
    }

    renderResults(data.results, selectedModel);
    showToast('Phân tích hoàn tất!', 'success');

  } catch (err) {
    showToast(err.message, 'error');
    resultContainer.innerHTML = `
      <div class="result-card fake" style="text-align:center;padding:28px;">
        <div style="font-size:36px;margin-bottom:12px;">⚠️</div>
        <div style="font-size:16px;font-weight:700;color:var(--danger-light);">${err.message}</div>
        <div style="font-size:13px;color:var(--text-secondary);margin-top:8px;">
          Hãy chắc chắn đã chạy <code style="background:rgba(255,255,255,0.08);padding:2px 6px;border-radius:6px;">python -m src.train</code> trước.
        </div>
      </div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>🔍</span> Phân tích tin tức';
  }
});

/* ─── Render results ─────────── */
function renderResults(results, modelKey) {
  const container = document.getElementById('result-container');
  const keys = Object.keys(results);

  if (modelKey === 'all' || keys.length > 1) {
    renderMultiResults(results, container);
  } else {
    const r = results[keys[0]];
    renderSingleResult(r, container);
  }
}

function renderSingleResult(r, container) {
  const isReal = r.label === 'reliable';
  const cls = isReal ? 'real' : 'fake';
  const icon = isReal ? '✅' : '⚠️';
  const notes = {
    real: 'Hệ thống đánh giá nội dung này có mức độ đáng tin cậy tương đối cao dựa trên mô hình đã huấn luyện. Tuy nhiên, hãy luôn kiểm chứng thông tin từ nhiều nguồn chính thống.',
    fake: 'Hệ thống phát hiện nội dung này có một số dấu hiệu không đáng tin cậy. Nên kiểm chứng thêm từ các nguồn báo chí chính thống và cơ quan có thẩm quyền.'
  };

  container.innerHTML = `
    <div class="result-container animate-in">
      <div class="result-card ${cls}">
        <div class="result-header">
          <div>
            <div class="result-label">Kết quả phân tích</div>
            <div class="result-verdict">${r.display}</div>
          </div>
          <div style="text-align:right;">
            <span class="result-badge ${cls}">${icon} ${isReal ? 'Tin thật' : 'Tin giả'}</span>
            <div class="result-prob" style="margin-top:10px;">
              <div class="result-prob-label">Độ tin cậy dự đoán</div>
              <div class="result-prob-value">${r.probability}<span style="font-size:18px;color:var(--text-secondary);">%</span></div>
            </div>
          </div>
        </div>
        <div class="progress-track">
          <div class="progress-fill ${cls}" style="width:0%" id="pbar"></div>
        </div>
        <p class="result-note">${notes[isReal ? 'real' : 'fake']}</p>
        <div style="margin-top:14px;font-size:13px;color:var(--text-muted);">
          Mô hình: <strong style="color:var(--text-secondary);">${r.model_name}</strong>
        </div>
      </div>
    </div>`;

  // Animate progress bar
  setTimeout(() => {
    const pbar = document.getElementById('pbar');
    if (pbar) pbar.style.width = r.probability + '%';
  }, 100);
}

function renderMultiResults(results, container) {
  const keys = Object.keys(results);
  const votes = { reliable: 0, unreliable: 0 };
  keys.forEach(k => votes[results[k].label]++);
  const consensus = votes.reliable >= votes.unreliable ? 'reliable' : 'unreliable';
  const isReal = consensus === 'reliable';

  const cards = keys.map((key, i) => {
    const r = results[key];
    const cls = r.label === 'reliable' ? 'real' : 'fake';
    return `
      <div class="model-result-item" style="animation-delay:${i * 0.1}s">
        <div>
          <div class="model-result-name">${r.model_name}</div>
        </div>
        <span class="result-badge ${cls}" style="font-size:12px;">${r.label === 'reliable' ? '✅ Tin thật' : '⚠️ Tin giả'}</span>
        <div class="model-result-prob">${r.probability}%</div>
      </div>`;
  }).join('');

  container.innerHTML = `
    <div class="result-container animate-in">
      <div style="text-align:center;margin-bottom:20px;padding:20px;background:${isReal ? 'var(--success-bg)' : 'var(--danger-bg)'};border:1px solid ${isReal ? 'var(--success-border)' : 'var(--danger-border)'};border-radius:var(--radius-lg);">
        <div style="font-size:40px;margin-bottom:8px;">${isReal ? '✅' : '⚠️'}</div>
        <div style="font-size:14px;color:var(--text-secondary);margin-bottom:4px;">Kết quả tổng hợp (${keys.length} mô hình)</div>
        <div style="font-size:22px;font-weight:800;color:var(--text-white);">${isReal ? 'Tin đáng tin cậy' : 'Tin có dấu hiệu không đáng tin cậy'}</div>
        <div style="margin-top:8px;font-size:13px;color:var(--text-secondary);">Đồng thuận bởi ${Math.max(votes.reliable, votes.unreliable)}/${keys.length} mô hình</div>
      </div>
      <div class="multi-results">${cards}</div>
    </div>`;
}

// Expose globals
window.fillExample = fillExample;
window.clearForm = clearForm;
