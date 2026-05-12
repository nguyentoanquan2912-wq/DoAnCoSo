/* ═══════════════════════════════════
   DASHBOARD PAGE LOGIC
═══════════════════════════════════ */

let metricsData = null;
let activeModel = 'lr';
let barChart = null;

const MODEL_LABELS = { lr: 'Logistic Regression', nb: 'Naive Bayes', svm: 'Linear SVM' };
const MODEL_COLORS = {
  lr: { fill: 'rgba(78,124,255,0.8)', stroke: '#4e7cff' },
  nb: { fill: 'rgba(0,212,255,0.8)', stroke: '#00d4ff' },
  svm: { fill: 'rgba(16,185,129,0.8)', stroke: '#10b981' }
};

/* ─── Load metrics ─────────────── */
async function loadMetrics() {
  showLoading('Đang tải dữ liệu...');
  try {
    const res = await fetch('/api/models');
    if (!res.ok) throw new Error(await res.text());
    metricsData = await res.json();
    renderAll();
    showToast('Dữ liệu đã được tải!', 'success', 2000);
  } catch (err) {
    document.getElementById('dashboard-content').innerHTML = `
      <div style="text-align:center;padding:80px 24px;">
        <div style="font-size:52px;margin-bottom:16px;">🤖</div>
        <div style="font-size:20px;font-weight:700;color:var(--text-primary);margin-bottom:10px;">Chưa tìm thấy dữ liệu</div>
        <div style="font-size:15px;color:var(--text-secondary);margin-bottom:24px;">
          Vui lòng huấn luyện mô hình trước bằng lệnh:
        </div>
        <code style="display:inline-block;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);padding:12px 24px;border-radius:12px;font-size:15px;color:var(--primary-light);">
          python -m src.train
        </code>
      </div>`;
  } finally {
    hideLoading();
  }
}

/* ─── Render all sections ──────── */
function renderAll() {
  renderSummaryCards();
  renderBarChart();
  renderConfusionMatrix(activeModel);
  renderDatasetStats();
}

/* ─── Summary metric cards ─────── */
function renderSummaryCards() {
  const keys = ['lr', 'nb', 'svm'];
  const metricNames = ['accuracy', 'precision', 'recall', 'f1'];
  const metricLabels = ['Accuracy', 'Precision', 'Recall', 'F1-Score'];
  const metricIcons = ['🎯', '🔍', '📡', '⚖️'];

  // Best metrics across all models
  const best = {};
  metricNames.forEach(m => {
    best[m] = Math.max(...keys.map(k => metricsData[k]?.[m] || 0));
  });

  const grid = document.getElementById('metrics-grid');
  if (!grid) return;

  grid.innerHTML = keys.map(key => {
    const d = metricsData[key] || {};
    const color = MODEL_COLORS[key];
    return `
      <div class="chart-card" style="border-color:${color.stroke}30;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
          <div style="width:42px;height:42px;background:${color.fill.replace('0.8','0.15')};border:1px solid ${color.stroke}50;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;">🤖</div>
          <div>
            <div style="font-size:16px;font-weight:700;color:var(--text-white);">${d.model_name || MODEL_LABELS[key]}</div>
            <div style="font-size:12px;color:var(--text-muted);">Mô hình phân loại</div>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          ${metricNames.map((m, i) => `
            <div style="background:rgba(255,255,255,0.04);border-radius:12px;padding:14px;text-align:center;">
              <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">${metricLabels[i]}</div>
              <div style="font-size:22px;font-weight:800;color:${d[m] >= 80 ? 'var(--success-light)' : d[m] >= 60 ? 'var(--primary-light)' : 'var(--danger-light)'};">
                ${d[m] !== undefined ? d[m] : '—'}<span style="font-size:12px;">%</span>
              </div>
            </div>`).join('')}
        </div>
      </div>`;
  }).join('');
}

/* ─── Bar chart (vanilla canvas) ─ */
function renderBarChart() {
  const canvas = document.getElementById('bar-chart');
  if (!canvas) return;

  if (barChart) { barChart = null; }

  const keys = ['lr', 'nb', 'svm'];
  const metrics = ['accuracy', 'precision', 'recall', 'f1'];
  const metricLabels = ['Accuracy', 'Precision', 'Recall', 'F1'];

  const data = keys.map(k => metrics.map(m => metricsData[k]?.[m] || 0));
  const colors = keys.map(k => MODEL_COLORS[k].stroke);
  const labels = keys.map(k => MODEL_LABELS[k]);

  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = 320 * dpr;
  ctx.scale(dpr, dpr);

  const W = rect.width;
  const H = 320;
  const padLeft = 44, padRight = 20, padTop = 20, padBottom = 60;
  const chartW = W - padLeft - padRight;
  const chartH = H - padTop - padBottom;

  // Background
  ctx.fillStyle = 'transparent';
  ctx.fillRect(0, 0, W, H);

  // Grid lines
  ctx.strokeStyle = 'rgba(255,255,255,0.06)';
  ctx.lineWidth = 1;
  const steps = 5;
  for (let i = 0; i <= steps; i++) {
    const y = padTop + (chartH / steps) * i;
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(W - padRight, y);
    ctx.stroke();
    ctx.fillStyle = 'rgba(148,163,184,0.7)';
    ctx.font = '11px Inter, sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(`${100 - i * 20}%`, padLeft - 6, y + 4);
  }

  // Grouped bars
  const groupW = chartW / metrics.length;
  const barW = groupW * 0.2;
  const gap = groupW * 0.05;

  metrics.forEach((_, mi) => {
    const gx = padLeft + mi * groupW + groupW / 2 - (keys.length * (barW + gap)) / 2;

    keys.forEach((key, ki) => {
      const val = data[ki][mi];
      const bh = (val / 100) * chartH;
      const x = gx + ki * (barW + gap);
      const y = padTop + chartH - bh;

      // Bar with gradient
      const grad = ctx.createLinearGradient(0, y, 0, padTop + chartH);
      grad.addColorStop(0, colors[ki]);
      grad.addColorStop(1, colors[ki] + '44');
      ctx.fillStyle = grad;
      ctx.beginPath();
      const r = 5;
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + barW - r, y);
      ctx.arcTo(x + barW, y, x + barW, y + r, r);
      ctx.lineTo(x + barW, padTop + chartH);
      ctx.lineTo(x, padTop + chartH);
      ctx.arcTo(x, y, x + r, y, r);
      ctx.closePath();
      ctx.fill();

      // Value label
      ctx.fillStyle = 'rgba(226,232,240,0.9)';
      ctx.font = `bold 9px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText(`${val}`, x + barW / 2, y - 4);
    });

    // Metric label
    ctx.fillStyle = 'rgba(148,163,184,0.9)';
    ctx.font = '12px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(metricLabels[mi], padLeft + mi * groupW + groupW / 2, H - 36);
  });

  // Legend
  const legY = H - 16;
  const totalLegW = keys.length * 120;
  const legStartX = (W - totalLegW) / 2;
  keys.forEach((key, i) => {
    const lx = legStartX + i * 120;
    ctx.fillStyle = colors[i];
    ctx.fillRect(lx, legY - 8, 14, 10);
    ctx.fillStyle = 'rgba(148,163,184,0.9)';
    ctx.font = '11px Inter, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(MODEL_LABELS[key], lx + 18, legY);
  });
}

/* ─── Confusion matrix ─────────── */
function renderConfusionMatrix(modelKey) {
  const d = metricsData?.[modelKey];
  if (!d) return;

  const classes = d.classes || ['reliable', 'unreliable'];
  const cm = d.confusion_matrix || [[0, 0], [0, 0]];
  const labelMap = { reliable: 'Tin thật', unreliable: 'Tin giả' };

  const container = document.getElementById('cm-container');
  if (!container) return;

  const rows = classes.map((actual, i) =>
    `<tr>
      <td style="font-weight:700;color:var(--text-primary);white-space:nowrap;">${labelMap[actual] || actual}</td>
      ${classes.map((_, j) => {
        const val = cm[i]?.[j] ?? 0;
        const isMain = i === j;
        return `<td class="${isMain ? 'cm-cell-high' : 'cm-cell-low'}">${val}</td>`;
      }).join('')}
    </tr>`
  ).join('');

  container.innerHTML = `
    <table class="cm-table">
      <thead>
        <tr>
          <th>Thực tế \\ Dự đoán</th>
          ${classes.map(c => `<th>${labelMap[c] || c}</th>`).join('')}
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;

  // Update active tab style
  document.querySelectorAll('.model-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.model === modelKey);
  });
}

/* ─── Dataset stats ────────────── */
function renderDatasetStats() {
  const ds = metricsData?.dataset;
  if (!ds) return;

  const container = document.getElementById('dataset-stats');
  if (!container) return;

  const reliablePct = ds.total ? ((ds.reliable / ds.total) * 100).toFixed(1) : 0;
  const unreliablePct = ds.total ? ((ds.unreliable / ds.total) * 100).toFixed(1) : 0;

  container.innerHTML = `
    <div class="ds-item">
      <div class="ds-value">${ds.total}</div>
      <div class="ds-label">Tổng mẫu</div>
    </div>
    <div class="ds-item">
      <div class="ds-value" style="color:var(--success-light);">${ds.reliable}</div>
      <div class="ds-label">Tin đáng tin cậy</div>
    </div>
    <div class="ds-item">
      <div class="ds-value" style="color:var(--danger-light);">${ds.unreliable}</div>
      <div class="ds-label">Tin không đáng tin cậy</div>
    </div>
    <div class="ds-item">
      <div class="ds-value">${ds.train_size}</div>
      <div class="ds-label">Tập huấn luyện</div>
    </div>
    <div class="ds-item">
      <div class="ds-value">${ds.test_size}</div>
      <div class="ds-label">Tập kiểm tra</div>
    </div>
    <div class="ds-item">
      <div class="ds-value">${reliablePct}%</div>
      <div class="ds-label">Tỷ lệ tin thật</div>
    </div>`;
}

/* ─── Tab switching ────────────── */
document.querySelectorAll('.model-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    activeModel = tab.dataset.model;
    renderConfusionMatrix(activeModel);
  });
});

/* ─── Resize chart ─────────────── */
let resizeTimeout;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(renderBarChart, 300);
});

/* ─── Init ─────────────────────── */
loadMetrics();
