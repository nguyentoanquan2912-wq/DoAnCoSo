/* ═══════════════════════════════════
   CHAT WIDGET LOGIC
═══════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    const chatWidget = document.getElementById('chat-widget');
    const toggleBtn = document.getElementById('chat-toggle-btn');
    const settingsBtn = document.getElementById('chat-btn-settings');
    const keyPanel = document.getElementById('chat-key-panel');
    const saveKeyBtn = document.getElementById('save-key-btn');
    const keyInput = document.getElementById('gemini-api-key');
    const chatMessages = document.getElementById('chat-messages');
    const textarea = document.getElementById('chat-textarea');
    const sendBtn = document.getElementById('chat-send-btn');
  
    // Biến lưu trữ lịch sử chat để gửi cho API
    // Format: [{role: "user", content: "..."}, {role: "assistant", content: "..."}]
    let conversationHistory = [];
  
    // 1. Lấy API key từ LocalStorage (không hardcode key vào code)
    let apiKey = localStorage.getItem('trustcheck_gemini_key') || '';
    if (apiKey) {
      keyInput.value = apiKey;
    }
  
    // Xử lý bật/tắt widget
    toggleBtn.addEventListener('click', () => {
      chatWidget.classList.toggle('is-open');
      // Nếu mở lên mà chưa có key, hiện panel cài đặt
      if (chatWidget.classList.contains('is-open')) {
        if (!apiKey) {
          keyPanel.style.display = 'block';
        } else {
          textarea.focus();
        }
      }
    });
  
    // Nút bánh răng cài đặt
    settingsBtn.addEventListener('click', () => {
      keyPanel.style.display = keyPanel.style.display === 'none' ? 'block' : 'none';
    });
  
    // Lưu key
    saveKeyBtn.addEventListener('click', () => {
      const val = keyInput.value.trim();
      if (!val) {
        showToast('Vui lòng nhập API Key', 'warning');
        return;
      }
      apiKey = val;
      localStorage.setItem('trustcheck_gemini_key', apiKey);
      keyPanel.style.display = 'none';
      showToast('Đã lưu API Key!', 'success');
      textarea.focus();
    });
  
    // Tự động resize textarea
    textarea.addEventListener('input', function() {
      this.style.height = '44px'; // Reset height
      this.style.height = Math.min(this.scrollHeight, 120) + 'px';
      
      // Bật tắt nút gửi
      sendBtn.disabled = !this.value.trim();
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
  
    // Format text thành HTML đơn giản (xuống dòng và in đậm)
    function formatMessage(text) {
      return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
    }
  
    async function sendMessage() {
      const text = textarea.value.trim();
      if (!text) return;
  
      if (!apiKey) {
        showToast('Vui lòng cấu hình Google Gemini API Key trước!', 'warning');
        keyPanel.style.display = 'block';
        return;
      }
  
      // Xóa textarea và reset height
      textarea.value = '';
      textarea.style.height = '44px';
      sendBtn.disabled = true;
  
      // In ra khung chat (User)
      const userMsgHtml = `<div class="chat-msg user-msg">${formatMessage(text)}</div>`;
      chatMessages.insertAdjacentHTML('beforeend', userMsgHtml);
      scrollToBottom();
  
      // Thêm indicator typing
      const typingId = 'typing-' + Date.now();
      const typingHtml = `<div id="${typingId}" class="chat-typing"><span></span><span></span><span></span></div>`;
      chatMessages.insertAdjacentHTML('beforeend', typingHtml);
      scrollToBottom();
  
      try {
        // Gọi API Backend
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            api_key: apiKey,
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
  
        // Cập nhật giao diện
        const botReply = data.reply;
        const botMsgHtml = `<div class="chat-msg bot-msg">${formatMessage(botReply)}</div>`;
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
          <div class="chat-msg bot-msg" style="border:1px solid var(--danger-border);background:var(--danger-bg);">
            ⚠️ <strong>Lỗi:</strong> ${err.message}
          </div>`;
        chatMessages.insertAdjacentHTML('beforeend', errorHtml);
        
        // Nếu lỗi do key (thường trả về 401 hoặc text auth), ép nhập lại key
        if(err.message.toLowerCase().includes('khóa api') || err.message.toLowerCase().includes('key')) {
           keyPanel.style.display = 'block';
        }
      } finally {
        scrollToBottom();
      }
    }
  });
