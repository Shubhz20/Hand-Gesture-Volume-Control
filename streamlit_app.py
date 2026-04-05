import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Hand Gesture Volume Control", page_icon="🖐️", layout="centered")

st.title("🖐️ Hand Gesture Volume Control")
st.markdown("""
**Instructions:**
1. Click **▶ Start Camera** and allow camera access.
2. Show your hand — pinch thumb and index finger together/apart to change volume.
3. The volume bar updates in real-time based on your finger distance.
""")

# Use st.components.v1.iframe alternative - embed full HTML
components.html("""
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1646424915/hands.js" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils@0.3.1640029074/camera_utils.js" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils@0.3.1620248257/drawing_utils.js" crossorigin="anonymous"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #0e1117;
      color: white;
      font-family: 'Segoe UI', sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 12px;
      gap: 12px;
    }
    #btn {
      background: linear-gradient(135deg, #ff4b4b, #ff6b6b);
      color: white;
      border: none;
      padding: 12px 36px;
      border-radius: 50px;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
      box-shadow: 0 4px 15px rgba(255,75,75,0.4);
      letter-spacing: 0.5px;
    }
    #btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(255,75,75,0.5); }
    #btn.stop { background: linear-gradient(135deg, #555, #333); box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
    .canvas-wrap {
      width: 100%;
      max-width: 620px;
      border-radius: 14px;
      overflow: hidden;
      border: 2px solid #2a2a3e;
      background: #13131f;
      position: relative;
    }
    canvas { width: 100%; display: block; }
    video { display: none; }
    #vol-row {
      width: 100%;
      max-width: 620px;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    #vol-label { font-size: 13px; color: #aaa; white-space: nowrap; min-width: 80px; }
    .bar-bg {
      flex: 1;
      background: #1e1e2e;
      border-radius: 50px;
      height: 18px;
      overflow: hidden;
      border: 1px solid #2a2a3e;
    }
    #vol-bar {
      height: 100%;
      background: linear-gradient(90deg, #00c87a, #00e5ff);
      border-radius: 50px;
      width: 50%;
      transition: width 0.08s linear;
    }
    #vol-pct { font-size: 14px; font-weight: 700; min-width: 40px; text-align: right; color: #00e5ff; }
    #status {
      font-size: 12px;
      color: #666;
      text-align: center;
    }
    #music-wrap {
      width: 100%;
      max-width: 620px;
      background: #13131f;
      border: 1px solid #2a2a3e;
      border-radius: 12px;
      padding: 12px 16px;
    }
    #music-title { font-size: 12px; color: #888; margin-bottom: 8px; }
    audio { width: 100%; }
  </style>
</head>
<body>
  <button id="btn" onclick="toggleCamera()">&#9654; Start Camera</button>

  <div class="canvas-wrap">
    <video id="video" autoplay playsinline></video>
    <canvas id="canvas"></canvas>
  </div>

  <div id="vol-row">
    <span id="vol-label">&#128266; Volume</span>
    <div class="bar-bg"><div id="vol-bar"></div></div>
    <span id="vol-pct">50%</span>
  </div>

  <div id="status">Click "Start Camera" to begin</div>

  <div id="music-wrap">
    <div id="music-title">&#127925; Music — volume controlled by your hand gesture</div>
    <audio id="audio" controls loop>
      <source src="https://github.com/Shubhz20/Hand-Gesture-Volume-Control/raw/main/song.mp3" type="audio/mpeg">
      Your browser does not support the audio element.
    </audio>
  </div>

<script>
  let mpCamera = null;
  let running  = false;
  let volPct   = 50;
  const SMOOTH = 0.25;

  const audioEl  = document.getElementById('audio');
  const videoEl  = document.getElementById('video');
  const canvas   = document.getElementById('canvas');
  const ctx      = canvas.getContext('2d');
  const volBar   = document.getElementById('vol-bar');
  const volPctEl = document.getElementById('vol-pct');
  const statusEl = document.getElementById('status');
  const btn      = document.getElementById('btn');
  audioEl.volume = 0.5;

  // --- MediaPipe Hands ---
  const hands = new Hands({ locateFile: f => `https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1646424915/${f}` });
  hands.setOptions({ maxNumHands: 1, modelComplexity: 0, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
  hands.onResults(onResults);

  function onResults(res) {
    const W = res.image.width, H = res.image.height;
    canvas.width = W; canvas.height = H;

    // Mirror draw
    ctx.save();
    ctx.translate(W, 0); ctx.scale(-1, 1);
    ctx.drawImage(res.image, 0, 0, W, H);
    ctx.restore();

    if (res.multiHandLandmarks && res.multiHandLandmarks.length) {
      const lm = res.multiHandLandmarks[0];

      // Draw skeleton (mirrored coords)
      const mirroredLm = lm.map(p => ({ x: 1 - p.x, y: p.y, z: p.z }));
      drawConnectors(ctx, mirroredLm, HAND_CONNECTIONS, { color: 'rgba(0,229,255,0.5)', lineWidth: 2 });
      drawLandmarks(ctx, mirroredLm, { color: '#ff4b4b', lineWidth: 1, radius: 4 });

      const thumb = mirroredLm[4], index = mirroredLm[8];
      const x1 = thumb.x * W, y1 = thumb.y * H;
      const x2 = index.x * W, y2 = index.y * H;

      // Finger connector line
      ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2);
      ctx.strokeStyle = '#00e5ff'; ctx.lineWidth = 3; ctx.stroke();

      const dist = Math.hypot(x2-x1, y2-y1) / 4;
      const target = Math.max(0, Math.min(100, (dist - 20) / (130 - 20) * 100));
      volPct += (target - volPct) * SMOOTH;

      audioEl.volume = Math.max(0, Math.min(1, volPct / 100));
    }

    // Update UI bar
    volBar.style.width = volPct + '%';
    volPctEl.textContent = Math.round(volPct) + '%';

    // Overlay volume text on canvas
    ctx.fillStyle = 'rgba(0,0,0,0.55)';
    ctx.fillRect(10, 10, 110, 34);
    ctx.fillStyle = '#00e5ff';
    ctx.font = 'bold 14px sans-serif';
    ctx.fillText('Vol: ' + Math.round(volPct) + '%', 20, 32);
  }

  async function toggleCamera() {
    if (!running) {
      running = true;
      btn.textContent = '&#9646;&#9646; Stop Camera';
      btn.classList.add('stop');
      statusEl.textContent = 'Starting camera...';
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240, frameRate: 15 }, audio: false });
        videoEl.srcObject = stream;
        mpCamera = new Camera(videoEl, {
          onFrame: async () => { await hands.send({ image: videoEl }); },
          width: 320, height: 240
        });
        mpCamera.start();
        statusEl.textContent = '&#128994; Camera active — show your hand!';
      } catch (e) {
        statusEl.textContent = '&#10060; Camera error: ' + e.message;
        running = false;
        btn.textContent = '&#9654; Start Camera';
        btn.classList.remove('stop');
      }
    } else {
      running = false;
      btn.textContent = '&#9654; Start Camera';
      btn.classList.remove('stop');
      if (mpCamera) { mpCamera.stop(); mpCamera = null; }
      if (videoEl.srcObject) { videoEl.srcObject.getTracks().forEach(t => t.stop()); videoEl.srcObject = null; }
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      statusEl.textContent = 'Camera stopped.';
    }
  }
</script>
</body>
</html>
""", height=720)
