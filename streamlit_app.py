import streamlit as st
import cv2
import mediapipe as mp
import math
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase

st.title("🎵 Hand Gesture Volume Controller (Web Demo)")

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
draw = mp.solutions.drawing_utils


class Processor(VideoProcessorBase):
    def __init__(self):
        self.volume = 0.3

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        result = hands.process(rgb)

        x1 = y1 = x2 = y2 = 0

        if result.multi_hand_landmarks:
            hand = result.multi_hand_landmarks[0]
            draw.draw_landmarks(img, hand, mp_hands.HAND_CONNECTIONS)

            h, w, _ = img.shape
            for i, lm in enumerate(hand.landmark):
                x, y = int(lm.x * w), int(lm.y * h)

                if i == 8:  # index
                    x1, y1 = x, y
                if i == 4:  # thumb
                    x2, y2 = x, y

            dist = math.dist((x1, y1), (x2, y2))

            # map to 0–1 volume range
            self.volume = max(0, min(1, (dist - 30) / (200 - 30)))

        return img


stream = webrtc_streamer(key="gesture")

if stream.video_processor:
    st.write("✋ Move fingers to change volume")

    st.session_state.volume = stream.video_processor.volume

    # browser music player
    st.audio("song.mp3", start_time=0)
    st.write(f"🔊 Volume level: **{round(st.session_state.volume,2)}**")
