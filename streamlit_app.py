import cv2
import mediapipe as mp
import numpy as np
import streamlit as st
import av
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, AudioProcessorBase, WebRtcMode, MediaPlayer

# Title and description
st.title("Hand Gesture Volume Control 🎵")
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
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.drawing_utils = mp.solutions.drawing_utils
        self.prev_volume_pct = 50.0 # 0-100 scale for display
        self.smooth_factor = 0.3

    def recv(self, frame):
        image = frame.to_ndarray(format="bgr24")
        
        # Mirror and process
        image = cv2.flip(image, 1)
        frame_height, frame_width, _ = image.shape
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        output = self.hands.process(rgb_image)
        hands_landmarks = output.multi_hand_landmarks

        x1 = y1 = x2 = y2 = 0
        
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

                cv2.line(image, (x1, y1), (x2, y2), (0, 255, 0), 5)
                
                # Distance calculation
                dist = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5 // 4
                
                # Calculate target volume (0-100)
                target_vol = max(0, min(100, (dist - 20) / (150 - 20) * 100))
                
                # Smoothing
                self.prev_volume_pct += (target_vol - self.prev_volume_pct) * self.smooth_factor
                
                # Update shared state (0.0 - 1.0)
                shared_state.volume = self.prev_volume_pct / 100.0

        # Display Volume
        cv2.putText(
            image,
            f"Volume: {int(self.prev_volume_pct)}%",
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 0),
            4,
        )

        return av.VideoFrame.from_ndarray(image, format="bgr24")

class AudioVolumeProcessor(AudioProcessorBase):
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        # Convert audio to numpy array
        # Audio is typically separate planar or packed.
        # We need to handle different layouts, but typically simpler to just multiply using valid numpy types.
        
        # Convert to numpy (int16 or float32 depending on source)
        raw_samples = frame.to_ndarray()
        
        # Apply volume
        new_samples = (raw_samples * shared_state.volume).astype(raw_samples.dtype)
        
        # Create new frame
        new_frame = av.AudioFrame.from_ndarray(new_samples, layout=frame.layout.name)
        new_frame.sample_rate = frame.sample_rate
        new_frame.time_base = frame.time_base
        new_frame.pts = frame.pts
        return new_frame

# Setup Media Player
# Note: 'song.mp3' must be locally available
try:
    player = MediaPlayer("song.mp3")
except Exception as e:
    st.error(f"Could not load song.mp3: {e}")
    player = None

if player:
    webrtc_streamer(
        key="gesture-volume",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        video_processor_factory=GestureProcessor,
        audio_processor_factory=AudioVolumeProcessor,
        source_audio=player,
    )
