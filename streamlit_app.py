import streamlit as st

# HTML Method: Runs Hand Gesture Tracking 100% in the Browser
# Note: Using st.markdown with unsafe_allow_html=True to bypass iframe camera permission blocks.
st.set_page_config(page_title="Hand Gesture Volume Control", layout="centered")

st.title("Hand Gesture Volume Control")
st.write("This version runs entirely in your browser using the HTML Method (client-side AI) to solve connectivity errors.")

# Client-side AI Logic (HTML/JS/CSS)
st.markdown(
    \"\"\"
    <div id="cam_container" style="position: relative; width: 640px; height: 480px; margin: auto; background: #000; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 30px rgba(0,0,0,0.5);">
        <video id="input_video" style="display: none;" playsinline></video>
        <canvas id="output_canvas" width="640" height="480" style="width: 100%; height: 100%; transform: scaleX(-1);"></canvas>
        
        <!-- Volume UI Overlay -->
        <div style="position: absolute; right: 30px; top: 120px; width: 30px; height: 240px; background: rgba(255,255,255,0.1); border: 2px solid rgba(255,255,255,0.5); border-radius: 15px; padding: 3px;">
             <div id="vol_fill" style="position: absolute; bottom: 0; left: 0; width: 100%; height: 50%; background: #00ff88; border-radius: 10px; transition: height 0.1s;"></div>
        </div>
        <div id="vol_label" style="position: absolute; right: 20px; top: 90px; color: #fff; font-family: monospace; font-weight: bold; background: rgba(0,0,0,0.5); padding: 2px 5px; border-radius: 4px;">Vol: 50%</div>

        <button id="start_button" style="position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); padding: 20px 40px; font-size: 20px; background: #00ff88; border: none; border-radius: 10px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 10px rgba(0,255,136,0.5); z-index: 10;">Start Camera</button>
        <div id="status_msg" style="position: absolute; width: 100%; bottom: 20px; text-align: center; color: #fff; font-family: sans-serif; pointer-events: none; text-shadow: 1px 1px 2px #000;">Ready</div>
        
        <audio id="audio_element" loop crossorigin="anonymous">
            <source src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" type="audio/mpeg">
        </audio>
    </div>

    <!-- MediaPipe Libraries -->
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js" crossorigin="anonymous"></script>

    <script>
    const video = document.getElementById('input_video');
    const canvas = document.getElementById('output_canvas');
    const ctx = canvas.getContext('2d');
    const audio = document.getElementById('audio_element');
    const startBtn = document.getElementById('start_button');
    const statusMsg = document.getElementById('status_msg');
    const volFill = document.getElementById('vol_fill');
    const volLabel = document.getElementById('vol_label');

    let currentVolume = 0.5;
    audio.volume = currentVolume;

    function onResults(results) {
        ctx.save();
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);
        
        if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
            const landmarks = results.multiHandLandmarks[0];
            
            // Draw Hand Connections
            window.drawConnectors(ctx, landmarks, window.HAND_CONNECTIONS, {color: '#00FF88', lineWidth: 4});
            window.drawLandmarks(ctx, landmarks, {color: '#FF3B30', lineWidth: 1, radius: 3});

            // Index Tip (8) and Thumb Tip (4)
            const index = landmarks[8];
            const thumb = landmarks[4];

            // Distance in screen pixels
            const dx = (index.x - thumb.x) * canvas.width;
            const dy = (index.y - thumb.y) * canvas.height;
            const dist = Math.sqrt(dx*dx + dy*dy);

            // Volume Scaling (min 30px, max 200px)
            let vol = (dist - 30) / (200 - 30);
            vol = Math.max(0, Math.min(1, vol));
            
            // Smoothing
            currentVolume += (vol - currentVolume) * 0.2;
            audio.volume = currentVolume;

            // Update Overlay
            const pct = Math.round(currentVolume * 100);
            volFill.style.height = pct + '%';
            volLabel.innerText = 'Vol: ' + pct + '%';

            // Draw connecting line between fingers
            ctx.beginPath();
            ctx.moveTo(thumb.x * canvas.width, thumb.y * canvas.height);
            ctx.lineTo(index.x * canvas.width, index.y * canvas.height);
            ctx.strokeStyle = '#FFFFFF';
            ctx.lineWidth = 3;
            ctx.stroke();
        }
        ctx.restore();
    }

    async function init() {
        startBtn.style.display = 'none';
        statusMsg.innerText = 'Initalizing AI...';

        const hands = new Hands({locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
        }});
        
        hands.setOptions({
            maxNumHands: 1,
            modelComplexity: 1,
            minDetectionConfidence: 0.5,
            minTrackingConfidence: 0.5
        });
        
        hands.onResults(onResults);

        const camera = new Camera(video, {
            onFrame: async () => {
                await hands.send({image: video});
            },
            width: 640,
            height: 480
        });

        statusMsg.innerText = 'Starting Camera...';
        try {
            await audio.play();
            await camera.start();
            statusMsg.innerText = 'Running Locally (Zero Lag)';
        } catch (e) {
            statusMsg.innerText = 'Error: ' + e.message;
            startBtn.style.display = 'block';
        }
    }

    startBtn.addEventListener('click', init);
    </script>
    \"\"\",
    unsafe_allow_html=True
)

st.write("---")

# ---------------------------------------------------------
# COMMENTED OUT PYTHON CODE BASE (ARCHIVED)
# ---------------------------------------------------------

# import os
# os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"
# os.environ["MESA_GL_VERSION_OVERRIDE"] = "3.3"
# os.environ["GLOG_minloglevel"] = "2"

# import cv2
# import mediapipe as mp
# import numpy as np
# import streamlit as st
# import av
# from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, AudioProcessorBase, WebRtcMode

# class SharedState:
#     def __init__(self):
#         self.volume = 1.0

# @st.cache_data
# def load_song_to_memory():
#     try:
#         container = av.open("song.mp3")
#         stream = container.streams.audio[0]
#         resampler = av.AudioResampler(format="s16", layout="stereo", rate=48000)
#         frames = []
#         for packet in container.demux(stream):
#             for frame in packet.decode():
#                 r_frames = resampler.resample(frame)
#                 for r in r_frames:
#                     frames.append(r.to_ndarray())
#         full_audio = np.concatenate(frames, axis=1)
#         if full_audio.shape[0] == 1:
#             full_audio = np.concatenate([full_audio, full_audio], axis=0)
#         return full_audio
#     except Exception as e:
#         return None

# class GestureProcessor(VideoProcessorBase):
#     def __init__(self):
#         self.mp_hands = mp.solutions.hands
#         self.hands = self.mp_hands.Hands(static_image_mode=False, max_num_hands=1)
#         self.drawing_utils = mp.solutions.drawing_utils
#         self.prev_volume_pct = 50.0

#     def recv(self, frame):
#         image = frame.to_ndarray(format="bgr24")
#         # ... MediaPipe Logic ...
#         return av.VideoFrame.from_ndarray(image, format="bgr24")

# class AudioVolumeProcessor(AudioProcessorBase):
#     def recv(self, frame):
#         return frame

# webrtc_streamer(
#     key="gesture-volume",
#     mode=WebRtcMode.SENDRECV,
#     rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
#     video_processor_factory=GestureProcessor,
#     audio_processor_factory=AudioVolumeProcessor,
#     async_processing=True,
# )
