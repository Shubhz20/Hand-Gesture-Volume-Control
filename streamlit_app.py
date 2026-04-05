import os
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"
os.environ["MESA_GL_VERSION_OVERRIDE"] = "3.3"
os.environ["GLOG_minloglevel"] = "2"  # Suppresses the EGL/GPU C++ warnings


import cv2
import mediapipe as mp
import numpy as np
import streamlit as st
import av
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, AudioProcessorBase, WebRtcMode


# Title and description
st.title("Hand Gesture Volume Control")
st.markdown(
    """
    **Instructions:**
    1. Click "Start" to open the camera and play music.
    2. Show your hand. Pinch thumb and index finger to change volume.
    3. The music is streamed from the server and volume is applied in real-time Python code!
    """
)

# Shared state to communicate between Video and Audio processors
class SharedState:
    def __init__(self):
        self.volume = 1.0  # 0.0 to 1.0

if "shared_state" not in st.session_state:
    st.session_state["shared_state"] = SharedState()

shared_state = st.session_state["shared_state"]

class GestureProcessor(VideoProcessorBase):
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.drawing_utils = mp.solutions.drawing_utils
        self.prev_volume_pct = 50.0
        self.smooth_factor = 0.3
        self._frame_count = 0
        self._last_landmarks = None

    def recv_queued(self, frames):
        output_frames = []
        for frame in frames:
            image = frame.to_ndarray(format="bgr24")
            image = cv2.flip(image, 1)
            frame_height, frame_width, _ = image.shape

            self._frame_count += 1
            if self._frame_count % 2 == 0:
                small = cv2.resize(image, (160, 120))
                rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                output = self.hands.process(rgb_small)
                self._last_landmarks = output.multi_hand_landmarks

            hands_landmarks = self._last_landmarks

            if hands_landmarks:
                for hand in hands_landmarks:
                    self.drawing_utils.draw_landmarks(image, hand)
                    landmarks = hand.landmark

                    thumb = landmarks[4]
                    index = landmarks[8]

                    x1 = int(index.x * frame_width)
                    y1 = int(index.y * frame_height)
                    x2 = int(thumb.x * frame_width)
                    y2 = int(thumb.y * frame_height)

                    cv2.line(image, (x1, y1), (x2, y2), (0, 255, 0), 4)

                    dist = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5 // 4
                    target_vol = max(0, min(100, (dist - 20) / (150 - 20) * 100))
                    self.prev_volume_pct += (target_vol - self.prev_volume_pct) * self.smooth_factor
                    shared_state.volume = self.prev_volume_pct / 100.0

            bar_x, bar_y, bar_w, bar_h = 20, 70, 20, 150
            filled = int(bar_h * self.prev_volume_pct / 100)
            cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (200, 200, 200), -1)
            cv2.rectangle(image, (bar_x, bar_y + bar_h - filled), (bar_x + bar_w, bar_y + bar_h), (0, 200, 100), -1)
            cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), 2)

            cv2.putText(image, f"Vol: {int(self.prev_volume_pct)}%", (10, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            output_frames.append(av.VideoFrame.from_ndarray(image, format="bgr24"))
        return output_frames

# --- PRELOAD SONG ONCE INTO MEMORY TO SAVE CPU ---
@st.cache_data
def load_song_to_memory():
    print("Pre-decoding full song into RAM to prevent thread starvation...")
    try:
        container = av.open("song.mp3")
        stream = container.streams.audio[0]
        # Target standard WebRTC parameters: s16, stereo, 48000Hz
        resampler = av.AudioResampler(format="s16", layout="stereo", rate=48000)
        
        frames = []
        for packet in container.demux(stream):
            for frame in packet.decode():
                r_frames = resampler.resample(frame)
                for r in r_frames:
                    frames.append(r.to_ndarray())
        # Concatenate all frames along the time axis (axis=1)
        full_audio = np.concatenate(frames, axis=1)
        print(f"Song loaded! Shape: {full_audio.shape}")
        return full_audio
    except Exception as e:
        print("Error pre-loading song:", e)
        return None

preloaded_song = load_song_to_memory()

class AudioVolumeProcessor(AudioProcessorBase):
    def __init__(self):
        self.song_idx = 0

    def recv_queued(self, frames):
        output_frames = []
        for frame in frames:
            samples_needed = frame.samples
            
            # If song failed to load or frame is malformed, return silent padding
            if preloaded_song is None or samples_needed <= 0:
                silent_frame = av.AudioFrame.from_ndarray(
                    np.zeros((2, max(samples_needed, 480)), dtype=np.int16),
                    layout="stereo"
                )
                silent_frame.sample_rate = 48000
                silent_frame.time_base = frame.time_base
                silent_frame.pts = frame.pts
                output_frames.append(silent_frame)
                continue

            end_idx = self.song_idx + samples_needed
            
            # If we reached the end of the song, loop back
            if end_idx > preloaded_song.shape[1]:
                self.song_idx = 0
                end_idx = samples_needed
                
            raw_samples = preloaded_song[:, self.song_idx : end_idx]
            self.song_idx = end_idx
            
            # Safe multiplication for volume
            new_samples = (raw_samples * shared_state.volume).astype(np.int16)

            new_frame = av.AudioFrame.from_ndarray(new_samples, layout="stereo")
            new_frame.sample_rate = 48000
            new_frame.time_base = frame.time_base
            new_frame.pts = frame.pts
            output_frames.append(new_frame)
            
        return output_frames

webrtc_streamer(
    key="gesture-volume",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration={
        "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
    },
    video_processor_factory=GestureProcessor,
    audio_processor_factory=AudioVolumeProcessor,
    media_stream_constraints={"video": True, "audio": True},
    async_processing=True,
)
