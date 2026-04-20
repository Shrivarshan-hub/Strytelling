import cv2
import time
import os
import datetime
from tracker.vision_tracker import VisionTracker
from tracker.app_tracker import AppTracker
from logic.intelligence import StateLogic
from db.database import Database

def main():
    print("[*] Initializing FocusLens Modules...")
    vision_tracker = VisionTracker()
    app_tracker = AppTracker()
    # 5 frames smoothing (approx 0.5 - 1 second to avoid flickering states)
    logic = StateLogic(smoothing_window=5)
    
    db = Database()
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    if not cap.isOpened():
        print("\n" + "="*50)
        print("[!] CRITICAL ERROR: Could NOT open the webcam.")
        print("[!] Your camera is actively BLOCKED by another background Terminal!")
        print("[!] Please check your terminal tabs in VS Code and hit the trash can icon on all of them.")
        print("="*50 + "\n")
        time.sleep(5)
        return

    # Ensure camera resolution is adequate but lightweight
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    session_start = time.time()
    last_db_save = time.time()
    last_eval_time = time.time()
    
    # Session Constraints
    MAX_SESSION_DURATION = 3600 # 1 hour Max
    
    # Data Storage (Memory)
    logs_memory = []
    
    # Exact Time Trackers (Timestamp driven)
    focus_time = 0.0
    distraction_time = 0.0
    absence_time = 0.0
    
    # Cache / Process Skipping
    frame_counter = 0
    cached_process_name = "unknown"
    cached_app_category = "UNKNOWN"
    cached_face_status = "ABSENT"
    cached_attention_state = "UNKNOWN"
    cached_overall_status = "UNKNOWN"
    cached_ear = 0.0
    
    print("[*] FocusLens Active! Press 'ESC' or 'q' to exit.")
    
    try:
        while True:
            # 1. Graceful Exit Check
            if os.path.exists("stop_flag.txt"):
                print("[*] Stop signal received from Dashboard. Terminating...")
                break
                
            current_time = time.time()
            if (current_time - session_start) >= MAX_SESSION_DURATION:
                print("[*] Maximum session duration reached. Auto-saving...")
                break

            ret, frame = cap.read()
            if not ret:
                print("[!] ERROR: Failed to read from webcam.")
                break
                
            frame_counter += 1
            
            # 2. Performance Optimization: Skip full process every other frame
            if frame_counter % 2 != 0:
                frame, face_status, attention_state, ear = vision_tracker.process_frame(frame)
                cached_face_status = face_status
                cached_attention_state = attention_state
                cached_ear = ear
                
                process_name, window_title, app_category = app_tracker.get_active_window()
                cached_process_name = process_name
                cached_app_category = app_category
                
                cached_overall_status = logic.determine_status(cached_app_category, cached_face_status, cached_attention_state)
            
            # 3. Exact Time Tracking
            dt = current_time - last_eval_time
            last_eval_time = current_time
            
            if cached_overall_status == "TRUE FOCUS":
                focus_time += dt
            elif cached_overall_status in ["DISTRACTION", "FAKE STUDY"]:
                distraction_time += dt
            elif cached_overall_status in ["ABSENT", "DROWSY"]:
                absence_time += dt
                
            # 4. Data Storage in Memory (1 Log Every Second)
            if current_time - last_db_save >= 1.0:
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logs_memory.append((now_str, cached_process_name, cached_app_category, cached_face_status, cached_attention_state, cached_overall_status))
                last_db_save = current_time
                
            # 5. Real-Time UI Overlay Construction
            session_time = int(current_time - session_start)
            
            cv2.putText(frame, f"Session Time: {session_time // 60}m {session_time % 60}s", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, f"App: [{cached_app_category}] {cached_process_name}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            cv2.putText(frame, f"Face: {cached_face_status} | Look: {cached_attention_state}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            status_color = (0, 255, 0)
            if cached_overall_status in ["FAKE STUDY", "DISTRACTION"]:
                status_color = (0, 0, 255)
            elif cached_overall_status in ["ABSENT", "DROWSY"]:
                status_color = (0, 165, 255)
            elif cached_overall_status == "NEUTRAL FOCUS":
                status_color = (255, 200, 0) 
                
            cv2.putText(frame, f"FOCUS STATUS: {cached_overall_status}", (20, 140), cv2.FONT_HERSHEY_DUPLEX, 0.8, status_color, 2)
            
            if cached_overall_status == "DROWSY":
                cv2.putText(frame, "ALERT: You appear Drowsy!", (20, 180), cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 0, 255), 2)
            if cached_overall_status == "DISTRACTION":
                cv2.putText(frame, "ALERT: Distraction Detected", (20, 180), cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 0, 255), 2)
            if cached_overall_status == "FAKE STUDY":
                cv2.putText(frame, "ALERT: Please look at the screen", (20, 180), cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 165, 255), 2)

            cv2.imshow("FocusLens Live Tracker", frame)
            
            key = cv2.waitKey(1)
            if key == 27 or key == ord('q'):
                break

    except Exception as e:
        print(f"[!] ENCOUNTERED CRITICAL ERROR: {e}")
        
    finally:
        # 6. Finalize and Save Operations
        print(f"[*] Finalizing session. Saving {len(logs_memory)} logged frames...")
        if len(logs_memory) > 0:
            db.insert_bulk_logs(logs_memory)
        
        actual_total_duration = time.time() - session_start
        if actual_total_duration > 0 and len(logs_memory) > 0:
            db.save_session_exact(actual_total_duration, focus_time, distraction_time, absence_time)
            
        print("[*] Releasing resources and shutting down...")
        if cap.isOpened():
            cap.release()
        cv2.destroyAllWindows()
        db.close()
        
        if os.path.exists("stop_flag.txt"):
            os.remove("stop_flag.txt")
            
        print("[*] Tracking session ended cleanly.")

if __name__ == "__main__":
    main()
