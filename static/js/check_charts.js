/* ═══════════════════════════════════
   CHECK PAGE — ANALYSIS CHARTS
   Single Model (Linear SVM) Edition
   Uses Chart.js 4.x
   Includes: Gauge, Features Bar, Radar, Signs Pie
   ═══════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  const dataEl = document.getElementById('chart-data');
  if (!dataEl) return;

  let chartData;
  try {
    chartData = JSON.parse(dataEl.textContent);
  } catch (e) {
    console.error('Cannot parse chart data:', e);
    return;
  }

  const svmResult = chartData.svm_result;
  const topFeatures = chartData.top_features || [];
  const scoring = chartData.scoring;
  const signs = chartData.signs || [];

  // Color palette
  const colors = {
    reliable: 'rgba(16, 185, 129, 0.85)',
    unreliable: 'rgba(239, 68, 68, 0.85)',
    reliableBg: 'rgba(16, 185, 129, 0.15)',
    unreliableBg: 'rgba(239, 68, 68, 0.15)',
    positive: 'rgba(16, 185, 129, 0.8)',
    negative: 'rgba(239, 68, 68, 0.8)',
    positiveBg: 'rgba(16, 185, 129, 0.15)',
    negativeBg: 'rgba(239, 68, 68, 0.15)',
    primary: 'rgba(78, 124, 255, 0.8)',
    primaryBg: 'rgba(78, 124, 255, 0.15)',
    cyan: 'rgba(0, 212, 255, 0.8)',
    cyanBg: 'rgba(0, 212, 255, 0.15)',
    amber: 'rgba(245, 158, 11, 0.8)',
    amberBg: 'rgba(245, 158, 11, 0.15)',
    purple: 'rgba(168, 85, 247, 0.8)',
    purpleBg: 'rgba(168, 85, 247, 0.15)',
    grid: 'rgba(255, 255, 255, 0.08)',
    text: 'rgba(255, 255, 255, 0.7)',
    textMuted: 'rgba(255, 255, 255, 0.4)',
    empty: 'rgba(255, 255, 255, 0.06)',
  };

  // Chart.js global defaults for dark theme
  Chart.defaults.color = colors.text;
  Chart.defaults.borderColor = colors.grid;
  Chart.defaults.font.family = 'Inter, sans-serif';

  const isReliable = svmResult.label === 'reliable';
  const mainColor = isReliable ? colors.reliable : colors.unreliable;

  // ─── 1. GAUGE CHART (Half Doughnut) ──────────────────────────────
  const gaugeCtx = document.getElementById('gauge-chart');
  if (gaugeCtx) {
    const prob = svmResult.probability;
    const remaining = 100 - prob;

    new Chart(gaugeCtx, {
      type: 'doughnut',
      data: {
        labels: ['Xác suất dự đoán', 'Còn lại'],
        datasets: [{
          data: [prob, remaining],
          backgroundColor: [mainColor, colors.empty],
          borderColor: [mainColor, 'transparent'],
          borderWidth: [2, 0],
          hoverOffset: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        rotation: -90,
        circumference: 180,
        cutout: '72%',
        plugins: {
          legend: { display: false },
          tooltip: {
            filter: (item) => item.dataIndex === 0,
            callbacks: {
              label: (ctx) => {
                const lbl = isReliable ? '✅ Tin đáng tin cậy' : '⚠️ Tin không đáng tin cậy';
                return `${ctx.raw}% — ${lbl}`;
              }
            }
          }
        }
      },
      plugins: [{
        id: 'gaugeCenter',
        afterDraw(chart) {
          const { ctx: c } = chart;
          c.save();
          const centerX = (chart.chartArea.left + chart.chartArea.right) / 2;
          const centerY = chart.chartArea.bottom - 10;

          // Main percentage
          c.font = 'bold 36px Inter, sans-serif';
          c.fillStyle = mainColor;
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText(`${prob}%`, centerX, centerY - 28);

          // Label
          c.font = '13px Inter, sans-serif';
          c.fillStyle = colors.text;
          const labelText = isReliable ? 'Tin đáng tin cậy' : 'Tin không đáng tin cậy';
          c.fillText(labelText, centerX, centerY + 2);

          // Model name
          c.font = '11px Inter, sans-serif';
          c.fillStyle = colors.textMuted;
          c.fillText('Linear SVM', centerX, centerY + 22);

          c.restore();
        }
      }]
    });
  }

  // ─── 2. TOP FEATURES BAR CHART ───────────────────────────────────
  const featCtx = document.getElementById('features-bar-chart');
  if (featCtx && topFeatures.length > 0) {
    const featLabels = topFeatures.map(f => f.word);
    const featValues = topFeatures.map(f => Math.abs(f.weight));
    const featColors = topFeatures.map(f =>
      f.influence === 'positive' ? colors.positive : colors.negative
    );

    new Chart(featCtx, {
      type: 'bar',
      data: {
        labels: featLabels,
        datasets: [{
          label: 'Mức ảnh hưởng (|weight|)',
          data: featValues,
          backgroundColor: featColors,
          borderColor: featColors,
          borderWidth: 1,
          borderRadius: 4,
          borderSkipped: false,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const feat = topFeatures[ctx.dataIndex];
                const dir = feat.influence === 'positive' ? '📗 Tin thật' : '📕 Tin giả';
                return `${feat.word}: ${feat.weight.toFixed(4)} → ${dir}`;
              }
            }
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: { color: colors.grid },
            ticks: { color: colors.text, font: { size: 10 } },
            title: {
              display: true,
              text: 'Mức ảnh hưởng (|trọng số TF-IDF × hệ số SVM|)',
              color: colors.textMuted,
              font: { size: 11 }
            }
          },
          y: {
            grid: { display: false },
            ticks: { color: colors.text, font: { size: 11, weight: '500' } }
          }
        }
      }
    });
  } else if (featCtx) {
    const c = featCtx.getContext('2d');
    c.font = '14px Inter, sans-serif';
    c.fillStyle = colors.textMuted;
    c.textAlign = 'center';
    c.fillText('Không có dữ liệu đặc trưng', featCtx.width / 2, featCtx.height / 2);
  }

  // ─── 3. RADAR CHART — Multi-dimensional Analysis ─────────────────
  const radarCtx = document.getElementById('radar-chart');
  if (radarCtx) {
    const prob = svmResult.probability;
    const relScore = scoring.reliability_score || 0;
    const confLevel = scoring.confidence_level || 'thấp';

    // Tính các chỉ số cho radar (trên thang 100)
    const confScore = confLevel === 'cao' ? 95 : confLevel === 'trung bình' ? 65 : 35;

    // Tính điểm từ features
    const positiveFeats = topFeatures.filter(f => f.influence === 'positive').length;
    const negativeFeats = topFeatures.filter(f => f.influence === 'negative').length;
    const totalFeats = Math.max(positiveFeats + negativeFeats, 1);
    const featScore = Math.round((positiveFeats / totalFeats) * 100);

    // Tính điểm từ signs
    const detectedSigns = signs.filter(s => s.detected).length;
    const totalSigns = Math.max(signs.length, 1);
    const signsScore = Math.round(((totalSigns - detectedSigns) / totalSigns) * 100);

    // Độ dài nội dung (điểm ước lượng)
    const contentScore = prob > 80 ? 85 : prob > 60 ? 65 : 45;

    const radarData = [prob, relScore, confScore, featScore, signsScore, contentScore];
    const radarLabels = [
      'Xác suất SVM',
      'Điểm tin cậy',
      'Độ tự tin',
      'Tích cực vs Tiêu cực',
      'An toàn dấu hiệu',
      'Chất lượng nội dung'
    ];

    new Chart(radarCtx, {
      type: 'radar',
      data: {
        labels: radarLabels,
        datasets: [{
          label: 'Điểm phân tích',
          data: radarData,
          backgroundColor: isReliable ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
          borderColor: isReliable ? colors.reliable : colors.unreliable,
          borderWidth: 2,
          pointBackgroundColor: isReliable ? colors.reliable : colors.unreliable,
          pointBorderColor: '#fff',
          pointBorderWidth: 1,
          pointRadius: 5,
          pointHoverRadius: 7,
        }, {
          label: 'Ngưỡng an toàn',
          data: [70, 70, 70, 70, 70, 70],
          backgroundColor: 'rgba(78, 124, 255, 0.05)',
          borderColor: 'rgba(78, 124, 255, 0.3)',
          borderWidth: 1,
          borderDash: [5, 5],
          pointRadius: 0,
          pointHoverRadius: 0,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: true,
            position: 'bottom',
            labels: {
              color: colors.text,
              font: { size: 11 },
              padding: 16,
              usePointStyle: true,
              pointStyle: 'circle',
            }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${ctx.raw}/100`
            }
          }
        },
        scales: {
          r: {
            beginAtZero: true,
            max: 100,
            min: 0,
            ticks: {
              stepSize: 20,
              color: colors.textMuted,
              font: { size: 9 },
              backdropColor: 'transparent',
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.06)',
            },
            pointLabels: {
              color: colors.text,
              font: { size: 11, weight: '500' },
            },
            angleLines: {
              color: 'rgba(255, 255, 255, 0.06)',
            }
          }
        }
      }
    });
  }

  // ─── 4. SIGNS PIE/DOUGHNUT CHART ─────────────────────────────────
  const signsCtx = document.getElementById('signs-pie-chart');
  if (signsCtx && signs.length > 0) {
    const detected = signs.filter(s => s.detected).length;
    const clear = signs.length - detected;

    new Chart(signsCtx, {
      type: 'doughnut',
      data: {
        labels: ['⚠️ Dấu hiệu phát hiện', '✅ Không phát hiện'],
        datasets: [{
          data: [detected, clear],
          backgroundColor: [
            'rgba(239, 68, 68, 0.75)',
            'rgba(16, 185, 129, 0.75)',
          ],
          borderColor: [
            'rgba(239, 68, 68, 1)',
            'rgba(16, 185, 129, 1)',
          ],
          borderWidth: 2,
          hoverOffset: 8,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        cutout: '55%',
        plugins: {
          legend: {
            display: true,
            position: 'bottom',
            labels: {
              color: colors.text,
              font: { size: 12 },
              padding: 16,
              usePointStyle: true,
              pointStyle: 'circle',
            }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const total = detected + clear;
                const pct = total > 0 ? Math.round((ctx.raw / total) * 100) : 0;
                return `${ctx.label}: ${ctx.raw}/${total} (${pct}%)`;
              }
            }
          }
        }
      },
      plugins: [{
        id: 'signsCenter',
        afterDraw(chart) {
          const { ctx: c } = chart;
          c.save();
          const centerX = (chart.chartArea.left + chart.chartArea.right) / 2;
          const centerY = (chart.chartArea.top + chart.chartArea.bottom) / 2;

          const total = detected + clear;
          const pct = total > 0 ? Math.round((clear / total) * 100) : 0;

          c.font = 'bold 28px Inter, sans-serif';
          c.fillStyle = pct >= 70 ? colors.reliable : pct >= 40 ? colors.amber : colors.unreliable;
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText(`${pct}%`, centerX, centerY - 8);

          c.font = '11px Inter, sans-serif';
          c.fillStyle = colors.textMuted;
          c.fillText('An toàn', centerX, centerY + 14);

          c.restore();
        }
      }]
    });

    // Thêm chi tiết danh sách signs bên dưới chart
    const signsContainer = signsCtx.parentElement;
    if (signsContainer) {
      const detailDiv = document.createElement('div');
      detailDiv.style.cssText = 'margin-top:16px; display:grid; gap:6px;';
      signs.forEach(sign => {
        const icon = sign.detected ? '⚠️' : '✅';
        const bgColor = sign.detected ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.06)';
        const borderColor = sign.detected ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.15)';
        const textColor = sign.detected ? 'var(--danger-light)' : 'var(--success-light)';
        detailDiv.innerHTML += `
          <div style="display:flex; align-items:center; gap:8px; padding:8px 12px; background:${bgColor}; border:1px solid ${borderColor}; border-radius:8px; font-size:12px;">
            <span>${icon}</span>
            <span style="color:${textColor};">${sign.text}</span>
          </div>`;
      });
      signsContainer.appendChild(detailDiv);
    }
  } else if (signsCtx) {
    const c = signsCtx.getContext('2d');
    c.font = '14px Inter, sans-serif';
    c.fillStyle = colors.textMuted;
    c.textAlign = 'center';
    c.fillText('Không có dữ liệu dấu hiệu', signsCtx.width / 2, signsCtx.height / 2);
  }
});
