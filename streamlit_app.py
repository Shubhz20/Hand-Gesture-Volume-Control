import cv2
import math
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
from mediapipe import solutions as mp_solutions

# ---------------- UI ----------------
st.set_page_config(page_title="Gesture Volume Controller")
st.title("🎵 Gesture Volume Controller")
st.write("Pinch your fingers to change volume")

audio_container = st.empty()
volume_text = st.empty()

# Play uploaded song
audio_container.audio("song.mp3")

# ------------- MediaPipe -------------
mp_hands = mp_solutions.hands
mp_draw = mp_solutions.drawing_utils


# ------------ HAND + VOLUME LOGIC (YOUR LOGIC) ------------
class HandVolumeProcessor(VideoProcessorBase):
    def __init__(self):
        self.volume = 0.5

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        with mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        ) as hands:

            result = hands.process(rgb)

            if result.multi_hand_landmarks:
                hand = result.multi_hand_landmarks[0]
                mp_draw.draw_landmarks(img, hand, mp_hands.HAND_CONNECTIONS)

                h, w, _ = img.shape
                x1 = int(hand.landmark[8].x * w)   # index tip
                y1 = int(hand.landmark[8].y * h)
                x2 = int(hand.landmark[4].x * w)   # thumb tip
                y2 = int(hand.landmark[4].y * h)

                # SAME DISTANCE LOGIC
                dist = math.sqrt((x2-x1)**2 + (y2-y1)**2) // 4

                # SAME VOLUME MAPPING
                self.volume = max(0, min(1, (dist - 30) / (200 - 30)))

                cv2.line(img, (x1, y1), (x2, y2), (0, 255, 0), 5)
                cv2.putText(
                    img,
                    f"Volume: {int(self.volume * 100)}%",
                    (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 0),
                    4
                )

        return img


# ------------ WEBRTC STREAM ------------
ctx = webrtc_streamer(
    key="gesture-volume",
    video_processor_factory=HandVolumeProcessor
)

# ------------ DISPLAY VOLUME ------------
if ctx.video_processor:
    vol = int(ctx.video_processor.volume * 100)
    volume_text.markdown(f"### 🔊 Current Volume: **{vol}%**")
