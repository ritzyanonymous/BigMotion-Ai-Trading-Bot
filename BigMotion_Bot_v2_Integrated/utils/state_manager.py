"""State management"""
import json
from pathlib import Path
from typing import Dict, Any
from threading import Lock


class StateManager:
    def __init__(self, state_file: str = 'bot_state.json'):
        self.state_file = Path(state_file)
        self.lock = Lock()
        self.state = self.load_state()
    
    def load_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                return self.get_default_state()
        return self.get_default_state()
    
    def get_default_state(self) -> Dict[str, Any]:
        return {
            'last_daily_report': None,
            'last_weekly_report': None,
            'total_trades': 0,
            'status': 'initialized'
        }
    
    def save_state(self, state: Dict[str, Any] = None):
        with self.lock:
            if state:
                self.state.update(state)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=4)
    
    def get_state(self) -> Dict[str, Any]:
        with self.lock:
            return self.state.copy()
    
    def update(self, updates: Dict[str, Any]):
        with self.lock:
            self.state.update(updates)
            self.save_state()
    
    def get(self, key: str, default: Any = None) -> Any:
        with self.lock:
            return self.state.get(key, default)
