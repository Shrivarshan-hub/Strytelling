from flask import Flask, render_template, jsonify, send_file
import subprocess
import os
import sys
from db.database import Database
import csv
import io

app = Flask(__name__)
tracker_process = None

def stop_process(process):
    if process:
        try:
            if os.name == 'nt':
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
            else:
                process.terminate()
        except:
            pass
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_tracking', methods=['POST'])
def start_tracking():
    global tracker_process
    if tracker_process is None or tracker_process.poll() is not None:
        try:
            # Wipe live logs before initiating new session
            db = Database()
            db.conn.execute("DELETE FROM focus_log")
            db.conn.commit()
            db.close()
            
            # Ensure no stale stop flag is present
            if os.path.exists("stop_flag.txt"):
                os.remove("stop_flag.txt")
            
            
            python_exe = sys.executable
            
            # Windows requires specific flags to spawn external GUI tools (like OpenCV) from a background host thread
            kwargs = {}
            if os.name == 'nt':
                kwargs['creationflags'] = subprocess.CREATE_NEW_CONSOLE
                
            tracker_process = subprocess.Popen([python_exe, "main.py"], **kwargs)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"status": "error"})
    return jsonify({"status": "info"})

@app.route('/stop_tracking', methods=['POST'])
def stop_tracking():
    global tracker_process
    if tracker_process is not None and tracker_process.poll() is None:
        try:
            with open("stop_flag.txt", "w") as f:
                f.write("stop")
            
            # Allow time for main.py to read the flag and gracefully exit/save data
            tracker_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Only forcefully kill if it hung for too long
            tracker_process = stop_process(tracker_process)
            
        tracker_process = None
        return jsonify({"status": "success"})
    return jsonify({"status": "info"})

@app.route('/get_analysis', methods=['GET'])
def get_analysis():
    db = Database()
    data = db.get_current_analysis()
    db.close()
    return jsonify(data)

@app.route('/get_history', methods=['GET'])
def get_history():
    db = Database()
    sessions = db.get_all_sessions()
    db.close()
    
    result = []
    for s in sessions:
        result.append({
            "id": s[0],
            "date": s[1],
            "score": round(s[2], 1),
            "focus_time": s[3],
            "distraction_time": s[4],
            "absence_time": s[5]
        })
    return jsonify(result)

@app.route('/download_csv', methods=['GET'])
def download_csv():
    db = Database()
    sessions = db.get_all_sessions()
    db.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Session ID', 'Date', 'Focus Score (%)', 'Focus Time (s)', 'Distraction Time (s)', 'Absence Time (s)'])
    for s in sessions:
        writer.writerow([s[0], s[1], round(s[2], 1), s[3], s[4], s[5]])
    
    mByte_output = io.BytesIO(output.getvalue().encode('utf-8'))
    return send_file(
        mByte_output, 
        mimetype="text/csv", 
        as_attachment=True, 
        download_name="focuslens_history.csv"
    )

@app.route('/download_session_csv/<int:session_id>', methods=['GET'])
def download_session_csv(session_id):
    db = Database()
    session = db.get_session_by_id(session_id)
    db.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Session ID', 'Date', 'Focus Score (%)', 'Focus Time (s)', 'Distraction Time (s)', 'Absence Time (s)'])
    if session:
        writer.writerow([session[0], session[1], round(session[2], 1), session[3], session[4], session[5]])
    
    mByte_output = io.BytesIO(output.getvalue().encode('utf-8'))
    return send_file(
        mByte_output, 
        mimetype="text/csv", 
        as_attachment=True, 
        download_name=f"focuslens_session_{session_id}.csv"
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
