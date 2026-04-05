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
            static_image_mode=False,
            max_num_hands=1,          # Only track 1 hand — faster
            model_complexity=0,       # Lightest model
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.drawing_utils = mp.solutions.drawing_utils
        self.prev_volume_pct = 50.0
        self.smooth_factor = 0.3
        self._frame_count = 0
        self._last_landmarks = None   # Cache last result for skipped frames

    def recv(self, frame):
        image = frame.to_ndarray(format="bgr24")
        image = cv2.flip(image, 1)
        frame_height, frame_width, _ = image.shape

        self._frame_count += 1

        # Process MediaPipe only every 2nd frame to halve CPU load
        if self._frame_count % 2 == 0:
            # Downscale for faster inference, then map coords back
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

        # Draw volume bar
        bar_x, bar_y, bar_w, bar_h = 20, 70, 20, 150
        filled = int(bar_h * self.prev_volume_pct / 100)
        cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (200, 200, 200), -1)
        cv2.rectangle(image, (bar_x, bar_y + bar_h - filled), (bar_x + bar_w, bar_y + bar_h), (0, 200, 100), -1)
        cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), 2)

        cv2.putText(
            image,
            f"Vol: {int(self.prev_volume_pct)}%",
            (10, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        return av.VideoFrame.from_ndarray(image, format="bgr24")

class AudioVolumeProcessor(AudioProcessorBase):
    def __init__(self):
        self.container = av.open("song.mp3")
        self.stream = self.container.streams.audio[0]
        self.packet_generator = self.container.decode(self.stream)
        self.resampler = None
        self.fifo = av.AudioFifo()

    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        # Initialize resampler once we know the target format from the first incoming frame
        if self.resampler is None:
            self.resampler = av.AudioResampler(
                format=frame.format.name,
                layout=frame.layout.name,
                rate=frame.sample_rate,
            )

        samples_needed = frame.samples
        
        while self.fifo.samples < samples_needed:
            try:
                song_frame = next(self.packet_generator)
            except StopIteration:
                # Loop the song: seek to beginning
                self.container.seek(0)
                self.packet_generator = self.container.decode(self.stream)
                song_frame = next(self.packet_generator)
            except Exception:
                break

            resampled_frames = self.resampler.resample(song_frame)
            if resampled_frames:
                self.fifo.write(resampled_frames[0])

        if self.fifo.samples >= samples_needed:
            output_frame = self.fifo.read(samples_needed)
            
            # Apply Volume
            raw_samples = output_frame.to_ndarray()
            
            # Safe multiplication for volume
            if raw_samples.dtype.kind == 'i':
                new_samples = (raw_samples * shared_state.volume).astype(raw_samples.dtype)
            elif raw_samples.dtype.kind == 'f':
                 new_samples = (raw_samples * shared_state.volume).astype(raw_samples.dtype)
            else:
                 new_samples = raw_samples

            new_frame = av.AudioFrame.from_ndarray(new_samples, layout=frame.layout.name)
            new_frame.sample_rate = frame.sample_rate
            new_frame.time_base = frame.time_base
            new_frame.pts = frame.pts
            return new_frame
        
        else:
            return av.AudioFrame.from_ndarray(
                np.zeros((frame.layout.channels, samples_needed), dtype=frame.to_ndarray().dtype),
                layout=frame.layout.name
            )

webrtc_streamer(
    key="gesture-volume",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    video_processor_factory=GestureProcessor,
    audio_processor_factory=AudioVolumeProcessor,
    media_stream_constraints={
        "video": {
            "width": {"ideal": 320},
            "height": {"ideal": 240},
            "frameRate": {"ideal": 15}
        }, 
        "audio": True
    },
    async_processing=True,
)
