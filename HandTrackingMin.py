import cv2
import mediapipe as mp
import pyautogui
import math
import subprocess

#initialize distance
x1=y1=x2=y2=0

#To Link Volume
def set_volume_mac(volume):
    volume=max(0,min(100,int(volume)))
    subprocess.call(["osascript","-e",f"set volume output volume {volume}"])

#To detect and track hands
my_hands =mp.solutions.hands.Hands()
drawing_utils = mp.solutions.drawing_utils

#To Capture Video
webcam = cv2.VideoCapture(0)
prev_volume=0
smooth_factor=1
set_volume_mac(prev_volume)

while True:
    ret, image = webcam.read()
    if not ret:
        break

    image=cv2.flip(image,1)
    frame_height,frame_width, _ = image.shape

    rgb_image=cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
    output = my_hands.process(rgb_image)
    hands= output.multi_hand_landmarks
    if hands:
        for hand in hands:
            drawing_utils.draw_landmarks(image,hand)
            landmarks= hand.landmark
            for id,landmark in enumerate(landmarks):
                x= int(landmark.x * frame_width)
                y= int(landmark.y * frame_height)
                if id==8:
                    cv2.circle(img=image,center=(x,y),radius=8,color=(0,255,255),thickness=3)
                    x1=x
                    y1=y
                if id==4:
                    cv2.circle(img=image,center=(x,y),radius=8,color=(0,0,255),thickness=3)
                    x2=x
                    y2=y

    #To find distance between thumb and indexfinger
    dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** (0.5) // 4

    volume = max(0, min(100, (dist - 30) / (200 - 30) * 100))
    prev_volume += (volume - prev_volume) * smooth_factor
    set_volume_mac(prev_volume)
    cv2.putText(image, f"Volume: {int(prev_volume)}%", (20, 50),
    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 4)

    cv2.line(image,(x1,y1),(x2,y2),(0,255,0),5)

    #conditions
    if dist >50:
        pyautogui.press("volumeup")
    else:
        pyautogui.press("volumedown")

    cv2.imshow('Gesture Control', image)

    key=cv2.waitKey(10)
    if key ==27:
        break


webcam.release()
cv2.destroyAllWindows()