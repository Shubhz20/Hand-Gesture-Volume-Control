const videoElement = document.getElementById('input-video');
const canvasElement = document.getElementById('output-canvas');
const canvasCtx = canvasElement.getContext('2d');
const musicPlayer = document.getElementById('music-player');
const volumeBar = document.getElementById('volume-bar');
const volumeValueDisplay = document.getElementById('volume-val');
const startBtn = document.getElementById('start-btn');

let volume = 0.5; // Shared volume state

// Handle start button
startBtn.addEventListener('click', () => {
    musicPlayer.play();
    startBtn.innerText = "System Engaged";
    startBtn.style.opacity = "0.5";
    startBtn.disabled = true;
});

// Configure MediaPipe Hands
const hands = new Hands({
    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
});

hands.setOptions({
    maxNumHands: 1,
    modelComplexity: 1,
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5
});

// MediaPipe results handler
hands.onResults((results) => {
    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
    canvasCtx.drawImage(results.image, 0, 0, canvasElement.width, canvasElement.height);

    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
        const landmarks = results.multiHandLandmarks[0];
        
        // Draw landmarks
        drawConnectors(canvasCtx, landmarks, HAND_CONNECTIONS, { color: '#818cf8', lineWidth: 5 });
        drawLandmarks(canvasCtx, landmarks, { color: '#c084fc', lineWidth: 2 });

        // Calculate distance between thumb (4) and index (8)
        const thumbTip = landmarks[4];
        const indexTip = landmarks[8];
        
        const dx = (thumbTip.x - indexTip.x) * canvasElement.width;
        const dy = (thumbTip.y - indexTip.y) * canvasElement.height;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Map distance to volume (approximate 40px to 300px range)
        let targetVol = (distance - 40) / (300 - 40);
        targetVol = Math.max(0, Math.min(1, targetVol)); // Clamp 0 to 1

        // Smooth volume update
        volume = volume + (targetVol - volume) * 0.2;
        musicPlayer.volume = volume;
        
        // Update UI
        const volPercent = Math.round(volume * 100);
        volumeBar.style.width = `${volPercent}%`;
        volumeValueDisplay.innerText = `${volPercent}%`;
        
        // Visual feedback on hand
        canvasCtx.beginPath();
        canvasCtx.moveTo(thumbTip.x * canvasElement.width, thumbTip.y * canvasElement.height);
        canvasCtx.lineTo(indexTip.x * canvasElement.width, indexTip.y * canvasElement.height);
        canvasCtx.strokeStyle = '#22c55e';
        canvasCtx.lineWidth = 10;
        canvasCtx.stroke();
    }
    canvasCtx.restore();
});

// Initialize Camera
const camera = new Camera(videoElement, {
    onFrame: async () => {
        await hands.send({ image: videoElement });
    },
    width: 1280,
    height: 720
});
camera.start();
