import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Hand Gesture Volume Control", page_icon="🖐️", layout="centered")

st.title("🖐️ Hand Gesture Volume Control")
st.markdown("""
**Instructions:**
1. Click **Start Camera** to enable your webcam.
2. Show your hand — pinch thumb and index finger together/apart to change volume.
3. The volume changes in real-time based on finger distance.
""")

components.html("""
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js" crossorigin="anonymous"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      background: #0e1117; 
      color: white; 
      font-family: 'Segoe UI', sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
    }
    #btn {
      background: #ff4b4b;
      color: white;
      border: none;
      padding: 12px 32px;
      border-radius: 8px;
      font-size: 16px;
      cursor: pointer;
      margin-bottom: 16px;
      font-weight: 600;
      transition: background 0.2s;
    }
    #btn:hover { background: #e03c3c; }
    #btn.stop { background: #555; }
    .canvas-wrapper {
      position: relative;
      width: 100%;
      max-width: 640px;
      border-radius: 12px;
      overflow: hidden;
      background: #1c1c2e;
      border: 2px solid #333;
    }
    canvas {
      width: 100%;
      display: block;
    }
    .hidden { display: none; }
    video { display: none; }

    /* Volume display */
    #vol-display {
      margin-top: 16px;
      width: 100%;
      max-width: 640px;
    }
    .vol-label {
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;
      font-size: 14px;
      color: #ccc;
    }
    .vol-bar-bg {
      background: #2a2a3e;
      border-radius: 8px;
      height: 20px;
      overflow: hidden;
    }
    #vol-bar {
      height: 100%;
      background: linear-gradient(90deg, #00c87a, #00e5ff);
      border-radius: 8px;
      transition: width 0.1s ease;
      width: 50%;
    }
    #status {
      margin-top: 10px;
      font-size: 13px;
      color: #888;
      text-align: center;
    }
    #music-section {
      margin-top: 16px;
      width: 100%;
      max-width: 640px;
      background: #1c1c2e;
      border-radius: 10px;
      padding: 12px 16px;
      border: 1px solid #333;
    }
    #music-label {
      font-size: 13px;
      color: #aaa;
      margin-bottom: 6px;
    }
    audio {
      width: 100%;
      border-radius: 6px;
    }
  </style>
</head>
<body>
  <button id="btn" onclick="toggleCamera()">▶ Start Camera</button>

  <div class="canvas-wrapper">
    <video id="video" autoplay playsinline></video>
    <canvas id="canvas"></canvas>
  </div>

  <div id="vol-display">
    <div class="vol-label">
      <span>Volume</span>
      <span id="vol-pct">50%</span>
    </div>
    <div class="vol-bar-bg">
      <div id="vol-bar"></div>
    </div>
  </div>

  <div id="status">Click "Start Camera" to begin</div>

  <div id="music-section">
    <div id="music-label">🎵 Background Music (volume controlled by gesture)</div>
    <audio id="audio" controls loop>
      <source src="https://github.com/Shubhz20/Hand-Gesture-Volume-Control/raw/main/song.mp3" type="audio/mpeg">
    </audio>
  </div>

<script>
  let camera = null;
  let running = false;
  let volPct = 50;
  const smoothFactor = 0.3;
  const audio = document.getElementById('audio');
  audio.volume = 0.5;

  const video = document.getElementById('video');
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');

  const hands = new Hands({
    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
  });

  hands.setOptions({
    maxNumHands: 1,
    modelComplexity: 0,
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5
  });

  hands.onResults(onResults);

  function onResults(results) {
    canvas.width = results.image.width;
    canvas.height = results.image.height;

    // Draw mirrored camera frame
    ctx.save();
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);
    ctx.restore();

    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
      const landmarks = results.multiHandLandmarks[0];
      const W = canvas.width, H = canvas.height;

      // Mirror x coords for display
      const mx = (x) => W - x * W;
      const my = (y) => y * H;

      const thumb  = landmarks[4];
      const index  = landmarks[8];

      const x1 = mx(thumb.x),  y1 = my(thumb.y);
      const x2 = mx(index.x),  y2 = my(index.y);

      // Draw line between fingers
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = '#00e5ff';
      ctx.lineWidth = 3;
      ctx.stroke();

      // Draw dots
      [{ x: x1, y: y1 }, { x: x2, y: y2 }].forEach(pt => {
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 8, 0, 2 * Math.PI);
        ctx.fillStyle = '#ff4b4b';
        ctx.fill();
      });

      // Draw all landmarks
      drawConnectors(ctx, landmarks, HAND_CONNECTIONS, { color: 'rgba(255,255,255,0.3)', lineWidth: 1 });
      drawLandmarks(ctx, landmarks, { color: 'rgba(255,255,255,0.5)', lineWidth: 1, radius: 3 });

      // Distance-based volume
      const dist = Math.hypot(x2 - x1, y2 - y1) / 4;
      const targetVol = Math.max(0, Math.min(100, (dist - 20) / (150 - 20) * 100));
      volPct += (targetVol - volPct) * smoothFactor;

      // Update audio volume
      audio.volume = Math.max(0, Math.min(1, volPct / 100));
      updateVolumeUI(volPct);
    }

    // Draw volume bar overlay on canvas
    const barH = 150, barW = 22, barX = 16, barY = H - barH - 16;
    const filled = Math.round(barH * volPct / 100);
    ctx.fillStyle = 'rgba(0,0,0,0.4)';
    ctx.roundRect(barX - 4, barY - 4, barW + 8, barH + 28, 8);
    ctx.fill();
    ctx.fillStyle = '#2a2a3e';
    ctx.roundRect(barX, barY, barW, barH, 4);
    ctx.fill();
    const grad = ctx.createLinearGradient(0, barY + barH - filled, 0, barY + barH);
    grad.addColorStop(0, '#00e5ff');
    grad.addColorStop(1, '#00c87a');
    ctx.fillStyle = grad;
    ctx.roundRect(barX, barY + barH - filled, barW, filled, 4);
    ctx.fill();
    ctx.fillStyle = 'white';
    ctx.font = 'bold 11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(Math.round(volPct) + '%', barX + barW / 2, barY + barH + 18);
  }

  function updateVolumeUI(pct) {
    document.getElementById('vol-bar').style.width = pct + '%';
    document.getElementById('vol-pct').textContent = Math.round(pct) + '%';
  }

  async function toggleCamera() {
    const btn = document.getElementById('btn');
    if (!running) {
      running = true;
      btn.textContent = '⏹ Stop Camera';
      btn.classList.add('stop');
      document.getElementById('status').textContent = 'Starting camera...';
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240, frameRate: 15 }, audio: false });
        video.srcObject = stream;
        camera = new Camera(video, {
          onFrame: async () => { await hands.send({ image: video }); },
          width: 320,
          height: 240
        });
        camera.start();
        document.getElementById('status').textContent = '🟢 Camera active — show your hand!';
      } catch (e) {
        document.getElementById('status').textContent = '❌ Camera error: ' + e.message;
        running = false;
        btn.textContent = '▶ Start Camera';
        btn.classList.remove('stop');
      }
    } else {
      running = false;
      btn.textContent = '▶ Start Camera';
      btn.classList.remove('stop');
      if (camera) { camera.stop(); camera = null; }
      if (video.srcObject) {
        video.srcObject.getTracks().forEach(t => t.stop());
        video.srcObject = null;
      }
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      document.getElementById('status').textContent = 'Camera stopped.';
    }
  }
</script>
</body>
</html>
""", height=750)
