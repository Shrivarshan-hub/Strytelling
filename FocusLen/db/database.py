import sqlite3
import datetime
import os

class Database:
    def __init__(self, db_path="db/focuslens.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS focus_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                app_name TEXT,
                app_category TEXT,
                face_status TEXT,
                attention_state TEXT,
                overall_status TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_date DATETIME,
                total_duration INTEGER,
                focus_time INTEGER,
                distraction_time INTEGER,
                absence_time INTEGER,
                focus_score REAL
            )
        ''')
        self.conn.commit()

    def insert_log(self, app_name, app_category, face_status, attention_state, overall_status):
        cursor = self.conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO focus_log (timestamp, app_name, app_category, face_status, attention_state, overall_status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (now, app_name, app_category, face_status, attention_state, overall_status))
        self.conn.commit()

    def insert_bulk_logs(self, logs):
        cursor = self.conn.cursor()
        cursor.executemany('''
            INSERT INTO focus_log (timestamp, app_name, app_category, face_status, attention_state, overall_status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', logs)
        self.conn.commit()
    
    def save_session_exact(self, total_duration, focus_time, distraction_time, absence_time):
        focus_score = (focus_time / total_duration) * 100 if total_duration > 0 else 0
        cursor = self.conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO focus_sessions (session_date, total_duration, focus_time, distraction_time, absence_time, focus_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (now, int(total_duration), int(focus_time), int(distraction_time), int(absence_time), round(focus_score, 1)))
        self.conn.commit()
    
    def get_current_analysis(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT overall_status FROM focus_log")
        rows = cursor.fetchall()
        
        if not rows:
            return {
                "total_duration": 0, "focus_time": 0, "distraction_time": 0, "absence_time": 0, "focus_score": 0,
                "app_usage": []
            }
            
        total_time = len(rows)
        # Tracking focus time mapping uniquely to TRUE FOCUS (which correctly enforces study apps in DB logs)
        focus_time = sum(1 for r in rows if r[0] == 'TRUE FOCUS')
        distraction_time = sum(1 for r in rows if r[0] in ['DISTRACTION', 'FAKE STUDY'])
        absence_time = sum(1 for r in rows if r[0] == 'ABSENT')
        
        focus_score = (focus_time / total_time) * 100 if total_time > 0 else 0
        
        cursor.execute("SELECT app_name, COUNT(*) as duration FROM focus_log GROUP BY app_name ORDER BY duration DESC LIMIT 5")
        app_usage = [{"app": r[0] if r[0] else "unknown", "duration": r[1]} for r in cursor.fetchall()]

        return {
            "total_duration": total_time,
            "focus_time": focus_time,
            "distraction_time": distraction_time,
            "absence_time": absence_time,
            "focus_score": round(focus_score, 1),
            "app_usage": app_usage
        }

    def end_session_and_save(self):
        analysis = self.get_current_analysis()
        if analysis["total_duration"] > 0:
            cursor = self.conn.cursor()
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                INSERT INTO focus_sessions (session_date, total_duration, focus_time, distraction_time, absence_time, focus_score)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (now, analysis["total_duration"], analysis["focus_time"], analysis["distraction_time"], analysis["absence_time"], analysis["focus_score"]))
            
            # We no longer delete focus_log here, so Streamlit can still display the last session's details
            self.conn.commit()

    def get_all_sessions(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, session_date, focus_score, focus_time, distraction_time, absence_time FROM focus_sessions ORDER BY id DESC")
        return cursor.fetchall()

    def get_session_by_id(self, session_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, session_date, focus_score, focus_time, distraction_time, absence_time FROM focus_sessions WHERE id = ?", (session_id,))
        return cursor.fetchone()

    def close(self):
        self.conn.close()
