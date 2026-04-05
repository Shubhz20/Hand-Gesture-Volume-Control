import streamlit as st
import streamlit.components.v1 as components

# HTML Method: Runs Hand Gesture Tracking 100% in the Browser
# This bypasses all networking and server CPU issues. 
st.title("Hand Gesture Volume Control")
st.markdown("This version runs entirely in your browser using the **HTML Method** for maximum speed and zero lag.")
st.info("Instructions: 1. Click Start. 2. Allow camera access. 3. Pinch index and thumb to change music volume.")

components.html(
    \"\"\"
    <div id="container" style="position: relative; width: 640px; height: 480px; margin: auto; background: #000; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.5);">
        <video id="input_video" style="display: none;" playsinline></video>
        <canvas id="output_canvas" width="640" height="480" style="width: 100%; height: 100%; transform: scaleX(-1);"></canvas>
        <div id="vol_bar_bg" style="position: absolute; right: 30px; top: 140px; width: 25px; height: 200px; background: rgba(255,255,255,0.2); border: 2px solid #fff; border-radius: 5px;"></div>
        <div id="vol_bar_fill" style="position: absolute; right: 30px; bottom: 140px; width: 25px; height: 100px; background: #00ff88; border-radius: 3px; transition: height 0.1s;"></div>
        <div id="vol_text" style="position: absolute; right: 15px; top: 110px; color: #fff; font-family: sans-serif; font-weight: bold; text-shadow: 1px 1px 2px #000;">Vol: 50%</div>
        
        <audio id="bg_music" loop crossorigin="anonymous">
            <source src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" type="audio/mpeg">
        </audio>
        
        <button id="start_btn" style="position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); padding: 20px 40px; font-size: 20px; cursor: pointer; background: #00ff88; border: none; border-radius: 8px; font-weight: bold; color: #000; z-index: 100;">Start Camera and Music</button>
        <div id="loading_msg" style="position: absolute; left: 50%; top: 60%; transform: translate(-50%, -50%); color: #fff; display: none; font-family: sans-serif;">Loading AI Models...</div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>

    <script>
    const videoElement = document.getElementById('input_video');
    const canvasElement = document.getElementById('output_canvas');
    const canvasCtx = canvasElement.getContext('2d');
    const audio = document.getElementById('bg_music');
    const startBtn = document.getElementById('start_btn');
    const loadingMsg = document.getElementById('loading_msg');
    const volFill = document.getElementById('vol_bar_fill');
    const volText = document.getElementById('vol_text');

    let currentVol = 0.5;
    audio.volume = currentVol;

    function onResults(results) {
        canvasCtx.save();
        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
        canvasCtx.drawImage(results.image, 0, 0, canvasElement.width, canvasElement.height);
        
        if (results.multiHandLandmarks) {
            for (const landmarks of results.multiHandLandmarks) {
                drawConnectors(canvasCtx, landmarks, HAND_CONNECTIONS, {color: '#00FF00', lineWidth: 5});
                drawLandmarks(canvasCtx, landmarks, {color: '#FF0000', lineWidth: 2});

                const index = landmarks[8];
                const thumb = landmarks[4];

                const dx = (index.x - thumb.x) * canvasElement.width;
                const dy = (index.y - thumb.y) * canvasElement.height;
                const distance = Math.sqrt(dx*dx + dy*dy);

                let vol = (distance - 30) / (180 - 30);
                vol = Math.max(0, Math.min(1, vol));
                
                currentVol += (vol - currentVol) * 0.3;
                audio.volume = currentVol;

                const volPct = Math.round(currentVol * 100);
                volFill.style.height = (volPct * 2) + 'px';
                volText.innerText = 'Vol: ' + volPct + '%';

                canvasCtx.beginPath();
                canvasCtx.moveTo(thumb.x * canvasElement.width, thumb.y * canvasElement.height);
                canvasCtx.lineTo(index.x * canvasElement.width, index.y * canvasElement.height);
                canvasCtx.strokeStyle = '#fff';
                canvasCtx.lineWidth = 4;
                canvasCtx.stroke();
            }
        }
        canvasCtx.restore();
    }

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

    const camera = new Camera(videoElement, {
        onFrame: async () => {
            await hands.send({image: videoElement});
        },
        width: 640,
        height: 480
    });

    startBtn.onclick = async () => {
        startBtn.style.display = 'none';
        loadingMsg.style.display = 'block';
        try {
            await audio.play();
            await camera.start();
            loadingMsg.style.display = 'none';
        } catch (err) {
            alert("Error starting camera: " + err);
        }
    };
    </script>
    \"\"\",
    height=550,
)

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
