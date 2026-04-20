import cv2
import mediapipe as mp
import os
import urllib.request
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# The newer MediaPipe tasks API requires a downloaded model file
MODEL_PATH = "blaze_face_short_range.tflite"
if not os.path.exists(MODEL_PATH):
    print("Downloading MediaPipe face detection model...")
    url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite"
    urllib.request.urlretrieve(url, MODEL_PATH)
    print("Download complete.")

# Initialize the FaceDetector using the modern Tasks API
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.FaceDetectorOptions(base_options=base_options)
detector = vision.FaceDetector.create_from_options(options)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
        
    # Convert BGR to RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Convert to MediaPipe Image format
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    # Detect faces
    result = detector.detect(mp_image)

    if result.detections:
        print("PRESENT")
    else:
        print("ABSENT")

    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()