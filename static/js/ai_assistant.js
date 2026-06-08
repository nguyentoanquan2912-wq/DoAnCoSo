/* ═══════════════════════════════════
   DEDICATED AI ASSISTANT LOGIC
   ═══════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  const chatMessages = document.getElementById('page-chat-messages');
  const textarea = document.getElementById('page-chat-textarea');
  const sendBtn = document.getElementById('page-chat-send-btn');
  const clearBtn = document.getElementById('page-btn-clear');

  let conversationHistory = [];
  let activeModel = 'local-core';

  // Clear chat history
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      conversationHistory = [];
      chatMessages.innerHTML = `
        <div class="assistant-msg bot">
          <div class="msg-avatar">🤖</div>
          <div class="msg-content">
            <p>Lịch sử hội thoại đã được xoá. Hãy bắt đầu cuộc trò chuyện mới!</p>
          </div>
        </div>`;
      showToast('Đã xoá lịch sử hội thoại!', 'success');
    });
  }

  // Engine AI nội bộ - không cần cấu hình API Key

  // Đồng bộ trạng thái nút gửi
  function updateSendButton() {
    sendBtn.disabled = !textarea.value.trim();
  }

  // Tự động điều chỉnh kích thước textarea
  function adjustTextareaHeight() {
    textarea.style.height = '46px';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
  }

  textarea.addEventListener('input', () => {
    adjustTextareaHeight();
    updateSendButton();
  });
  textarea.addEventListener('keyup', updateSendButton);
  textarea.addEventListener('change', updateSendButton);
  textarea.addEventListener('paste', () => {
    setTimeout(() => {
      adjustTextareaHeight();
      updateSendButton();
    }, 50);
  });

  // Enter để gửi tin nhắn
  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener('click', () => sendMessage());

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

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
          htmlLines.push('<blockquote>');
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
          htmlLines.push('<ul>');
        }
        line = listMatch[1];
        line = `<li>${parseInlineMarkdown(line)}</li>`;
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
        htmlLines.push(`<h3>${parseInlineMarkdown(line.substring(4))}</h3>`);
      } else if (line.startsWith('## ')) {
        htmlLines.push(`<h2>${parseInlineMarkdown(line.substring(3))}</h2>`);
      } else if (line.startsWith('# ')) {
        htmlLines.push(`<h1>${parseInlineMarkdown(line.substring(2))}</h1>`);
      } else if (line === '') {
        if (!inQuote) {
          htmlLines.push('<br>');
        }
      } else {
        // Normal paragraph
        let parsed = parseInlineMarkdown(line);
        htmlLines.push(`<p>${parsed}</p>`);
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

  async function sendMessage(overrideText = null) {
    const text = overrideText !== null ? overrideText : textarea.value.trim();
    if (!text) return;

    // Engine nội bộ

    if (overrideText === null) {
      textarea.value = '';
      textarea.style.height = '46px';
      sendBtn.disabled = true;
    }

    // Append user message
    const userMsgHtml = `
      <div class="assistant-msg user">
        <div class="msg-avatar">👤</div>
        <div class="msg-content"><p>${parseInlineMarkdown(text).replace(/\n/g, '<br>')}</p></div>
      </div>`;
    chatMessages.insertAdjacentHTML('beforeend', userMsgHtml);
    scrollToBottom();

    // Append typing spinner
    const typingId = 'typing-' + Date.now();
    const typingHtml = `
      <div id="${typingId}" class="assistant-msg bot typing">
        <div class="msg-avatar" style="background: linear-gradient(135deg, rgba(78, 124, 255, 0.25), rgba(0, 212, 255, 0.2)); border: 1px solid rgba(0, 212, 255, 0.35);">🤖</div>
        <div class="msg-content">
          <div class="chat-typing"><span></span><span></span><span></span></div>
        </div>
      </div>`;
    chatMessages.insertAdjacentHTML('beforeend', typingHtml);
    scrollToBottom();

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: conversationHistory
        })
      });

      const data = await res.json();

      // Remove typing element
      const typingEl = document.getElementById(typingId);
      if (typingEl) typingEl.remove();

      if (!res.ok) {
        throw new Error(data.error || 'Lỗi không xác định');
      }

      // Append bot response
      const botReply = data.reply;
      const botMsgHtml = `
        <div class="assistant-msg bot">
          <div class="msg-avatar" style="background: linear-gradient(135deg, rgba(78, 124, 255, 0.25), rgba(0, 212, 255, 0.2)); border: 1px solid rgba(0, 212, 255, 0.35);">🤖</div>
          <div class="msg-content">${renderMarkdown(botReply)}</div>
        </div>`;
      chatMessages.insertAdjacentHTML('beforeend', botMsgHtml);

      // Track history
      conversationHistory.push({ role: 'user', content: text });
      conversationHistory.push({ role: 'assistant', content: botReply });
      if (conversationHistory.length > 30) {
        conversationHistory = conversationHistory.slice(conversationHistory.length - 30);
      }

    } catch (err) {
      const typingEl = document.getElementById(typingId);
      if (typingEl) typingEl.remove();

      const errorHtml = `
        <div class="assistant-msg bot">
          <div class="msg-avatar">🤖</div>
          <div class="msg-content" style="border: 1px solid var(--danger-border); background: var(--danger-bg);">
            <p>⚠️ <strong>Lỗi kết nối hoặc xử lý:</strong> ${err.message}</p>
          </div>
        </div>`;
      chatMessages.insertAdjacentHTML('beforeend', errorHtml);

      // Engine nội bộ
    } finally {
      scrollToBottom();
    }
  }

  // Quick templates sender
  window.sendTemplateQuery = function(type) {
    const templates = {
      guide_analyze: "Hướng dẫn tôi cách kiểm chứng, phân tích một bài viết bằng TrustCheck?",
      explain_score: "Điểm tin cậy được tính như thế nào và có ý nghĩa gì?",
      explain_result: "Giải thích kết quả phân loại Reliable và Unreliable?",
      url_help: "Cách phân tích một bài viết qua đường dẫn URL như thế nào?",
      ocr_help: "Hướng dẫn cách trích xuất văn bản từ hình ảnh (OCR) để phân tích?",
      dashboard_help: "Trang Dashboard thống kê những số liệu gì?",
      history_help: "Làm thế nào để xem lại lịch sử các bài viết đã phân tích?",
      fact_check_tips: "Cho tôi một số mẹo và lời khuyên tự kiểm chứng nhanh nguồn tin?"
    };
    
    const query = templates[type];
    if (query) {
      sendMessage(query);
    }
  };
});
