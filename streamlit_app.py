import os
import cv2
import mediapipe as mp
import numpy as np
import streamlit as st
import av
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, AudioProcessorBase, WebRtcMode

# Streamlit App Configuration
st.info("Status: System ready. Connecting to camera...")

# Shared state to communicate between Video and Audio processors
class SharedState:
    def __init__(self):
        self.volume = 1.0

if "shared_state" not in st.session_state:
    st.session_state["shared_state"] = SharedState()
shared_state = st.session_state["shared_state"]

# Pre-load song into memory once to save CPU and reduce networking lag
@st.cache_data
def load_song_to_memory():
    try:
        container = av.open("song.mp3")
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="s16", layout="stereo", rate=48000)
        
        frames = []
        for packet in container.demux(stream):
            for frame in packet.decode():
                r_frames = resampler.resample(frame)
                for r in r_frames:
                    frames.append(r.to_ndarray())
        
        full_audio = np.concatenate(frames, axis=1)
        if full_audio.shape[0] == 1:
            full_audio = np.concatenate([full_audio, full_audio], axis=0)
        return full_audio
    except Exception as e:
        st.error("Music file song.mp3 not found. Please upload one.")
        return None

preloaded_song = load_song_to_memory()

# AI Gesture Processor Logic (Python)
class GestureProcessor(VideoProcessorBase):
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0, # Use fastest model for cloud
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.drawing_utils = mp.solutions.drawing_utils
        self.prev_volume_pct = 50.0
        self.smooth_factor = 0.3
        self._frame_count = 0
        self._last_landmarks = None

    def recv(self, frame):
        image = frame.to_ndarray(format="bgr24")
        image = cv2.flip(image, 1)
        frame_height, frame_width, _ = image.shape

        self._frame_count += 1
        # Skip 2 frames (process every 3rd) for cloud efficiency
        if self._frame_count % 3 == 0:
            small = cv2.resize(image, (160, 120))
            rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            output = self.hands.process(rgb_small)
            self._last_landmarks = output.multi_hand_landmarks

        if self._last_landmarks:
            for hand in self._last_landmarks:
                self.drawing_utils.draw_landmarks(image, hand)
                landmarks = hand.landmark
                thumb, index = landmarks[4], landmarks[8]
                x1, y1 = int(index.x * frame_width), int(index.y * frame_height)
                x2, y2 = int(thumb.x * frame_width), int(thumb.y * frame_height)
                
                cv2.line(image, (x1, y1), (x2, y2), (0, 255, 0), 4)
                dist = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5 // 4
                target_vol = max(0, min(100, (dist - 20) / (150 - 20) * 100))
                self.prev_volume_pct += (target_vol - self.prev_volume_pct) * self.smooth_factor
                shared_state.volume = self.prev_volume_pct / 100.0

        bar_x, bar_y, bar_w, bar_h = 20, 70, 20, 150
        filled = int(bar_h * self.prev_volume_pct / 100)
        cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (200, 200, 200), -1)
        cv2.rectangle(image, (bar_x, bar_y + bar_h - filled), (bar_x + bar_w, bar_y + bar_h), (0, 200, 100), -1)
        cv2.putText(image, f"Vol: {int(self.prev_volume_pct)}%", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return av.VideoFrame.from_ndarray(image, format="bgr24")

class AudioVolumeProcessor(AudioProcessorBase):
    def __init__(self):
        self.song_idx = 0

    def recv(self, frame):
        samples_needed = frame.samples
        if preloaded_song is None or samples_needed <= 0:
            return av.AudioFrame.from_ndarray(np.zeros((2, max(samples_needed, 480)), dtype=np.int16), layout="stereo")

        end_idx = self.song_idx + samples_needed
        if end_idx > preloaded_song.shape[1]:
            self.song_idx = 0
            end_idx = samples_needed
            
        raw_samples = preloaded_song[:, self.song_idx : end_idx]
        self.song_idx = end_idx
        new_samples = (raw_samples * shared_state.volume).astype(np.int16)
        
        new_frame = av.AudioFrame.from_ndarray(new_samples, layout="stereo" if new_samples.shape[0] == 2 else "mono")
        new_frame.sample_rate = 48000
        new_frame.time_base, new_frame.pts = frame.time_base, frame.pts
        return new_frame

# The main WebRTC launcher
webrtc_streamer(
    key="gesture-volume-control",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    video_processor_factory=GestureProcessor,
    audio_processor_factory=AudioVolumeProcessor,
    async_processing=True,
    media_stream_constraints={"video": True, "audio": True}
)

# HTML Method: High-reliability Auto-start script
st.markdown(
    """
    <script>
    const clickStart = () => {
        const buttons = Array.from(window.parent.document.querySelectorAll("button"));
        const btn = buttons.find(b => b.innerText && b.innerText.trim().toLowerCase() === "start");
        if (btn) {
            btn.click();
            console.log("Success: Auto-started the camera.");
            return true;
        }
        return false;
    };
    const interval = setInterval(() => { if (clickStart()) clearInterval(interval); }, 1000);
    setTimeout(() => clearInterval(interval), 40000); // Stop looking after 40 seconds
    </script>
    """,
    unsafe_allow_html=True
)
