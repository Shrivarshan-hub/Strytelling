# 🔍 FocusLens - A - Z Project Documentation

FocusLens is an intelligent, real-time attention-tracking and desktop productivity monitoring system. It leverages Computer Vision (via MediaPipe) alongside OS-level Application Tracking to guarantee that a user is genuinely studying or working—catching instances of drowsiness, physical distraction, and digital distraction securely on the local device.

---

## 🏗️ 1. Complete Architecture Overview

The system is constructed with a modular split between the active Tracker (running OpenCV/AI) and the Dashboard/API Control layer. 

### Core Modules

* **`main.py` (The Engine)**
  This script drives the core tracking loop. It instantiates the camera feed and evaluates both the user's face and their active computer applications. It manages time-tracking variables (timestamp-based), stores tracking history in local RAM to prevent database locking/lag, and writes final analytics to SQLite once the session stops.
  - **Auto-Safety Built-In:** Capable of safely auto-saving and aborting a tracking session if active for over 1 hour.
  - **Frame Skipping:** To save CPU headroom, full AI inference logic acts strictly every alternate processing frame.

* **`app.py` (Flask Web Dashboard Server)**
  This is the web-server layer serving the user interface and REST API. 
  - **Functionality:** Listens to `/start_tracking` and `/stop_tracking` HTTP requests, dynamically triggering or cleanly halting `main.py` utilizing a flag-file (`stop_flag.txt`) for graceful process stopping.
  - Generates real-time statistics (`/get_analysis`) and allows querying of prior history (`/get_history`).
  - Supports CSV extraction for data exports.

* **`tracker/vision_tracker.py`**
  Handles visual verification natively over frames grabbed via OpenCV.
  - Leverages heavily optimized **MediaPipe Face Landmarker API**. 
  - Calculates Head Pose mapping (SolvePnP) to confirm if Yaw angles suggest a user is gazing closely at the monitor.
  - Calculates Eye Aspect Ratio (EAR) mapping over a 3-second strict allowance queue to detect deep *Drowsiness*.

* **`tracker/app_tracker.py`**
  Handles digital verification using local Windows API libraries (`win32gui`, `win32process`, `psutil`). 
  - Continuously scrapes the Foreground window the user is physically interacting with.
  - Compares the process executable (`.exe`) and active window name text against Hardcoded dictionaries of "STUDY_APPS" or "DISTRACTING_APPS".

* **`logic/intelligence.py`**
  Operates as the fusion engine logic that judges the combination of both physical and digital attributes. Extrapolates statuses like:
  - **TRUE FOCUS**: Active application is a Study app AND Face is focused forward.
  - **FAKE STUDY**: Active application is a Study app BUT user's Face is looking away continuously.
  - **DISTRACTION**: Application is marked distracting (Spotify, Steam, Discord), immediately overpowering Face metrics. 
  - Utilizes a Deque (Frame smoothing cache) to debounce rapid flashes between logic changes and ensure consistent output.

* **`db/database.py`**
  The interface interacting natively with Python's generalized SQLite3 libraries. 
  - Spawns and manages `focuslens.db`.
  - Configured into dual table architecture: 
    1. `focus_log` (Receives active session telemetry directly).
    2. `focus_sessions` (Condenses telemetry into singular history reports alongside accuracy scores).
  - Handles **Bulk Inserts** for zero-stutter performance.

* **`dashboard/app.py` (Streamlit Analytics [Secondary UI])**
  An active Streamlit page used to natively build interactive pie charts and bar graphs relying directly over the actively parsed sessions within SQLite using Plotly Express and Pandas. 

---

## ⚙️ 2. Dependencies & Environment
### **Technology Stack**
* **Language:** Python 3.x
* **Computer Vision:** OpenCV (`cv2`)
* **AI/Machine Learning:** Google MediaPipe (Using `blaze_face_short_range.tflite` & `face_landmarker.task`)
* **OS Interfacing:** `psutil`, `pywin32`
* **Local Backend Database:** SQLite3
* **Web UI / APIs:** Flask, Streamlit, Pandas, Plotly Express

### **System Requirements**
- Designed for **Windows** primarily given reliance on `win32gui`. 
- Local Webcam device required.

---

## 🚦 3. Execution & Operations Flow

1. **Dashboard Start:** User launches `python app.py`. A Flask app spins up securely over port `5000`. 
2. **Session Invocation:** User clicks "Start Tracking" via the Web Interface. Flask invokes `subprocess.Popen("main.py")`.
3. **Tracking Active:** 
   - `main.py` opens the camera. 
   - Memory is engaged, counting exact timestamp durations utilizing `time.time()` differentials. Frame data caches natively. 
   - Screen renders an overlaid GUI of immediate tracking statuses and alert texts.
4. **Conclusion:** 
   - User stops the operation manually via `/stop_tracking` on Web Interface, OR they hit 1 hour.
   - A `stop_flag.txt` flag is raised. `main.py` breaks its infinite `while True` loop gracefully.
   - Cached telemetry data in memory is safely translated through `insert_bulk_logs()` and `save_session_exact()`.
   - The camera is properly released (`cap.release()`), preventing Windows IO blocks, and OpenCV windows are shredded. 

---

## 📊 4. Time Tracking & Analysis Rules

* Time is kept globally and objectively natively utilizing timestamps, rendering abstract "per frame" tracking completely obsolete. 
* All analytics rely upon a **Focus Score Algorithm**, calculating straightforward percentages indicating physical true attention spanning total duration length.
* Data export allows granular CSV dumping enabling longer-term statistical study of habits. 

---

## 💡 5. Error Preventions 
* **Database Deadlocking Avoidance:** Addressed by transitioning `main.py` to compile logs actively into a localized memory array instance before making a unified API bulk shipment downward towards the `.db` layer at the end of the script lifetime.
* **CPU Drain:** Subverted by tracking 3D Head models strictly every nth frame and persisting prior cached variables over empty gaps. 
* **Port Hijacking:** Explicit `finally` block inclusion guarantees `cap.release()` triggering, which defends the camera access integrity against background program crashes.
