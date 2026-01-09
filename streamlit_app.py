import cv2
import mediapipe as mp
import numpy as np
import streamlit as st
import av
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase

# Title and description
st.title("Hand Gesture Volume Control")

class GestureProcessor(VideoProcessorBase):
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.drawing_utils = mp.solutions.drawing_utils
        self.prev_volume = 0
        self.smooth_factor = 0.5

    def recv(self, frame):
        image = frame.to_ndarray(format="bgr24")
        
        # Mirror image
        image = cv2.flip(image, 1)
        frame_height, frame_width, _ = image.shape

        # Process hand landmarks
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        output = self.hands.process(rgb_image)
        hands_landmarks = output.multi_hand_landmarks

        x1 = y1 = x2 = y2 = 0
        
        if hands_landmarks:
            for hand in hands_landmarks:
                self.drawing_utils.draw_landmarks(image, hand)
                landmarks = hand.landmark
                
                # We need landmarks for thumb (4) and index finger (8)
                # But iterating typically gives us normalized coordinates.
                # We need pixel coordinates.
                
                # Get coordinates for thumb tip (4) and index tip (8)
                thumb = landmarks[4]
                index = landmarks[8]
                
                x1 = int(index.x * frame_width)
                y1 = int(index.y * frame_height)
                
                x2 = int(thumb.x * frame_width)
                y2 = int(thumb.y * frame_height)

                # Draw line between them
                cv2.line(image, (x1, y1), (x2, y2), (0, 255, 0), 5)
                
                # Calculate distance
                dist = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5 // 4
                
                # Convert to volume scale
                volume = max(0, min(100, (dist - 30) / (200 - 30) * 100))
                
                # Smoothing
                self.prev_volume += (volume - self.prev_volume) * self.smooth_factor

        # Display Volume on screen
        cv2.putText(
            image,
            f"Volume: {int(self.prev_volume)}%",
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 0),
            4,
        )

        return av.VideoFrame.from_ndarray(image, format="bgr24")

webrtc_streamer(
    key="gesture-control",
    video_processor_factory=GestureProcessor,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)
