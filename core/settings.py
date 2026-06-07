"""
Persistent application settings stored as JSON.
"""

import json
import os
import sys

DEFAULT_PATH = os.path.join(os.path.expanduser("~"), ".videovortex_settings.json")


def default_output_dir() -> str:
    if sys.platform == "android" or os.path.exists("/data/data"):
        dl = os.path.join(os.path.expanduser("~"), "Downloads")
    else:
        dl = os.path.join(os.path.expanduser("~"), "Desktop")
    os.makedirs(dl, exist_ok=True)
    return dl


DEFAULTS = {
    "output_dir": default_output_dir(),
    "theme": "hacker_green",
    "max_parallel": 3,
    "default_format": "best",
    "default_audio_quality": "192",
    "bypass_geo": True,
    "bypass_age": True,
    "geo_bypass_country": "US",
    "use_cookies": False,
    "cookies_file": "",
    "cookies_browser": "",
    "use_proxy": False,
    "proxy_url": "",
    "embed_subs": False,
    "embed_thumbnail": False,
    "embed_metadata": True,
    "remove_sponsor": True,
    "max_resolution": 16000,
    "sleep_interval": 0,
    "throttle_rate": "",
}


class SettingsManager:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        self.data: dict = {}
        self._load()
    
    def get(self, key: str, default=None):
        return self.data.get(key, DEFAULTS.get(key, default))
    
    def set(self, key: str, value):
        self.data[key] = value
        self._save()
    
    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = dict(DEFAULTS)
        else:
            self.data = dict(DEFAULTS)
    
    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass