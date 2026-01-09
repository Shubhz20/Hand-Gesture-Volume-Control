import cv2
import mediapipe as mp
import numpy as np
import streamlit as st
import av
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, AudioProcessorBase, WebRtcMode
from aiortc.contrib.media import MediaPlayer

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
    def __init__(self):
        self.container = av.open("song.mp3")
        self.stream = self.container.streams.audio[0]
        self.packet_generator = self.container.decode(self.stream)
        self.resampler = None

    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        # Lazy initialization of resampler based on the client's requested format (usually 48kHz, stereo)
        if self.resampler is None:
            self.resampler = av.AudioResampler(
                format=frame.format.name,
                layout=frame.layout.name,
                rate=frame.sample_rate,
            )

        try:
            # Read next audio frame from the file
            song_frame = next(self.packet_generator)
        except StopIteration:
            # Loop: seek to start and continue
            self.container.seek(0)
            # Re-create generator/decoder context
            self.packet_generator = self.container.decode(self.stream)
            song_frame = next(self.packet_generator)
        
        # Determine how many "frames" (time) we need to fill to match input frame
        # Actually, best effort: we just resample the song_frame to match target characteristics.
        # Note: Input frame 'frame' drives the timing. We want to output similar duration.
        
        # Resample the song frame to match input constraints
        resampled_frames = self.resampler.resample(song_frame)
        
        # 'resampled_frames' is a list of frames (usually 1 if sizes match well).
        # We take the first one. If empty, we might need to pull more, but simplistic approach first.
        if not resampled_frames:
             # Just return silent frame if we missed a beat
             return frame
        
        output_frame = resampled_frames[0]
        
        # Convert to numpy to apply volume
        raw_samples = output_frame.to_ndarray()
        
        # Apply volume from shared state
        # Ensure we don't overflow if using integers
        if raw_samples.dtype.kind == 'i':
             # integer types
             new_samples = (raw_samples * shared_state.volume).astype(raw_samples.dtype)
        else:
             # float types
             new_samples = (raw_samples * shared_state.volume).astype(raw_samples.dtype)
             
        # Pack back into AudioFrame
        new_frame = av.AudioFrame.from_ndarray(new_samples, layout=output_frame.layout.name)
        new_frame.sample_rate = output_frame.sample_rate
        new_frame.time_base = output_frame.time_base
        new_frame.pts = frame.pts # Sync PTS with the input 'clock' from Mic
        
        return new_frame

# We removed "source_audio=player" to avoid TypeError.
# The user MUST allow Microphone for this to work (it acts as the clock).
webrtc_streamer(
    key="gesture-volume",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    video_processor_factory=GestureProcessor,
    audio_processor_factory=AudioVolumeProcessor,
    media_stream_constraints={"video": True, "audio": True}, # Request Mic!
)
