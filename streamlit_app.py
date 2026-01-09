import streamlit as st
import mediapipe as mp
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
import av

st.set_page_config(page_title="Gesture Volume Control")
st.title("Gesture Volume Controller 🎵")
st.caption("Streamlit Demo (Web-safe)")

# --------- MediaPipe setup ----------
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

class HandProcessor(VideoProcessorBase):
    def __init__(self):
        self.hands = mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.volume = 0

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        rgb = img[:, :, ::-1]
        result = self.hands.process(rgb)

        if result.multi_hand_landmarks:
            hand = result.multi_hand_landmarks[0]
            mp_draw.draw_landmarks(img, hand)

            h, w, _ = img.shape
            x1 = y1 = x2 = y2 = 0

            for i, lm in enumerate(hand.landmark):
                x, y = int(lm.x * w), int(lm.y * h)
                if i == 8:
                    x1, y1 = x, y
                if i == 4:
                    x2, y2 = x, y

            dist = np.hypot(x2 - x1, y2 - y1)
            self.volume = int(np.clip((dist - 30) / 170 * 100, 0, 100))

            img = cv2.line(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
            img = cv2.putText(
                img,
                f"Volume: {self.volume}%",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 0),
                3,
            )

        return av.VideoFrame.from_ndarray(img, format="bgr24")

# --------- WebRTC Camera ----------
ctx = webrtc_streamer(
    key="gesture",
    video_processor_factory=HandProcessor,
    media_stream_constraints={"video": True, "audio": False},
)

# --------- Audio Player ----------
st.subheader("🎧 Test Audio")

audio_file = open("song.mp3", "rb")
st.audio(audio_file.read(), format="audio/mp3")

if ctx.video_processor:
    st.metric("Detected Volume", f"{ctx.video_processor.volume}%")
