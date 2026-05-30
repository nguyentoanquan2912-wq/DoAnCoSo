/* ═══════════════════════════════════
   CHAT WIDGET LOGIC
═══════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    const chatWidget = document.getElementById('chat-widget');
    const toggleBtn = document.getElementById('chat-toggle-btn');
    const chatMessages = document.getElementById('chat-messages');
    const textarea = document.getElementById('chat-textarea');
    const sendBtn = document.getElementById('chat-send-btn');
  
    // Biến lưu trữ lịch sử chat để gửi cho API
    let conversationHistory = [];
  
    // ─── Helper Functions ───────────────────
    function getTimeString() {
      const now = new Date();
      return now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
    }

    function escapeHtml(text) {
      return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    // ─── Markdown Renderer ──────────────────
    function parseInlineMarkdown(text) {
      // Escape HTML tags to prevent XSS
      let html = escapeHtml(text);
      // Bold
      html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      // Italic
      html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
      // Inline code
      html = html.replace(/`(.*?)`/g, '<code>$1</code>');
      return html;
    }

    function renderMarkdown(text) {
      if (!text) return '';
      const lines = text.split('\n');
      let inList = false;
      let inOrderedList = false;
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

        // Handle Numbered lists (1. item, 2. item, etc.)
        const numberedMatch = line.match(/^\d+\.\s+(.*)$/);
        if (numberedMatch) {
          if (inList) { inList = false; htmlLines.push('</ul>'); }
          if (!inOrderedList) {
            inOrderedList = true;
            htmlLines.push('<ol>');
          }
          htmlLines.push(`<li>${parseInlineMarkdown(numberedMatch[1])}</li>`);
          continue;
        } else {
          if (inOrderedList) {
            inOrderedList = false;
            htmlLines.push('</ol>');
          }
        }

        // Handle Bullet lists
        const listMatch = line.match(/^[\-\*]\s+(.*)$/);
        if (listMatch) {
          if (!inList) {
            inList = true;
            htmlLines.push('<ul>');
          }
          htmlLines.push(`<li>${parseInlineMarkdown(listMatch[1])}</li>`);
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
          htmlLines.push(`<p>${parseInlineMarkdown(line)}</p>`);
        }
      }

      if (inList) htmlLines.push('</ul>');
      if (inOrderedList) htmlLines.push('</ol>');
      if (inQuote) htmlLines.push('</blockquote>');

      return htmlLines.join('\n');
    }

    // ─── Copy Message ───────────────────────
    window.copyMsg = function(btn) {
      const msgEl = btn.closest('.chat-msg-row').querySelector('.chat-msg');
      if (!msgEl) return;
      navigator.clipboard.writeText(msgEl.textContent).then(() => {
        btn.textContent = '✅';
        setTimeout(() => btn.textContent = '📋', 2000);
      });
    };

    // ─── Toggle Widget ──────────────────────
    toggleBtn.addEventListener('click', () => {
      chatWidget.classList.toggle('is-open');
      if (chatWidget.classList.contains('is-open')) {
        textarea.focus();
      }
    });
  
    // Engine AI nội bộ - không cần cấu hình API Key

    // ─── Clear History Button ───────────────
    const clearBtn = document.getElementById('chat-clear-btn');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        conversationHistory = [];
        chatMessages.innerHTML = `
          <div class="chat-msg-row bot">
            <div class="chat-msg-avatar">🤖</div>
            <div>
              <div class="chat-msg bot-msg">Lịch sử hội thoại đã được xoá. Hãy bắt đầu cuộc trò chuyện mới!</div>
            </div>
          </div>`;
        showToast('Đã xoá lịch sử hội thoại!', 'success');
      });
    }

    // ─── Send Button State ──────────────────
    function updateSendButton() {
      sendBtn.disabled = !textarea.value.trim();
    }

    // Tự động resize textarea của widget
    function adjustTextareaHeight() {
      textarea.style.height = '44px'; // Reset height
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
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
  
    // Gửi bằng phím Enter (không kèm Shift)
    textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  
    sendBtn.addEventListener('click', sendMessage);
  
    // Cuộn xuống cuối
    function scrollToBottom() {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  
    // ─── Send Message ───────────────────────
    async function sendMessage() {
      const text = textarea.value.trim();
      if (!text) return;
  
      // Xóa textarea và reset height
      textarea.value = '';
      textarea.style.height = '44px';
      sendBtn.disabled = true;
  
      // In ra khung chat (User) — với avatar
      const userMsgHtml = `
        <div class="chat-msg-row user">
          <div class="chat-msg-avatar">👤</div>
          <div>
            <div class="chat-msg user-msg">${escapeHtml(text).replace(/\n/g, '<br>')}</div>
            <div class="chat-msg-meta"><span>${getTimeString()}</span></div>
          </div>
        </div>`;
      chatMessages.insertAdjacentHTML('beforeend', userMsgHtml);
      scrollToBottom();
  
      // Thêm indicator typing
      const typingId = 'typing-' + Date.now();
      const typingHtml = `
        <div id="${typingId}" class="chat-msg-row bot">
          <div class="chat-msg-avatar" style="background: linear-gradient(135deg, rgba(78, 124, 255, 0.25), rgba(0, 212, 255, 0.2)); border: 1px solid rgba(0, 212, 255, 0.35);">🤖</div>
          <div>
            <div class="chat-typing"><span></span><span></span><span></span></div>
          </div>
        </div>`;
      chatMessages.insertAdjacentHTML('beforeend', typingHtml);
      scrollToBottom();

      try {
        // Gọi API Backend (engine nội bộ)
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            history: conversationHistory
          })
        });
  
        const data = await res.json();
  
        // Xóa typing
        const typingEl = document.getElementById(typingId);
        if (typingEl) typingEl.remove();
  
        if (!res.ok) {
          throw new Error(data.error || 'Lỗi không xác định');
        }
  
        // Cập nhật giao diện — Bot message với avatar
        const botReply = data.reply;
        const botMsgHtml = `
          <div class="chat-msg-row bot">
            <div class="chat-msg-avatar" style="background: linear-gradient(135deg, rgba(78, 124, 255, 0.25), rgba(0, 212, 255, 0.2)); border: 1px solid rgba(0, 212, 255, 0.35);">🤖</div>
            <div>
              <div class="chat-msg bot-msg">${renderMarkdown(botReply)}</div>
              <div class="chat-msg-meta">
                <span>${getTimeString()}</span>
                <button class="chat-msg-copy" onclick="copyMsg(this)" title="Sao chép">📋</button>
              </div>
            </div>
          </div>`;
        chatMessages.insertAdjacentHTML('beforeend', botMsgHtml);
        
        // Thêm vào lịch sử (tối đa giữ 10 lượt hội thoại gần nhất để tránh tốn token)
        conversationHistory.push({ role: 'user', content: text });
        conversationHistory.push({ role: 'assistant', content: botReply });
        
        if (conversationHistory.length > 20) {
          conversationHistory = conversationHistory.slice(conversationHistory.length - 20);
        }
  
      } catch (err) {
        // Xóa typing nếu có lỗi
        const typingEl = document.getElementById(typingId);
        if (typingEl) typingEl.remove();
        
        const errorHtml = `
          <div class="chat-msg-row bot">
            <div class="chat-msg-avatar" style="background: linear-gradient(135deg, rgba(78, 124, 255, 0.25), rgba(0, 212, 255, 0.2)); border: 1px solid rgba(0, 212, 255, 0.35);">🤖</div>
            <div>
              <div class="chat-msg bot-msg" style="border:1px solid var(--danger-border);background:var(--danger-bg);">
                ⚠️ <strong>Lỗi:</strong> ${escapeHtml(err.message)}
              </div>
            </div>
          </div>`;
        chatMessages.insertAdjacentHTML('beforeend', errorHtml);
        
        // Engine nội bộ
      } finally {
        scrollToBottom();
        // Khôi phục trạng thái nút gửi dựa theo nội dung textarea
        sendBtn.disabled = !textarea.value.trim();
      }
    }
  });
