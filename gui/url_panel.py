"""Auto-fetch URL panel with debounce and live analysis."""

import tkinter as tk
import threading
from typing import Callable, Optional, Dict

from gui.widgets import ThemedFrame, ThemedLabel, ThemedEntry, GlowLabel
from core.url_analyzer import analyze_url
from core.video_info import fetch_video_info, fetch_playlist_info


class URLPanel(ThemedFrame):
    """URL bar with auto-fetch. Debounce: waits 800ms after last keystroke."""
    DEBOUNCE_MS = 800
    
    def __init__(self, parent, theme: dict, on_ready: Callable, cookies_browser: str = "",
                 cookies_file: str = "", **kwargs):
        super().__init__(parent, theme, **kwargs)
        self._theme = theme
        self._on_ready = on_ready
        self._cookies_browser = cookies_browser
        self._cookies_file = cookies_file
        self._info: Optional[Dict] = None
        self._last_url = ""
        self._last_analysis: Dict = {}
        self._debounce_job = None
        self._fetching = False
        self._build_ui()
    
    def set_cookies(self, browser: str = "", file: str = ""):
        self._cookies_browser = browser
        self._cookies_file = file
    
    def _build_ui(self):
        t = self._theme
        
        row1 = ThemedFrame(self, t)
        row1.pack(fill="x", padx=8, pady=(8, 3))
        
        GlowLabel(row1, t, text="[>] URL:", font=(t["font_mono"], 10, "bold")).pack(side="left", padx=(0, 8))
        
        self._url_var = tk.StringVar()
        self._url_entry = ThemedEntry(row1, t, textvariable=self._url_var)
        self._url_entry.pack(side="left", fill="x", expand=True, ipady=5)
        
        self._clear_btn = tk.Button(
            row1, text="✕", bg=t["btn_bg"], fg=t["text_dim"],
            activebackground=t["btn_hover"], activeforeground=t["error"],
            relief="flat", bd=0, cursor="hand2",
            font=(t["font_mono"], 10), command=self._clear_url
        )
        self._clear_btn.pack(side="left", padx=(4, 0))
        
        self._spinner_var = tk.StringVar(value="")
        self._spinner_lbl = ThemedLabel(row1, t, textvariable=self._spinner_var,
                                         color_key="accent", font=(t["font_mono"], 10, "bold"))
        self._spinner_lbl.pack(side="left", padx=6)
        
        row2 = ThemedFrame(self, t)
        row2.pack(fill="x", padx=8, pady=(0, 6))
        
        self._valid_box = self._make_box(row2, "VALIDITY", "—")
        self._phish_box = self._make_box(row2, "SECURITY", "—")
        self._plat_box = self._make_box(row2, "PLATFORM", "—")
        self._type_box = self._make_box(row2, "TYPE", "—")
        
        self._status_var = tk.StringVar(value="[i] Paste a URL — auto-detects instantly")
        ThemedLabel(row2, t, textvariable=self._status_var,
                    color_key="text_dim", font=(t["font_mono"], 8)).pack(side="left", padx=10)
        
        self._url_var.trace_add("write", self._on_text_changed)
    
    def _make_box(self, parent, label, initial):
        t = self._theme
        frm = ThemedFrame(parent, t, highlightthickness=1, highlightbackground=t["border"])
        frm.pack(side="left", padx=(0, 5), pady=2, ipadx=7, ipady=3)
        ThemedLabel(frm, t, text=label, color_key="text_dim",
                    font=(t["font_mono"], 7, "bold")).pack(anchor="w")
        lbl = ThemedLabel(frm, t, text=initial, font=(t["font_mono"], 9, "bold"))
        lbl.pack(anchor="w")
        return lbl
    
    def _on_text_changed(self, *_):
        url = self._url_var.get().strip()
        if not url:
            self._reset_boxes()
            self._status_var.set("[i] Paste a URL — auto-detects instantly")
            self._spinner_var.set("")
            self._info = None
            return
        
        if self._debounce_job:
            self.after_cancel(self._debounce_job)
        self._status_var.set("[•] Waiting...")
        self._debounce_job = self.after(self.DEBOUNCE_MS, lambda: self._fire_analyze(url))
    
    def _fire_analyze(self, url):
        if url == self._last_url and self._info and not self._fetching:
            self._on_ready(url, self._info, self._last_analysis)
            return
        if self._fetching:
            return
        self._fetching = True
        self._status_var.set("[↻] Analyzing...")
        self._spinner_var.set("◉")
        self._start_spinner()
        threading.Thread(target=self._worker_analyze, args=(url,), daemon=True).start()
    
    def _start_spinner(self):
        frames = ["◉", "◎", "◉", "●"]
        self._spin_i = 0
        
        def tick():
            if not self._fetching:
                self._spinner_var.set("")
                return
            self._spinner_var.set(frames[self._spin_i % len(frames)])
            self._spin_i += 1
            self.after(200, tick)
        
        self.after(200, tick)
    
    def _worker_analyze(self, url):
        analysis = analyze_url(url)
        self.after(0, lambda: self._show_analysis(url, analysis))
    
    def _show_analysis(self, url, analysis):
        t = self._theme
        self._valid_box.config(
            text="✓ VALID" if analysis["valid"] else "✕ INVALID",
            fg=t["success"] if analysis["valid"] else t["error"])
        self._phish_box.config(
            text="✓ SAFE" if not analysis["phishing"] else "⚠ PHISHING",
            fg=t["success"] if not analysis["phishing"] else t["error"])
        self._plat_box.config(text=analysis["platform"], fg=t["accent3"])
        self._type_box.config(
            text="PLAYLIST" if analysis["is_playlist"] else "VIDEO",
            fg=t["accent"])
        
        if analysis["phishing"]:
            self._status_var.set(f"[!] BLOCKED — {analysis['phishing_reason'][:55]}")
            self._fetching = False
            return
        
        if not analysis["valid"]:
            self._status_var.set("[✕] Invalid URL — check and try again")
            self._fetching = False
            return
        
        self._status_var.set("[↻] Fetching video info...")
        threading.Thread(target=self._worker_fetch, args=(url, analysis), daemon=True).start()
    
    def _worker_fetch(self, url, analysis):
        try:
            if analysis["is_playlist"]:
                info = fetch_playlist_info(url, cookies_browser=self._cookies_browser,
                                            cookies_file=self._cookies_file)
            else:
                info = fetch_video_info(url, cookies_browser=self._cookies_browser,
                                         cookies_file=self._cookies_file)
        except Exception as e:
            info = {"error": str(e)}
        self.after(0, lambda: self._show_info(url, info, analysis))
    
    def _show_info(self, url, info, analysis):
        self._fetching = False
        self._spinner_var.set("")
        if "error" in info:
            self._status_var.set(f"[✕] {info['error']}")
            return
        self._info = info
        self._last_url = url
        self._last_analysis = analysis
        title = (info.get("title") or url)[:60]
        self._status_var.set(f"[✓] {analysis['platform']} | {title}")
        self._on_ready(url, info, analysis)
    
    def _clear_url(self):
        self._url_var.set("")
        self._reset_boxes()
        self._status_var.set("[i] Paste a URL — auto-detects instantly")
        self._spinner_var.set("")
        self._info = None
        if self._debounce_job:
            self.after_cancel(self._debounce_job)
            self._debounce_job = None
        self._on_ready("", {}, {"platform": "", "is_playlist": False})
    
    def _reset_boxes(self):
        for box in (self._valid_box, self._phish_box, self._plat_box, self._type_box):
            box.config(text="—", fg=self._theme["text_dim"])
    
    def clear_url(self):
        self._clear_url()
    
    def apply_theme(self, theme: dict):
        self._theme = theme
        self.config(bg=theme["bg"])
        try:
            self._url_entry.apply_theme(theme)
        except Exception:
            pass