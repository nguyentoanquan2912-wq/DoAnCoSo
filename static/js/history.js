/* ═══════════════════════════════════
   HISTORY PAGE LOGIC
═══════════════════════════════════ */

let allHistory = [];
let filtered = [];
let currentPage = 1;
const PAGE_SIZE = 10;
let activeFilter = 'all';
let searchQuery = '';

const MODEL_NAMES = { lr: 'Logistic Regression', nb: 'Naive Bayes', svm: 'Linear SVM', ensemble: 'Mô hình Đồng thuận', all: 'Tất cả' };

/* ─── Load history ─────────────── */
async function loadHistory() {
  showLoading('Đang tải lịch sử...');
  try {
    const res = await fetch('/api/history');
    allHistory = await res.json();
    applyFilters();
    renderSummaryStats();
  } catch (err) {
    showToast('Không thể tải lịch sử.', 'error');
  } finally {
    hideLoading();
  }
}

/* ─── Filter & search ──────────── */
function applyFilters() {
  filtered = allHistory.filter(item => {
    const matchFilter =
      activeFilter === 'all' ||
      (activeFilter === 'real' && item.primary_label === 'reliable') ||
      (activeFilter === 'fake' && item.primary_label === 'unreliable');

    const q = searchQuery.toLowerCase();
    const matchSearch =
      !q ||
      (item.title || '').toLowerCase().includes(q) ||
      (item.content_preview || '').toLowerCase().includes(q);

    return matchFilter && matchSearch;
  });

  currentPage = 1;
  renderTable();
  renderPagination();
}

/* ─── Render table ─────────────── */
function renderTable() {
  const body = document.getElementById('history-tbody');
  const start = (currentPage - 1) * PAGE_SIZE;
  const pageData = filtered.slice(start, start + PAGE_SIZE);

  if (filtered.length === 0) {
    body.innerHTML = '';
    document.getElementById('empty-state').style.display = 'block';
    document.getElementById('history-table-wrap').style.display = 'none';
    return;
  }

  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('history-table-wrap').style.display = 'block';

  body.innerHTML = pageData.map(item => {
    const isReal = item.primary_label === 'reliable';
    const cls = isReal ? 'real' : 'fake';
    const modelDisplay = MODEL_NAMES[item.model_used] || item.model_used || '—';

    return `
      <tr>
        <td style="color:var(--text-muted);font-size:12px;">${formatDate(item.created_at)}</td>
        <td class="history-title-cell" title="${escapeHtml(item.title || '')}">
          ${escapeHtml(item.title || '(Không có tiêu đề)')}
        </td>
        <td><span class="badge ${cls}">${isReal ? '✅ Tin thật' : '⚠️ Tin giả'}</span></td>
        <td><strong style="color:var(--text-white);">${item.primary_probability}%</strong></td>
        <td style="font-size:13px;color:var(--text-muted);">${modelDisplay}</td>
        <td>
          <button class="delete-btn" onclick="deleteItem('${item.id}')" title="Xoá mục này">🗑️</button>
        </td>
      </tr>`;
  }).join('');

  // Counter
  const counter = document.getElementById('result-counter');
  if (counter) {
    counter.textContent = `Hiển thị ${start + 1}–${Math.min(start + PAGE_SIZE, filtered.length)} / ${filtered.length} kết quả`;
  }
}

/* ─── Pagination ───────────────── */
function renderPagination() {
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const container = document.getElementById('pagination');
  if (!container) return;
  if (totalPages <= 1) { container.innerHTML = ''; return; }

  let html = `
    <button class="page-btn" onclick="goPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>‹</button>`;

  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || Math.abs(i - currentPage) <= 1) {
      html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="goPage(${i})">${i}</button>`;
    } else if (Math.abs(i - currentPage) === 2) {
      html += `<span style="color:var(--text-muted);padding:0 4px;">…</span>`;
    }
  }

  html += `<button class="page-btn" onclick="goPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>›</button>`;
  container.innerHTML = html;
}

function goPage(page) {
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  if (page < 1 || page > totalPages) return;
  currentPage = page;
  renderTable();
  renderPagination();
  window.scrollTo({ top: 200, behavior: 'smooth' });
}

/* ─── Delete ───────────────────── */
async function deleteItem(id) {
  if (!confirm('Bạn có chắc muốn xoá mục này?')) return;
  try {
    const res = await fetch(`/api/history/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Xoá thất bại');
    allHistory = allHistory.filter(h => h.id !== id);
    applyFilters();
    renderSummaryStats();
    showToast('Đã xoá thành công.', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function clearAllHistory() {
  if (!confirm('Bạn có chắc muốn xoá TOÀN BỘ lịch sử?')) return;
  try {
    const res = await fetch('/api/history/clear', { method: 'DELETE' });
    if (!res.ok) throw new Error();
    allHistory = [];
    applyFilters();
    renderSummaryStats();
    showToast('Đã xoá toàn bộ lịch sử.', 'success');
  } catch {
    showToast('Xoá thất bại.', 'error');
  }
}

/* ─── Summary stats ────────────── */
function renderSummaryStats() {
  const total = allHistory.length;
  const real = allHistory.filter(h => h.primary_label === 'reliable').length;
  const fake = allHistory.filter(h => h.primary_label === 'unreliable').length;

  const elTotal = document.getElementById('stat-total');
  const elReal = document.getElementById('stat-real');
  const elFake = document.getElementById('stat-fake');

  if (elTotal) elTotal.textContent = total;
  if (elReal) elReal.textContent = real;
  if (elFake) elFake.textContent = fake;
}

/* ─── Filter buttons ───────────── */
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    activeFilter = btn.dataset.filter;
    document.querySelectorAll('.filter-btn').forEach(b => {
      b.className = 'filter-btn';
    });
    btn.classList.add('active-' + activeFilter);
    applyFilters();
  });
});

/* ─── Search ───────────────────── */
const searchInput = document.getElementById('search-input');
if (searchInput) {
  searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value;
    applyFilters();
  });
}

/* ─── Escape HTML ──────────────── */
function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* ─── Expose globals ───────────── */
window.deleteItem = deleteItem;
window.clearAllHistory = clearAllHistory;
window.goPage = goPage;

/* ─── Init ─────────────────────── */
loadHistory();
