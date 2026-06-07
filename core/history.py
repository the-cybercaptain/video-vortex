"""
Persistent download history stored as a JSON file.
"""

import json
import os
import time
from typing import List, Dict, Optional

_DEFAULT_PATH = os.path.join(os.path.expanduser("~"), ".videovortex_history.json")


class HistoryManager:
    def __init__(self, path: str = _DEFAULT_PATH):
        self.path = path
        self._items: List[Dict] = []
        self._load()
    
    def add(self, url: str, title: str, platform: str, status: str, filename: str = ""):
        entry = {
            "url": url,
            "title": title,
            "platform": platform,
            "status": status,
            "filename": filename,
            "timestamp": time.time(),
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._items.insert(0, entry)
        self._items = self._items[:500]
        self._save()
    
    def update_status(self, url: str, new_status: str, filename: str = ""):
        for item in self._items:
            if item["url"] == url:
                item["status"] = new_status
                item["filename"] = filename or item.get("filename", "")
                self._save()
                return
    
    def get_all(self) -> List[Dict]:
        return list(self._items)
    
    def clear(self):
        self._items = []
        self._save()
    
    def delete_entry(self, index: int):
        if 0 <= index < len(self._items):
            self._items.pop(index)
            self._save()
    
    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._items = json.load(f)
            except Exception:
                self._items = []
        else:
            self._items = []
    
    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._items, f, ensure_ascii=False, indent=2)
        except Exception:
            pass