/* ═══════════════════════════════════
   AI DEEP AUDIT LOGIC
   ═══════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  const initialState = document.getElementById('audit-initial-state');
  const loadingState = document.getElementById('audit-loading-state');
  const resultState = document.getElementById('audit-result-state');
  const startBtn = document.getElementById('btn-start-audit');
  const keyWarning = document.getElementById('audit-key-warning');
  const reportContent = document.getElementById('audit-report-content');
  const copyBtn = document.getElementById('btn-copy-audit');

  let rawReportText = '';

  // Hiện trạng thái engine nội bộ
  if (keyWarning) {
    keyWarning.style.background = 'rgba(16, 185, 129, 0.08)';
    keyWarning.style.borderColor = 'rgba(16, 185, 129, 0.3)';
    keyWarning.innerHTML = `
      <span style="font-size: 18px; float: left; margin-right: 10px;">🤖</span>
      <div style="font-size: 13.0px; color: var(--text-primary); line-height: 1.5;">
        <strong>AI Engine Nội Bộ:</strong> Sẵn sàng thẩm định bằng NLP + Machine Learning + SQLite RAG cục bộ. Không cần API Key.
      </div>`;
    keyWarning.style.display = 'block';
  }

  startBtn.addEventListener('click', async () => {
    showToast('Đang khởi chạy TrustCheck AI Engine...', 'info', 3000);

    const title = document.getElementById('audit-title-val')?.textContent.trim() || '';
    const content = document.getElementById('audit-content-val')?.textContent.trim() || '';

    initialState.style.display = 'none';
    loadingState.style.display = 'block';

    try {
      const res = await fetch('/api/ai-audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title,
          content: content
        })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Lỗi không xác định khi gọi API Thẩm định.');
      }

      rawReportText = data.report;
      reportContent.innerHTML = renderMarkdown(rawReportText);
      
      loadingState.style.display = 'none';
      resultState.style.display = 'block';
      showToast('Thẩm định chuyên sâu hoàn tất!', 'success');

    } catch (err) {
      loadingState.style.display = 'none';
      initialState.style.display = 'block';
      showToast(err.message, 'error');
    }
  });

  // Copy report
  copyBtn.addEventListener('click', () => {
    if (!rawReportText) return;
    navigator.clipboard.writeText(rawReportText)
      .then(() => showToast('Đã sao chép báo cáo vào bộ nhớ tạm!', 'success'))
      .catch(() => showToast('Không thể sao chép tự động.', 'error'));
  });

  // Line-by-line Markdown Parser
  function renderMarkdown(text) {
    if (!text) return '';
    const lines = text.split('\n');
    let inList = false;
    let inQuote = false;
    let htmlLines = [];

    for (let i = 0; i < lines.length; i++) {
      let line = lines[i].trim();

      // Handle Blockquotes
      if (line.startsWith('>')) {
        if (!inQuote) {
          inQuote = true;
          htmlLines.push('<blockquote style="border-left: 4px solid var(--primary); padding-left: 14px; color: var(--text-secondary); margin: 12px 0;">');
        }
        line = line.substring(1).trim();
      } else if (inQuote && !line.startsWith('>')) {
        inQuote = false;
        htmlLines.push('</blockquote>');
      }

      // Handle Bullet lists
      const listMatch = line.match(/^[\-\*]\s+(.*)$/);
      if (listMatch) {
        if (!inList) {
          inList = true;
          htmlLines.push('<ul style="list-style: disc; padding-left: 20px; margin-bottom: 12px;">');
        }
        line = listMatch[1];
        line = `<li style="margin-bottom: 6px;">${parseInlineMarkdown(line)}</li>`;
        htmlLines.push(line);
        continue;
      } else {
        if (inList) {
          inList = false;
          htmlLines.push('</ul>');
        }
      }

      // Handle Headings
      if (line.startsWith('### ')) {
        htmlLines.push(`<h3 style="font-size: 16px; font-weight: 700; color: var(--text-white); margin: 20px 0 10px;">${parseInlineMarkdown(line.substring(4))}</h3>`);
      } else if (line.startsWith('## ')) {
        htmlLines.push(`<h2 style="font-size: 18px; font-weight: 800; color: var(--text-white); border-bottom: 1px solid var(--border-light); padding-bottom: 6px; margin: 24px 0 12px;">${parseInlineMarkdown(line.substring(3))}</h2>`);
      } else if (line.startsWith('# ')) {
        htmlLines.push(`<h1 style="font-size: 22px; font-weight: 900; color: var(--text-white); margin: 28px 0 16px;">${parseInlineMarkdown(line.substring(2))}</h1>`);
      } else if (line === '') {
        if (!inQuote) {
          htmlLines.push('<br>');
        }
      } else {
        // Normal paragraph
        let parsed = parseInlineMarkdown(line);
        htmlLines.push(`<p style="margin-bottom: 12px;">${parsed}</p>`);
      }
    }

    if (inList) htmlLines.push('</ul>');
    if (inQuote) htmlLines.push('</blockquote>');

    return htmlLines.join('\n');
  }

  function parseInlineMarkdown(text) {
    // Escape HTML tags to prevent XSS
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Inline code
    html = html.replace(/`(.*?)`/g, '<code>$1</code>');
    return html;
  }

  // ─── Đóng góp dữ liệu bài viết ──────────────────────────────────
  window.contributeArticle = async function(label) {
    const title = document.getElementById('audit-title-val')?.textContent.trim() || '';
    const content = document.getElementById('audit-content-val')?.textContent.trim() || '';
    
    if (!title || !content) {
      showToast('Không có tiêu đề hoặc nội dung để đóng góp.', 'warning');
      return;
    }
    
    const actionsRow = document.getElementById('contribute-actions-row');
    const originalContent = actionsRow.innerHTML;
    actionsRow.innerHTML = '<div class="spinner" style="width:14px;height:14px;border-width:2px;display:inline-block;vertical-align:middle;margin-right:6px;"></div> Đang ghi nhận...';
    
    try {
      const res = await fetch('/api/dataset/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content, label })
      });
      const data = await res.json();
      
      if (!res.ok) throw new Error(data.error || 'Lỗi lưu dữ liệu');
      
      showToast('🎉 ' + data.message, 'success');
      actionsRow.innerHTML = `<span style="color:var(--success); font-size:13.5px; font-weight:600;">✅ Đã đóng góp bài viết thành công làm tin ${label === 'reliable' ? 'THẬT' : 'GIẢ'}!</span>`;
      
      // Auto pulse trigger retrain button
      const retrainBtn = document.getElementById('btn-trigger-retrain');
      if (retrainBtn) {
        retrainBtn.classList.add('pulse');
        setTimeout(() => retrainBtn.classList.remove('pulse'), 5000);
      }
    } catch (err) {
      showToast(err.message, 'error');
      actionsRow.innerHTML = originalContent;
    }
  };

  // ─── Kích hoạt huấn luyện lại mô hình ────────────────────────────
  window.triggerRetrain = async function() {
    const retrainBtn = document.getElementById('btn-trigger-retrain');
    const statusDiv = document.getElementById('retrain-loading-status');
    
    retrainBtn.disabled = true;
    statusDiv.style.display = 'flex';
    
    try {
      const res = await fetch('/api/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      
      if (!res.ok) throw new Error(data.error || 'Lỗi kích hoạt huấn luyện');
      
      showToast('⚡ ' + data.message, 'info');
      
      // Bắt đầu vòng lặp thăm dò trạng thái (polling) cho đến khi huấn luyện xong
      pollTrainingStatus();
    } catch (err) {
      showToast(err.message, 'error');
      retrainBtn.disabled = false;
      statusDiv.style.display = 'none';
    }
  };

  async function pollTrainingStatus() {
    const retrainBtn = document.getElementById('btn-trigger-retrain');
    const statusDiv = document.getElementById('retrain-loading-status');
    
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/train/status');
        const data = await res.json();
        
        if (!data.in_progress) {
          clearInterval(interval);
          retrainBtn.disabled = false;
          statusDiv.style.display = 'none';
          
          if (data.error) {
            showToast('❌ Huấn luyện thất bại: ' + data.error, 'error');
          } else {
            showToast('🚀 Đã huấn luyện xong mô hình Linear SVM! Tri thức đã được cập nhật!', 'success');
            // Tải lại trang sau 1.5 giây để xem điểm số mới cập nhật
            setTimeout(() => window.location.reload(), 1500);
          }
        }
      } catch (err) {
        clearInterval(interval);
        retrainBtn.disabled = false;
        statusDiv.style.display = 'none';
        showToast('⚠️ Lỗi kiểm tra trạng thái huấn luyện.', 'warning');
      }
    }, 1500);
  }
});
