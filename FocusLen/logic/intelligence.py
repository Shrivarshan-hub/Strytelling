import time
from collections import deque

class StateLogic:
    def __init__(self, smoothing_window=3):
        self.state_history = deque(maxlen=smoothing_window)
        
    def determine_status(self, app_category, face_status, attention_state):
        raw_status = "UNKNOWN"
        
        # VERY STRICT RULESETS as requested
        # TRUE FOCUS = study app + focused face
        # FAKE STUDY = study app + distracted face
        # DISTRACTION = non-study app
        # ABSENT = no face
        
        if face_status == "ABSENT":
            raw_status = "ABSENT"
        elif attention_state == "DROWSY":
            raw_status = "DROWSY"
        elif app_category == "STUDY":
            if attention_state == "FOCUSED":
                raw_status = "TRUE FOCUS"
            else:
                raw_status = "FAKE STUDY"
        else:
            # Entirely non-study apps evaluate directly to distraction automatically
            raw_status = "DISTRACTION"
                
        # Debouncing behavior to smooth noise
        self.state_history.append(raw_status)
        
        if len(self.state_history) > 0:
            return max(set(self.state_history), key=self.state_history.count)
        return raw_status
