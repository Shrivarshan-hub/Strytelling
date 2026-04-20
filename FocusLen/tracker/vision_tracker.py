import cv2
import mediapipe as mp
import numpy as np
import os
import urllib.request
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class VisionTracker:
    def __init__(self):
        MODEL_PATH = "tracker/face_landmarker.task"
        if not os.path.exists(MODEL_PATH):
            url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
            urllib.request.urlretrieve(url, MODEL_PATH)

        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=True,
            num_faces=1
        )
        self.detector = vision.FaceLandmarker.create_from_options(options)

        self.model_points = np.array([
            (0.0, 0.0, 0.0),             
            (0.0, -330.0, -65.0),        
            (-225.0, 170.0, -135.0),     
            (225.0, 170.0, -135.0),      
            (-150.0, -150.0, -125.0),    
            (150.0, -150.0, -125.0)      
        ])
        
        # Timer state for accurate drowsiness
        self.eyes_closed_start_time = None
    
    def process_frame(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        results = self.detector.detect(mp_image)
        
        face_status = "ABSENT"
        attention_state = "UNKNOWN"
        ear = 0.0
        
        if results.face_landmarks:
            face_status = "PRESENT"
            for face_landmarks in results.face_landmarks:
                img_h, img_w, _ = frame.shape
                
                image_pts = np.array([
                    (face_landmarks[1].x * img_w, face_landmarks[1].y * img_h),     
                    (face_landmarks[152].x * img_w, face_landmarks[152].y * img_h), 
                    (face_landmarks[33].x * img_w, face_landmarks[33].y * img_h),   
                    (face_landmarks[263].x * img_w, face_landmarks[263].y * img_h), 
                    (face_landmarks[61].x * img_w, face_landmarks[61].y * img_h),   
                    (face_landmarks[291].x * img_w, face_landmarks[291].y * img_h)  
                ], dtype="double")
                
                focal_length = 1 * img_w
                cam_matrix = np.array([
                    [focal_length, 0, img_w / 2],
                    [0, focal_length, img_h / 2],
                    [0, 0, 1] 
                ])
                dist_matrix = np.zeros((4, 1), dtype=np.float64)
                
                success, rot_vec, trans_vec = cv2.solvePnP(self.model_points, image_pts, cam_matrix, dist_matrix)
                rmat, _ = cv2.Rodrigues(rot_vec)
                angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
                
                x_angle = angles[0] 
                y_angle = angles[1] 
                
                # Check Face yaw constraints
                if y_angle < -18 or y_angle > 18:
                    attention_state = "DISTRACTED"
                else:
                    attention_state = "FOCUSED"
                    
                left_eye_pts = [362, 385, 387, 263, 373, 380]
                right_eye_pts = [33, 160, 158, 133, 153, 144]
                
                def get_ear(eye_pts):
                    pts = [np.array([face_landmarks[p].x * img_w, face_landmarks[p].y * img_h]) for p in eye_pts]
                    v1 = np.linalg.norm(pts[1] - pts[5])
                    v2 = np.linalg.norm(pts[2] - pts[4])
                    h = np.linalg.norm(pts[0] - pts[3])
                    return (v1 + v2) / (2.0 * h) if h > 0 else 0
                    
                ear_left = get_ear(left_eye_pts)
                ear_right = get_ear(right_eye_pts)
                ear = (ear_left + ear_right) / 2.0
                
                # STRICT 3 SECONDS RULE FOR DROWSINESS
                if ear < 0.22:
                    if self.eyes_closed_start_time is None:
                        self.eyes_closed_start_time = time.time()
                    elif (time.time() - self.eyes_closed_start_time) >= 3.0:
                        attention_state = "DROWSY"
                else:
                    self.eyes_closed_start_time = None
                    
        else:
            face_status = "ABSENT"
            attention_state = "ABSENT"
            self.eyes_closed_start_time = None
            
        return frame, face_status, attention_state, ear
