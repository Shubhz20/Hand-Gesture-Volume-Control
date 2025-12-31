# Gesture Computer Control

A Python application that uses hand gestures to control computer volume on macOS. The application tracks hand movements using MediaPipe and adjusts system volume based on the distance between thumb and index finger.

## Features

- Real-time hand tracking using MediaPipe
- Volume control based on thumb and index finger distance
- Visual feedback with hand landmarks and volume display
- macOS system volume integration

## Requirements

- Python 3.9
- macOS (for volume control functionality)
- Webcam

## Installation

1. Clone the repository:
```
git clone <repository-url>
cd gesture-computer-control
```

2. Create a virtual environment:
```
python3.9 -m venv venv39
source venv39/bin/activate
```

3. Install dependencies:
```
pip install opencv-python mediapipe pyautogui numpy
```

## Usage

Run the application:
```
python HandTrackingMin.py
```

- Position your hand in front of the webcam
- Adjust the distance between your thumb and index finger to control volume
- Press ESC to exit

## How It Works

The application uses MediaPipe to detect hand landmarks. It calculates the distance between the thumb tip (landmark 4) and index finger tip (landmark 8) to determine the volume level. The volume is adjusted in real-time based on this distance.

## Dependencies

- opencv-python
- mediapipe
- pyautogui
- numpy

