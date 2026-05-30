/* ─── Navbar scroll effect ───────────────────── */
window.addEventListener('scroll', () => {
  const nav = document.querySelector('.navbar');
  if (!nav) return;
  nav.classList.toggle('scrolled', window.scrollY > 10);
});

/* ─── Active nav link ────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    const href = link.getAttribute('href');
    if (href === path || (href !== '/' && path.startsWith(href))) {
      link.classList.add('active');
    }
  });
});

/* ─── Counter animation ──────────────────────── */
function animateCounter(el) {
  const target = parseFloat(el.dataset.target);
  const isFloat = target % 1 !== 0;
  const duration = 1600;
  const start = performance.now();

  const tick = (now) => {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    const value = target * ease;
    el.textContent = isFloat ? value.toFixed(1) : Math.round(value).toLocaleString();
    if (progress < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

// Trigger on scroll into view
const counterObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      animateCounter(entry.target);
      counterObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.5 });

document.querySelectorAll('[data-target]').forEach(el => counterObserver.observe(el));

/* ─── Scroll-triggered animations ───────────── */
const animObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      entry.target.style.animationDelay = `${i * 0.08}s`;
      entry.target.classList.add('animate-in');
      animObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.card, .step-card, .metric-card').forEach(el => {
  el.style.opacity = '0';
  animObserver.observe(el);
});

/* ─── Toast notifications ────────────────────── */
function showToast(message, type = 'info', duration = 3500) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideInRight 0.3s ease reverse';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/* ─── Loading overlay ────────────────────────── */
function showLoading(text = 'Đang xử lý...') {
  let overlay = document.querySelector('.loading-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
      <div class="loading-spinner"></div>
      <div class="loading-text">${text}</div>
    `;
    document.body.appendChild(overlay);
  }
}

function hideLoading() {
  const overlay = document.querySelector('.loading-overlay');
  if (overlay) overlay.remove();
}

/* ─── Format date ────────────────────────────── */
function formatDate(isoString) {
  if (!isoString) return '—';
  const d = new Date(isoString);
  const pad = n => String(n).padStart(2, '0');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/* ─── Expose globals ─────────────────────────── */
window.showToast = showToast;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.formatDate = formatDate;

/* ─── Advanced Decorative Effects & Interactions ─── */
document.addEventListener('DOMContentLoaded', () => {
  // 1. Floating Particles Initialization
  const particlesContainer = document.getElementById('particles-container');
  if (particlesContainer) {
    const particleCount = 28;
    for (let i = 0; i < particleCount; i++) {
      const particle = document.createElement('div');
      particle.className = 'particle';
      particle.style.left = `${Math.random() * 100}%`;
      particle.style.bottom = `-${Math.random() * 20}px`;
      
      const size = Math.random() * 3 + 2; // 2px to 5px
      particle.style.width = `${size}px`;
      particle.style.height = `${size}px`;
      
      const duration = Math.random() * 12 + 8; // 8s to 20s
      particle.style.animationDuration = `${duration}s`;
      
      const delay = Math.random() * -20; // negative delay so they start immediately at different phases
      particle.style.animationDelay = `${delay}s`;
      
      particlesContainer.appendChild(particle);
    }
  }

  // 2. Interactive Cursor Glow Trail
  const cursorGlow = document.getElementById('cursor-glow');
  if (cursorGlow) {
    let mouseX = window.innerWidth / 2;
    let mouseY = window.innerHeight / 2;
    let glowX = mouseX;
    let glowY = mouseY;

    window.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
      // Set root variables for any CSS that uses mouse tracking
      document.documentElement.style.setProperty('--mouse-x', `${e.clientX}px`);
      document.documentElement.style.setProperty('--mouse-y', `${e.clientY}px`);
    });

    // Smooth interpolation for fluid cursor lag effect
    const updateGlow = () => {
      const dx = mouseX - glowX;
      const dy = mouseY - glowY;
      glowX += dx * 0.15; // interpolation factor
      glowY += dy * 0.15;
      
      cursorGlow.style.left = `${glowX}px`;
      cursorGlow.style.top = `${glowY}px`;
      
      requestAnimationFrame(updateGlow);
    };
    updateGlow();
  }

  // 3. Extended Scroll Reveal Observer
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => {
          entry.target.classList.add('visible');
        }, i * 60); // subtle cascading stagger
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.05, rootMargin: '0px 0px -50px 0px' });

  const elementsToReveal = document.querySelectorAll('.card, .step-card, .tech-item, .project-info-item, .stat-item, .live-card');
  elementsToReveal.forEach(el => revealObserver.observe(el));

  // 4. Neural Network Dots — Simulates AI neural activity
  const neuralDotsContainer = document.getElementById('neural-dots');
  if (neuralDotsContainer) {
    const neuralDotCount = 18;
    for (let i = 0; i < neuralDotCount; i++) {
      const dot = document.createElement('div');
      dot.className = 'neural-dot';
      dot.style.left = `${5 + Math.random() * 90}%`;
      dot.style.top = `${5 + Math.random() * 90}%`;
      
      const size = Math.random() * 4 + 2;
      dot.style.width = `${size}px`;
      dot.style.height = `${size}px`;
      
      const delay = Math.random() * 6;
      dot.style.animationDelay = `${delay}s`;
      dot.style.animationDuration = `${3 + Math.random() * 4}s`;
      
      neuralDotsContainer.appendChild(dot);
    }

    // Draw connections between nearby neural dots using SVG
    const dots = neuralDotsContainer.querySelectorAll('.neural-dot');
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;';
    neuralDotsContainer.appendChild(svg);

    // Wait for layout then draw connections
    requestAnimationFrame(() => {
      const positions = [];
      dots.forEach(dot => {
        const rect = dot.getBoundingClientRect();
        const containerRect = neuralDotsContainer.getBoundingClientRect();
        positions.push({
          x: rect.left - containerRect.left + rect.width / 2,
          y: rect.top - containerRect.top + rect.height / 2
        });
      });

      for (let i = 0; i < positions.length; i++) {
        for (let j = i + 1; j < positions.length; j++) {
          const dx = positions[i].x - positions[j].x;
          const dy = positions[i].y - positions[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          
          if (dist < 250 && Math.random() > 0.5) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', positions[i].x);
            line.setAttribute('y1', positions[i].y);
            line.setAttribute('x2', positions[j].x);
            line.setAttribute('y2', positions[j].y);
            line.setAttribute('stroke', 'rgba(0, 212, 255, 0.06)');
            line.setAttribute('stroke-width', '0.5');
            line.classList.add('neural-line');
            svg.appendChild(line);
          }
        }
      }
    });
  }

  // 5. Twinkling Stars Background
  const starsContainer = document.getElementById('stars-container');
  if (starsContainer) {
    starsContainer.style.cssText = 'position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;';
    const starCount = 40;
    for (let i = 0; i < starCount; i++) {
      const star = document.createElement('div');
      star.className = 'twinkle-star';
      star.style.left = `${Math.random() * 100}%`;
      star.style.top = `${Math.random() * 100}%`;
      
      const size = Math.random() * 2 + 1;
      star.style.width = `${size}px`;
      star.style.height = `${size}px`;
      
      star.style.animationDelay = `${Math.random() * 5}s`;
      star.style.animationDuration = `${2 + Math.random() * 4}s`;
      
      starsContainer.appendChild(star);
    }
  }

  // 6. Animated data scan line on hero — horizontal sweep
  const heroSection = document.querySelector('.hero');
  if (heroSection) {
    const dataScan = heroSection.querySelector('.data-scan-line');
    if (dataScan) {
      // CSS handles the animation, just ensure it's positioned
      dataScan.style.cssText = 'position:absolute;top:0;left:0;right:0;height:100%;pointer-events:none;z-index:0;overflow:hidden;';
    }
  }
});

