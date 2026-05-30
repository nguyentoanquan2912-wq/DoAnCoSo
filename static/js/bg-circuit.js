/**
 * High-tech Animated Circuit Background (AI Core & Chatbot Node Edition)
 * Draws a central AI processor core on the left and a chatbot on the right
 * connected by glowing circuit lines, simulating data packets and neural communication.
 */

(function () {
  const canvas = document.getElementById('bg-circuit');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let width = canvas.width = window.innerWidth;
  let height = canvas.height = window.innerHeight;

  let paths = [];
  let connectorPaths = [];
  let pulses = [];
  let time = 0;
  let rotationAngle = 0;
  let botReceiveFlash = 0; // Triggered when a pulse hits the bot
  let isMobile = false;

  // AI Core & Bot Coordinates
  let coreX = 0, coreY = 0;
  let botX = 0, botY = 0;

  // Mouse position tracking
  let mouse = { x: null, y: null, radius: 130 };

  window.addEventListener('mousemove', (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
  });

  window.addEventListener('mouseleave', () => {
    mouse.x = null;
    mouse.y = null;
  });

  window.addEventListener('resize', () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    initLayout();
  });

  // Calculate layout coordinates and pre-generate paths
  function initLayout() {
    isMobile = width < 800;

    if (isMobile) {
      coreX = width * 0.5;
      coreY = height * 0.22;
      botX = width * 0.5;
      botY = height * 0.72;
    } else {
      coreX = width * 0.28;
      coreY = height * 0.5;
      botX = width * 0.76;
      botY = height * 0.5;
    }

    generateStaticCircuits();
    pulses = [];
  }

  // Pre-generate circuit lines
  function generateStaticCircuits() {
    paths = [];
    connectorPaths = [];

    const coreRadius = 45;

    // 1. GENERATE RADIAL TRACES FROM THE AI CORE
    const numRadial = isMobile ? 12 : 18;
    for (let i = 0; i < numRadial; i++) {
      const angle = (i * (2 * Math.PI)) / numRadial;
      
      // Filter out angles pointing directly to the chatbot to avoid overlap with connectors
      if (!isMobile) {
        // Chatbot is to the right (around 0 radians / 360 degrees)
        // Skip angles between -30deg and +30deg
        const deg = (angle * 180) / Math.PI;
        if (deg < 35 || deg > 325) continue;
      } else {
        // Chatbot is below (around 90deg / Math.PI/2 radians)
        // Skip angles between 60deg and 120deg
        const deg = (angle * 180) / Math.PI;
        if (deg > 55 && deg < 125) continue;
      }

      const points = [];
      
      // Start on Core outer ring
      const startX = coreX + Math.cos(angle) * coreRadius;
      const startY = coreY + Math.sin(angle) * coreRadius;
      points.push({ x: startX, y: startY });

      // First leg: radial extension
      const len1 = Math.random() * 40 + 35;
      const x1 = startX + Math.cos(angle) * len1;
      const y1 = startY + Math.sin(angle) * len1;
      points.push({ x: x1, y: y1 });

      // Second leg: 45 degree bend
      const bendDir = Math.random() > 0.5 ? 1 : -1;
      const bendAngle = angle + (bendDir * Math.PI) / 4;
      const len2 = Math.random() * 35 + 25;
      const x2 = x1 + Math.cos(bendAngle) * len2;
      const y2 = y1 + Math.sin(bendAngle) * len2;
      
      // Clamp coordinates within screen boundaries
      if (x2 > 20 && x2 < width - 20 && y2 > 20 && y2 < height - 20) {
        points.push({ x: x2, y: y2 });

        // Third leg: Straight horizontal or vertical run to blend into grid
        const x3 = x2 + (Math.cos(angle) >= 0 ? 1 : -1) * (Math.random() * 80 + 50);
        const y3 = y2;
        if (x3 > 20 && x3 < width - 20) {
          points.push({ x: x3, y: y3 });
        }
      }

      paths.push({
        points: points,
        width: Math.random() * 0.7 + 0.6,
        color: `rgba(0, 212, 255, ${Math.random() * 0.08 + 0.07})`, // Electric Cyan
        pulseColor: '#00d4ff',
        pulseSpeed: Math.random() * 0.8 + 0.9,
        lastSpawn: 0,
        spawnDelay: Math.random() * 5000 + 2000
      });
    }

    // 2. GENERATE CONNECTOR TRACES FROM CORE TO BOT
    const numConnectors = 3;
    const botRadius = 32;

    for (let i = 0; i < numConnectors; i++) {
      const points = [];
      
      if (!isMobile) {
        // Desktop: Left to Right
        // Offset Y for top, middle, and bottom connectors
        const offsetY = (i - 1) * 15;
        const startX = coreX + coreRadius;
        const startY = coreY + offsetY;
        points.push({ x: startX, y: startY });

        // Run straight, then bend, then straight
        if (i === 1) {
          // Middle is completely straight
          points.push({ x: botX - botRadius - 10, y: botY });
        } else {
          // Top & Bottom bend 45 degrees to meet chatbot
          const x1 = startX + (botX - coreX) * 0.4;
          points.push({ x: x1, y: startY });

          const x2 = x1 + Math.abs(offsetY);
          const y2 = botY + (offsetY > 0 ? 12 : -12);
          points.push({ x: x2, y: y2 });
          points.push({ x: botX - botRadius - 6, y: y2 });
        }
      } else {
        // Mobile: Top to Bottom
        const offsetX = (i - 1) * 15;
        const startX = coreX + offsetX;
        const startY = coreY + coreRadius;
        points.push({ x: startX, y: startY });

        if (i === 1) {
          points.push({ x: botX, y: botY - botRadius - 10 });
        } else {
          const y1 = startY + (botY - coreY) * 0.4;
          points.push({ x: startX, y: y1 });

          const y2 = y1 + Math.abs(offsetX);
          const x2 = botX + (offsetX > 0 ? 12 : -12);
          points.push({ x: x2, y: y2 });
          points.push({ x: x2, y: botY - botRadius - 6 });
        }
      }

      connectorPaths.push({
        points: points,
        width: 1.0,
        color: 'rgba(0, 212, 255, 0.16)', // Slightly brighter connector lines
        pulseColor: '#00d4ff',
        pulseSpeed: 1.5,
        lastSpawn: 0,
        spawnDelay: Math.random() * 3000 + 1000
      });
    }
  }

  // Data pulse representation
  class DataPulse {
    constructor(path, isConnector = false) {
      this.path = path;
      this.isConnector = isConnector;
      this.segIndex = 0;
      this.progress = 0;
      this.speed = path.pulseSpeed;
      this.color = path.pulseColor;
      this.size = isConnector ? 1.8 : 1.3;
      this.active = true;

      const p = this.path.points[0];
      this.x = p.x;
      this.y = p.y;
    }

    update() {
      if (!this.active) return;

      const p1 = this.path.points[this.segIndex];
      const p2 = this.path.points[this.segIndex + 1];

      if (!p1 || !p2) {
        this.active = false;
        return;
      }

      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      this.progress += this.speed / dist;

      if (this.progress >= 1) {
        this.segIndex++;
        this.progress = 0;
        if (this.segIndex >= this.path.points.length - 1) {
          this.active = false;
          // Trigger chatbot notification glow if it's a connector pulse hitting the chatbot
          if (this.isConnector) {
            botReceiveFlash = 1.0;
          }
        }
      } else {
        this.x = p1.x + dx * this.progress;
        this.y = p1.y + dy * this.progress;
      }
    }

    draw() {
      if (!this.active) return;

      // Pulse Glow Head
      ctx.shadowBlur = 14;
      ctx.shadowColor = '#00d4ff';
      ctx.fillStyle = '#ffffff'; // White core

      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      ctx.fill();

      // Outer color core
      ctx.fillStyle = '#00d4ff';
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size * 1.5, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(0, 212, 255, 0.4)';
      ctx.fill();

      ctx.shadowBlur = 0; // reset

      // Tail
      const p1 = this.path.points[this.segIndex];
      const p2 = this.path.points[this.segIndex + 1];
      if (p1 && p2) {
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const ux = dx / dist;
        const pointerY = dy / dist;

        const tailLen = Math.min(32, dist * this.progress);
        
        ctx.beginPath();
        ctx.moveTo(this.x, this.y);
        ctx.lineTo(this.x - ux * tailLen, this.y - pointerY * tailLen);
        
        const grad = ctx.createLinearGradient(this.x, this.y, this.x - ux * tailLen, this.y - pointerY * tailLen);
        grad.addColorStop(0, 'rgba(0, 212, 255, 0.85)');
        grad.addColorStop(1, 'rgba(0, 212, 255, 0)');
        
        ctx.lineWidth = this.size * 1.2;
        ctx.strokeStyle = grad;
        ctx.stroke();
      }
    }
  }

  // Draw AI Core Processor Circle on the left
  function drawAICore() {
    const breath = Math.sin(time * 0.04);
    const size = 32;

    // Pulse aura glow
    ctx.shadowBlur = 18 + breath * 4;
    ctx.shadowColor = 'rgba(0, 212, 255, 0.45)';
    
    // 1. Outer breathing halo
    ctx.beginPath();
    ctx.arc(coreX, coreY, size * (1.3 + breath * 0.1), 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(0, 212, 255, 0.05)';
    ctx.fill();
    ctx.shadowBlur = 0; // Reset

    // 2. Rotating dashed dial ring
    ctx.save();
    ctx.translate(coreX, coreY);
    ctx.rotate(rotationAngle);
    ctx.beginPath();
    ctx.arc(0, 0, size * 1.2, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.28)';
    ctx.lineWidth = 1.2;
    ctx.setLineDash([7, 7]);
    ctx.stroke();
    ctx.restore();

    // 3. Middle ring
    ctx.beginPath();
    ctx.arc(coreX, coreY, size * 0.85, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.45)';
    ctx.lineWidth = 1.0;
    ctx.stroke();

    // 4. Central square CPU Chip with rounded corners
    const chipSize = 34;
    ctx.save();
    ctx.shadowBlur = 12;
    ctx.shadowColor = '#00d4ff';
    ctx.fillStyle = '#0a1628'; // Deep blue fill
    ctx.strokeStyle = '#00d4ff';
    ctx.lineWidth = 1.5;
    
    // Draw rounded rect
    ctx.beginPath();
    const cx = coreX - chipSize/2;
    const cy = coreY - chipSize/2;
    ctx.roundRect(cx, cy, chipSize, chipSize, 5);
    ctx.fill();
    ctx.stroke();
    ctx.shadowBlur = 0; // reset

    // Write "AI" inside
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 13px Inter, -apple-system, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('AI', coreX, coreY + 0.5);
    ctx.restore();
  }

  // Draw Chatbot robot face & speech bubble on the right
  function drawRobotBot() {
    const scaleFactor = 1 + botReceiveFlash * 0.15;
    const currentGlow = 8 + botReceiveFlash * 14;
    
    ctx.save();
    ctx.translate(botX, botY);
    
    // Dynamic glow during transmission hit
    if (botReceiveFlash > 0.05) {
      ctx.shadowBlur = currentGlow;
      ctx.shadowColor = '#00d4ff';
    }

    // 1. Draw head (circle)
    ctx.beginPath();
    ctx.arc(0, 0, 21 * scaleFactor, 0, Math.PI * 2);
    ctx.fillStyle = '#0a1628';
    ctx.strokeStyle = botReceiveFlash > 0.1 ? '#ffffff' : '#00d4ff';
    ctx.lineWidth = 1.5;
    ctx.fill();
    ctx.stroke();
    ctx.shadowBlur = 0; // reset

    // 2. Draw headphones/ears
    ctx.fillStyle = '#00d4ff';
    // Left ear piece
    ctx.beginPath();
    ctx.arc(-22 * scaleFactor, 0, 4.5 * scaleFactor, 0, Math.PI * 2);
    ctx.fill();
    // Right ear piece
    ctx.beginPath();
    ctx.arc(22 * scaleFactor, 0, 4.5 * scaleFactor, 0, Math.PI * 2);
    ctx.fill();
    
    // Headband arc
    ctx.beginPath();
    ctx.arc(0, 0, 22.5 * scaleFactor, Math.PI, 0);
    ctx.strokeStyle = '#00d4ff';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 3. Eyes (glowing cyan LEDs)
    const eyeSpacing = 7.5 * scaleFactor;
    const eyeSize = 2.4 * scaleFactor;
    ctx.shadowBlur = 8;
    ctx.shadowColor = '#00d4ff';
    ctx.fillStyle = botReceiveFlash > 0.1 ? '#ffffff' : '#00d4ff';

    // Left Eye
    ctx.beginPath();
    ctx.arc(-eyeSpacing, -2 * scaleFactor, eyeSize, 0, Math.PI * 2);
    ctx.fill();

    // Right Eye
    ctx.beginPath();
    ctx.arc(eyeSpacing, -2 * scaleFactor, eyeSize, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0; // reset

    // 4. Smile mouth
    ctx.beginPath();
    ctx.arc(0, 4 * scaleFactor, 5 * scaleFactor, 0.1 * Math.PI, 0.9 * Math.PI);
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.85)';
    ctx.lineWidth = 1.2;
    ctx.stroke();

    // 5. Draw Speech Bubble floating above robot
    drawSpeechBubble(scaleFactor);

    ctx.restore();
  }

  // Draw floating chatbot comment bubble
  function drawSpeechBubble(scale) {
    const bx = 16 * scale;
    const by = -48 * scale;
    const bw = 38 * scale;
    const bh = 18 * scale;
    const r = 4 * scale;

    ctx.save();
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.4)';
    ctx.fillStyle = 'rgba(10, 22, 40, 0.85)';
    ctx.lineWidth = 1.0;

    // Draw speech rectangle
    ctx.beginPath();
    ctx.roundRect(bx, by, bw, bh, r);
    ctx.fill();
    ctx.stroke();

    // Speech indicator triangle
    ctx.beginPath();
    ctx.moveTo(bx + 6 * scale, by + bh);
    ctx.lineTo(bx + 2 * scale, by + bh + 5 * scale);
    ctx.lineTo(bx + 11 * scale, by + bh);
    ctx.closePath();
    ctx.fillStyle = 'rgba(10, 22, 40, 0.85)';
    ctx.fill();
    ctx.stroke();

    // Typing dots animation
    const dotPhase = Math.floor(time / 20) % 4; // 0, 1, 2, 3
    ctx.fillStyle = '#00d4ff';
    const dotXStart = bx + 10 * scale;
    const dotY = by + bh/2 + 0.5 * scale;
    const dotDist = 6 * scale;

    for (let i = 0; i < 3; i++) {
      ctx.beginPath();
      ctx.arc(dotXStart + i * dotDist, dotY, 1.2 * scale, 0, Math.PI * 2);
      ctx.fillStyle = (i === dotPhase) ? '#ffffff' : 'rgba(0, 212, 255, 0.4)';
      ctx.fill();
    }

    ctx.restore();
  }

  // Draw paths
  function drawCircuits() {
    // Draw radiating paths
    paths.forEach(path => {
      ctx.beginPath();
      ctx.moveTo(path.points[0].x, path.points[0].y);
      for (let j = 1; j < path.points.length; j++) {
        ctx.lineTo(path.points[j].x, path.points[j].y);
      }
      ctx.lineWidth = path.width;
      ctx.strokeStyle = path.color;
      ctx.stroke();

      // End pads
      const lastPt = path.points[path.points.length - 1];
      ctx.fillStyle = path.color.replace('0.07', '0.4').replace('0.08', '0.4');
      ctx.beginPath();
      ctx.arc(lastPt.x, lastPt.y, 2.0, 0, Math.PI * 2);
      ctx.fill();
    });

    // Draw connecting paths between Core & Bot
    connectorPaths.forEach(path => {
      ctx.beginPath();
      ctx.moveTo(path.points[0].x, path.points[0].y);
      for (let j = 1; j < path.points.length; j++) {
        ctx.lineTo(path.points[j].x, path.points[j].y);
      }
      ctx.lineWidth = path.width;
      ctx.strokeStyle = path.color;
      ctx.stroke();
    });
  }

  // Auto spawn pulses
  function autoSpawn(timestamp) {
    // 1. Spawning core radiating pulses
    paths.forEach(path => {
      if (timestamp - path.lastSpawn > path.spawnDelay) {
        if (pulses.length < 24 && Math.random() > 0.4) {
          pulses.push(new DataPulse(path, false));
          path.lastSpawn = timestamp;
          path.spawnDelay = Math.random() * 4000 + 2000;
        }
      }
    });

    // 2. Spawning connector communication pulses
    connectorPaths.forEach(path => {
      if (timestamp - path.lastSpawn > path.spawnDelay) {
        if (pulses.length < 24 && Math.random() > 0.35) {
          pulses.push(new DataPulse(path, true));
          path.lastSpawn = timestamp;
          path.spawnDelay = Math.random() * 3000 + 1500;
        }
      }
    });
  }

  // Mouse interaction spawning
  function spawnMouseInteraction() {
    if (mouse.x === null || mouse.y === null) return;
    
    // Spawn pulses from Core or Connectors if mouse is close
    const dCore = Math.sqrt((mouse.x - coreX) ** 2 + (mouse.y - coreY) ** 2);
    const dBot = Math.sqrt((mouse.x - botX) ** 2 + (mouse.y - botY) ** 2);
    
    if (dCore < mouse.radius) {
      paths.forEach(path => {
        if (pulses.length < 25 && Math.random() > 0.985) {
          pulses.push(new DataPulse(path, false));
        }
      });
    }

    if (dBot < mouse.radius) {
      connectorPaths.forEach(path => {
        if (pulses.length < 25 && Math.random() > 0.98) {
          // Send reverse pulses or interaction pulse
          pulses.push(new DataPulse(path, true));
        }
      });
    }
  }

  // Render loop
  function loop(timestamp) {
    time++;
    rotationAngle += 0.005;
    
    // Decay flash
    botReceiveFlash = Math.max(0, botReceiveFlash - 0.025);

    // Clear Canvas
    ctx.clearRect(0, 0, width, height);

    // Draw lines
    drawCircuits();

    // Draw central AI CPU and Bot
    drawAICore();
    drawRobotBot();

    // Handle pulse spawning
    autoSpawn(timestamp);
    spawnMouseInteraction();

    // Update and draw pulses
    for (let i = pulses.length - 1; i >= 0; i--) {
      const pulse = pulses[i];
      pulse.update();
      if (!pulse.active) {
        pulses.splice(i, 1);
      } else {
        pulse.draw();
      }
    }

    requestAnimationFrame(loop);
  }

  // Kickoff
  initLayout();
  requestAnimationFrame(loop);
})();
