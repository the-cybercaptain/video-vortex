"""
VIDEO VORTEX — Ultimate Multi-Platform Video Downloader
Developed by CYBER CAPTAIN
FIXED: Playlist video resolution uses default "best"
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import threading
import tempfile
from pathlib import Path

from core.downloader import DownloadManager, DownloadStatus
from core.history import HistoryManager
from core.settings import SettingsManager
from gui.themes import get_theme, THEME_NAMES, THEMES
from gui.widgets import ThemedFrame, ThemedLabel, ThemedButton, GlowLabel
from gui.url_panel import URLPanel
from gui.active_downloads import ActiveDownloadsPanel
from gui.history_panel import HistoryPanel
from gui.settings_panel import SettingsPanel
from core.video_info import fmt_filesize


class VideoVortexApp(tk.Tk):
    APP_NAME = "VIDEO VORTEX"
    
    def __init__(self):
        super().__init__()
        self._settings = SettingsManager()
        self._history = HistoryManager()
        self._theme = get_theme(self._settings.get("theme", "hacker_green"))
        self._manager = DownloadManager(on_update=self._on_dl_update)
        self._fmt_data = []
        self._aq_data = []
        self._cur_info = {}
        self._cur_analysis = {}
        self._cur_url = ""
        self._thumb_img = None
        self._last_selected_task = None
        
        self.title(f"{self.APP_NAME} — Multi-Platform Video Downloader")
        self.configure(bg=self._theme["bg"])
        self._setup_window()
        self._build_layout()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_window(self):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(1750, sw - 40), min(800, sh - 60)
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(1200, 750)
        self.resizable(True, True)
    
    def _build_layout(self):
        t = self._theme
        
        self._make_title_bar().pack(fill="x")
        tk.Frame(self, bg=t["border"], height=1).pack(fill="x")
        
        nb = self._make_notebook()
        nb.pack(fill="both", expand=True)
        
        dl_tab = ThemedFrame(nb, t)
        nb.add(dl_tab, text=" ⬇ DOWNLOADER ")
        self._build_downloader_tab(dl_tab)
        
        hist_tab = ThemedFrame(nb, t)
        nb.add(hist_tab, text=" 📜 HISTORY ")
        self._history_panel = HistoryPanel(hist_tab, t, self._history)
        self._history_panel.pack(fill="both", expand=True)
        
        set_tab = ThemedFrame(nb, t)
        nb.add(set_tab, text=" ⚙ SETTINGS ")
        self._settings_panel = SettingsPanel(
            set_tab, t, self._settings,
            on_theme_change=self._apply_theme,
            on_bypass_change=self._on_bypass_changed,
        )
        self._settings_panel.pack(fill="both", expand=True)
        
        self._make_status_bar().pack(fill="x", side="bottom")
    
    def _make_title_bar(self):
        t = self._theme
        bar = ThemedFrame(self, t)
        
        GlowLabel(bar, t, text=f"⚡ {self.APP_NAME}",
                  font=(t["font_mono"], 16, "bold"), bg=t["bg"]).pack(side="left", padx=12, pady=8)
        
        ThemedLabel(bar, t, text=" Multi-Platform Video Downloader",
                    color_key="text_dim", font=(t["font_mono"], 9)).pack(side="left")
        
        ThemedLabel(bar, t, text="⚡ by CYBER CAPTAIN ⚡ ",
                    color_key="accent3", font=(t["font_mono"], 8, "bold")).pack(side="right", padx=(0, 12))
        
        self._theme_var = tk.StringVar(value=self._settings.get("theme", "hacker_green"))
        tc = ttk.Combobox(bar, textvariable=self._theme_var,
                          values=THEME_NAMES, state="readonly", width=18,
                          font=(t["font_mono"], 9))
        tc.pack(side="right", padx=(0, 12), pady=6)
        ThemedLabel(bar, t, text=" Theme:", color_key="text_dim",
                    font=(t["font_mono"], 9)).pack(side="right", padx=(0, 4))
        tc.bind("<<ComboboxSelected>>", lambda _: self._apply_theme(get_theme(self._theme_var.get())))
        
        return bar
    
    def _make_notebook(self):
        t = self._theme
        st = ttk.Style()
        st.theme_use("clam")
        st.configure("TNotebook", background=t["bg"], borderwidth=0)
        st.configure("TNotebook.Tab", background=t["bg2"], foreground=t["text_dim"],
                     font=(t["font_mono"], 10, "bold"), padding=(14, 6))
        st.map("TNotebook.Tab",
               background=[("selected", t["bg3"])],
               foreground=[("selected", t["accent"])])
        return ttk.Notebook(self)
    
    def _make_status_bar(self):
        t = self._theme
        bar = ThemedFrame(self, t, bg=t["bg2"])
        tk.Frame(bar, bg=t["border"], height=1).pack(fill="x")
        
        self._status_var = tk.StringVar(value="[▸] Ready — Paste a URL to begin.")
        ThemedLabel(bar, t, textvariable=self._status_var,
                    color_key="text_dim", font=(t["font_mono"], 9),
                    bg=t["bg2"]).pack(side="left", padx=10, pady=3)
        
        ThemedLabel(bar, t, text="💻 Developed by MUHAMMAD HAMAD ⚡",
                    color_key="accent3", font=(t["font_mono"], 8, "bold"),
                    bg=t["bg2"]).pack(side="right", padx=10, pady=3)
        
        self._dl_count_var = tk.StringVar(value="")
        ThemedLabel(bar, t, textvariable=self._dl_count_var,
                    color_key="accent", font=(t["font_mono"], 9, "bold"),
        
                    bg=t["bg2"]).pack(side="right", padx=10)
        
        return bar
    
    def _build_downloader_tab(self, parent):
        t = self._theme
        outer = ThemedFrame(parent, t)
        outer.pack(fill="both", expand=True)
        
        left = ThemedFrame(outer, t)
        left.pack(side="left", fill="both", expand=True)
        
        self._url_panel = URLPanel(
            left, t, on_ready=self._on_url_ready,
            cookies_browser=self._settings.get("cookies_browser", ""),
            cookies_file=self._settings.get("cookies_file", ""),
        )
        self._url_panel.pack(fill="x", padx=6, pady=(6, 0))
        
        tk.Frame(left, bg=t["border"], height=1).pack(fill="x", padx=6, pady=4)
        
        self._opts_frame = ThemedFrame(left, t, highlightthickness=1, highlightbackground=t["border"])
        self._opts_frame.pack(fill="x", padx=6, pady=0)
        self._build_options(self._opts_frame)
        
        tk.Frame(left, bg=t["border"], height=1).pack(fill="x", padx=6, pady=4)
        
        act_hdr = ThemedFrame(left, t)
        act_hdr.pack(fill="x", padx=6)
        ThemedLabel(act_hdr, t, text="▼ ACTIVE DOWNLOADS",
                    font=(t["font_mono"], 11, "bold"), color_key="accent").pack(side="left")
        self._act_count_lbl = ThemedLabel(act_hdr, t, text="[0 active]",
                                           color_key="text_dim", font=(t["font_mono"], 10))
        self._act_count_lbl.pack(side="left")
        
        self._active_panel = ActiveDownloadsPanel(
            left, t, manager=self._manager, on_select=self._on_task_select)
        self._active_panel.pack(fill="both", expand=True, padx=6, pady=(3, 6))
        
        self._right = ThemedFrame(outer, t, highlightthickness=1,
                                   highlightbackground=t["border"], width=380)
        self._right.pack(side="right", fill="y", padx=(4, 6), pady=6)
        self._right.pack_propagate(False)
        self._build_right_panel(self._right)
    
    def _build_options(self, parent):
        t = self._theme
        
        rowA = ThemedFrame(parent, t)
        rowA.pack(fill="x", padx=8, pady=8)
        
        ThemedLabel(rowA, t, text=" Mode:", font=(t["font_mono"], 11, "bold")).pack(side="left", padx=(0, 8))
        self._mode_var = tk.StringVar(value="video")
        for label, val in (("🎬 Video", "video"), ("🎵 MP3", "audio")):
            tk.Radiobutton(rowA, text=label, variable=self._mode_var, value=val,
                           command=self._on_mode_change, bg=t["bg"], fg=t["text"],
                           selectcolor=t["bg2"], activebackground=t["btn_hover"],
                           activeforeground=t["accent"], font=(t["font_mono"], 10, "bold"),
                           relief="flat").pack(side="left", padx=8)
        
        tk.Frame(rowA, bg=t["border"], width=2).pack(side="left", fill="y", padx=10)
        
        self._res_wrap = ThemedFrame(rowA, t)
        self._res_wrap.pack(side="left")
        ThemedLabel(self._res_wrap, t, text=" Resolution:", font=(t["font_mono"], 11, "bold")).pack(side="left", padx=(0, 8))
        self._res_var = tk.StringVar()
        self._res_combo = ttk.Combobox(self._res_wrap, textvariable=self._res_var,
                                        state="readonly", width=28, font=(t["font_mono"], 10))
        self._res_combo["values"] = ["— paste URL first —"]
        self._res_combo.current(0)
        self._res_combo.pack(side="left")
        self._res_combo.bind("<<ComboboxSelected>>", self._on_res_select)
        self._size_lbl = ThemedLabel(self._res_wrap, t, text="",
                                      color_key="accent3", font=(t["font_mono"], 10, "bold"))
        self._size_lbl.pack(side="left", padx=8)
        
        self._aq_wrap = ThemedFrame(rowA, t)
        ThemedLabel(self._aq_wrap, t, text=" Quality:", font=(t["font_mono"], 11, "bold")).pack(side="left", padx=(0, 8))
        self._aq_var = tk.StringVar()
        self._aq_combo = ttk.Combobox(self._aq_wrap, textvariable=self._aq_var,
                                       state="readonly", width=22, font=(t["font_mono"], 10))
        self._aq_combo["values"] = ["— paste URL first —"]
        self._aq_combo.current(0)
        self._aq_combo.pack(side="left")
        self._aq_wrap.pack_forget()  # initially hidden
        
        rowB = ThemedFrame(parent, t)
        rowB.pack(fill="x", padx=8, pady=(0, 8))
        
        ThemedLabel(rowB, t, text=" Save to:", font=(t["font_mono"], 11, "bold")).pack(side="left", padx=(0, 8))
        default_dir = self._settings.get("output_dir", str(Path.home() / "Desktop"))
        self._save_var = tk.StringVar(value=default_dir)
        self._path_entry = tk.Entry(
            rowB, textvariable=self._save_var, width=42,
            bg=t["entry_bg"], fg=t["text"], relief="flat",
            insertbackground=t["accent"], highlightthickness=1,
            highlightbackground=t["border"], font=(t["font_mono"], 10))
        self._path_entry.pack(side="left", ipady=5)
        
        ThemedButton(rowB, t, text=" Browse ", command=self._browse,
                     font=(t["font_mono"], 10, "bold"), padx=10, pady=5).pack(side="left", padx=8)
        
        self._start_btn = ThemedButton(
            rowB, t, text="⚡ START DOWNLOAD",
            command=self._start_download, accent=True,
            font=(t["font_mono"], 12, "bold"), padx=20, pady=8)
        self._start_btn.pack(side="right", padx=8)
        
        self._bypass_lbl = ThemedLabel(rowB, t, text="", color_key="accent3", font=(t["font_mono"], 8))
        self._bypass_lbl.pack(side="left", padx=8)
        self._update_bypass_label()
    
    def _build_right_panel(self, parent):
        t = self._theme
        
        ThemedLabel(parent, t, text="📋 VIDEO / TASK DETAIL",
                    font=(t["font_mono"], 11, "bold"),
                    color_key="accent").pack(pady=(12, 6))
        
        self._thumb_canvas = tk.Canvas(parent, width=320, height=190,
                                        bg=t["bg2"], highlightthickness=2,
                                        highlightbackground=t["border"])
        self._thumb_canvas.pack(padx=10, pady=5)
        self._set_thumb_placeholder("Click on a download\nto see thumbnail")
        
        self._playlist_frame = ThemedFrame(parent, t, highlightthickness=1,
                                            highlightbackground=t["border"])
        ThemedLabel(self._playlist_frame, t, text="PLAYLIST VIDEOS",
                    font=(t["font_mono"], 10, "bold"),
                    color_key="accent").pack(anchor="w", padx=8, pady=(6, 2))
        
        pl_scroll_frame = ThemedFrame(self._playlist_frame, t)
        pl_scroll_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        
        pl_vsb = tk.Scrollbar(pl_scroll_frame, orient="vertical")
        pl_hsb = tk.Scrollbar(pl_scroll_frame, orient="horizontal")
        
        self._pl_listbox = tk.Listbox(
            pl_scroll_frame, bg=t["bg2"], fg=t["text"],
            selectbackground=t["btn_hover"], selectforeground=t["accent"],
            relief="flat", bd=0, font=(t["font_mono"], 10),
            height=8, activestyle="none",
            yscrollcommand=pl_vsb.set,
            xscrollcommand=pl_hsb.set,
        )
        
        pl_vsb.config(command=self._pl_listbox.yview)
        pl_hsb.config(command=self._pl_listbox.xview)
        
        pl_hsb.pack(side="bottom", fill="x")
        pl_vsb.pack(side="right", fill="y")
        self._pl_listbox.pack(side="left", fill="both", expand=True)
        
        self._playlist_frame.pack_forget()
        
        self._detail_text = tk.Text(
            parent, width=38, height=12, bg=t["bg2"], fg=t["text"],
            insertbackground=t["accent"], relief="flat", bd=0,
            font=(t["font_mono"], 10), wrap="word", state="disabled")
        self._detail_text.pack(fill="both", expand=True, padx=10, pady=(6, 10))
    
    def _on_bypass_changed(self):
        cb = self._settings.get("cookies_browser", "")
        cf = self._settings.get("cookies_file", "")
        self._url_panel.set_cookies(browser=cb, file=cf)
        self._update_bypass_label()
    
    def _update_bypass_label(self):
        parts = []
        if self._settings.get("bypass_age", True):
            parts.append("🔞 Age")
        if self._settings.get("bypass_geo", True):
            parts.append(f"🌍 Geo({self._settings.get('geo_bypass_country','US')})")
        if self._settings.get("cookies_browser") or self._settings.get("cookies_file"):
            parts.append("🍪 Cookies")
        if self._settings.get("use_proxy") and self._settings.get("proxy_url"):
            parts.append("🌐 Proxy")
        self._bypass_lbl.config(text="Active: " + " | ".join(parts) if parts else "")
    
    def _set_thumb_placeholder(self, msg="No Thumbnail"):
        self._thumb_canvas.delete("all")
        self._thumb_canvas.create_text(
            160, 95, text=msg, fill=self._theme["text_dim"],
            font=(self._theme["font_mono"], 10), justify="center")
    
    def _browse(self):
        d = filedialog.askdirectory(initialdir=self._save_var.get())
        if d:
            self._save_var.set(d)
            self._settings.set("output_dir", d)
    
    def _on_mode_change(self):
        if self._mode_var.get() == "video":
            self._aq_wrap.pack_forget()
            self._res_wrap.pack(side="left")
        else:
            self._res_wrap.pack_forget()
            self._aq_wrap.pack(side="left")
    
    def _on_res_select(self, *_):
        idx = self._res_combo.current()
        if 0 <= idx < len(self._fmt_data):
            sz = self._fmt_data[idx].get("filesize")
            self._size_lbl.config(text=f"≈ {fmt_filesize(sz)}" if sz else "")
        else:
            self._size_lbl.config(text="")
    
    def _show_detail_text(self, text):
        self._detail_text.config(state="normal")
        self._detail_text.delete("1.0", "end")
        self._detail_text.insert("end", text)
        self._detail_text.config(state="disabled")
    
    def _on_url_ready(self, url, info, analysis):
        self._cur_url = url
        self._cur_info = info
        self._cur_analysis = analysis
        if not url or not info:
            self._fmt_data = []
            self._aq_data = []
            self._res_combo["values"] = ["— paste URL first —"]
            self._res_combo.current(0)
            self._aq_combo["values"] = ["— paste URL first —"]
            self._aq_combo.current(0)
            self._size_lbl.config(text="")
            self._set_thumb_placeholder("📷 PASTE A URL\nTO SEE THUMBNAIL")
            self._show_detail_text("")
            try:
                self._playlist_frame.pack_forget()
                self._pl_listbox.delete(0, "end")
            except Exception:
                pass
            self._set_status("[i] Paste a URL — auto-detects instantly")
            return
        
        # Check if it's a playlist - no resolution options for playlist
        entries = info.get("entries", [])
        if entries:
            # PLAYLIST - No resolution options, will use default "best"
            self._fmt_data = []
            self._res_combo["values"] = ["Best Quality (auto)"]
            self._res_combo.current(0)
            self._size_lbl.config(text="")
        else:
            # SINGLE VIDEO - Show resolution options
            self._fmt_data = info.get("formats", [])
            res_labels = [f"{f['label']}  [{fmt_filesize(f.get('filesize'))}]"
                          for f in self._fmt_data] or ["Best Quality"]
            self._res_combo["values"] = res_labels
            if res_labels:
                self._res_combo.current(0)
            self._on_res_select()
        
        self._aq_data = info.get("audio_formats", [])
        aq_labels = [f"{f['label']}  [{fmt_filesize(f.get('filesize'))}]"
                     for f in self._aq_data] or ["192kbps (default)"]
        self._aq_combo["values"] = aq_labels
        if aq_labels:
            self._aq_combo.current(0)
        
        title = (info.get("title") or "Unknown")[:100]
        creator = info.get("uploader") or "Unknown"
        dur = info.get("duration", "N/A")
        views = info.get("view_count", 0)
        age_lim = info.get("age_limit", 0)
        
        if views and views > 1_000_000:
            views_text = f"{views/1_000_000:.1f}M"
        elif views and views > 1000:
            views_text = f"{views/1000:.1f}K"
        else:
            views_text = f"{views:,}" if views else "--"
        
        if entries:
            self._pl_listbox.delete(0, "end")
            for i, e in enumerate(entries, 1):
                et = e.get("title") or e.get("url") or f"Video {i}"
                ed = e.get("duration", "")
                line = f" {i:>3}. {et}"
                if ed:
                    line += f"  [{ed}]"
                self._pl_listbox.insert("end", line)
            self._playlist_frame.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        else:
            self._playlist_frame.pack_forget()
            self._pl_listbox.delete(0, "end")
        
        detail = (f" Platform: {analysis.get('platform', '?')}\n\n"
                  f"Title:\n{title}\n"
                  f"Creator: {creator}\n"
                  f"Duration: {dur}\n")
        if age_lim:
            detail += f" Age Limit: {age_lim}+\n"
        if entries:
            detail += f" Playlist: {len(entries)} videos\n"
        if views:
            detail += f" Views: {views_text}\n"
        detail += f"\n URL:\n{url[:100]}"
        self._show_detail_text(detail)
        
        # Thumbnail
        thumb_url = info.get("thumbnail", "")
        if not thumb_url and entries:
            thumb_url = entries[0].get("thumbnail", "")
        
        if thumb_url:
            self._set_thumb_placeholder("⏳ Loading...")
            threading.Thread(target=self._load_thumb_for_url, args=(thumb_url,), daemon=True).start()
        else:
            self._set_thumb_placeholder("No thumbnail")
        
        self._set_status(f"[✓] Ready — {analysis.get('platform', '?')} | {title[:50]}")
    
    def _load_thumb_for_url(self, url):
        try:
            import urllib.request
            tmp = tempfile.mktemp(suffix=".jpg")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
                with open(tmp, "wb") as f:
                    f.write(data)
            self.after(0, lambda: self._show_thumb(tmp))
        except Exception:
            self.after(0, lambda: self._set_thumb_placeholder("✕ Thumbnail failed"))
    
    def _show_thumb(self, path):
        try:
            from PIL import Image, ImageTk
            img = Image.open(path).resize((320, 190), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._thumb_canvas.delete("all")
            self._thumb_canvas.create_image(0, 0, anchor="nw", image=photo)
            self._thumb_canvas.image = photo
        except Exception:
            self._set_thumb_placeholder(" Image error")
        finally:
            try:
                os.remove(path)
            except Exception:
                pass
    
    def _get_bypass_kwargs(self) -> dict:
        return {
            "bypass_age": self._settings.get("bypass_age", True),
            "bypass_geo": self._settings.get("bypass_geo", True),
            "geo_bypass_country": self._settings.get("geo_bypass_country", "US"),
            "use_cookies": bool(self._settings.get("cookies_file") or self._settings.get("cookies_browser")),
            "cookies_file": self._settings.get("cookies_file", ""),
            "cookies_browser": self._settings.get("cookies_browser", ""),
            "use_proxy": self._settings.get("use_proxy", False),
            "proxy_url": self._settings.get("proxy_url", ""),
            "embed_subs": self._settings.get("embed_subs", False),
            "embed_thumbnail": self._settings.get("embed_thumbnail", False),
            "embed_metadata": self._settings.get("embed_metadata", True),
            "remove_sponsor": self._settings.get("remove_sponsor", True),
            "max_resolution": self._settings.get("max_resolution", 16000),
            "sleep_interval": float(self._settings.get("sleep_interval", 0)),
            "throttle_rate": self._settings.get("throttle_rate", ""),
        }
    
    def _start_download(self):
        if not self._cur_url:
            messagebox.showwarning("No URL", "Paste a URL first — it auto-analyzes.")
            return
        if self._cur_analysis.get("phishing"):
            messagebox.showerror("Blocked", "Phishing URL — download blocked.")
            return
        
        is_audio = self._mode_var.get() == "audio"
        out_dir = self._save_var.get() or str(Path.home() / "Desktop")
        
        if is_audio:
            idx = self._aq_combo.current()
            aq = str(int(self._aq_data[idx]["abr"])) if 0 <= idx < len(self._aq_data) else "192"
            fmt = "bestaudio"
        else:
            idx = self._res_combo.current()
            # For playlist, no fmt_data - use "best"
            if self._fmt_data and 0 <= idx < len(self._fmt_data):
                fmt = self._fmt_data[idx]["format_id"]
            else:
                fmt = "best"
            aq = "192"
        
        info = self._cur_info
        platform = info.get("platform") or self._cur_analysis.get("platform", "Unknown")
        entries = info.get("entries", [])
        
        if entries:
            self._start_playlist(self._cur_url, info, fmt, is_audio, aq, out_dir, platform)
        else:
            self._start_single(self._cur_url, info.get("title", self._cur_url),
                               platform, fmt, is_audio, aq, out_dir,
                               info.get("thumbnail", ""))
    
    def _start_single(self, url, title, platform, fmt_id, is_audio, audio_quality, out_dir, thumb_url=""):
        bypass = self._get_bypass_kwargs()
        tid = self._manager.add_download(
            url=url, title=title, platform=platform, format_id=fmt_id,
            output_dir=out_dir, is_audio=is_audio, audio_quality=audio_quality,
            **bypass,
        )
        task = self._manager.get_task(tid)
        if task:
            task.thumbnail_url = thumb_url
            self._active_panel.add_task(task)
        self._history_panel.add_entry(url, title, platform, "Queued")
        self._set_status(f"[⬇] Started: {title[:50]}")
        self._url_panel.clear_url()
        self._clear_all_display()
    
    def _clear_all_display(self):
        self._thumb_canvas.delete("all")
        self._set_thumb_placeholder(" Paste a new URL\nto download")
        self._show_detail_text("")
        
        # ========== ADD THESE LINES - Clear resolution & audio ==========
        self._fmt_data = []
        self._aq_data = []
        self._res_combo["values"] = ["— paste URL first —"]
        self._res_combo.current(0)
        self._aq_combo["values"] = ["— paste URL first —"]
        self._aq_combo.current(0)
        self._size_lbl.config(text="")
        # ================================================================
        
        try:
            self._playlist_frame.pack_forget()
            self._pl_listbox.delete(0, "end")
        except Exception:
            pass
    
    def _start_playlist(self, url, info, fmt_id, is_audio, audio_quality, out_dir, platform):
        entries = info.get("entries", [])
        out_sub = os.path.join(out_dir, (info.get("title", "Playlist"))[:60])
        self._set_status(f"[📋] Playlist: {len(entries)} videos queued")
        
        for entry in entries:
            eu = entry.get("url", "")
            et = entry.get("title", eu)
            thumb = entry.get("thumbnail", "")
            if eu:
                self._start_single(eu, et, platform, fmt_id, is_audio, audio_quality, out_sub, thumb)
    
    def _on_dl_update(self, task_id):
        self.after(0, lambda: self._handle_dl_update(task_id))
    
    def _handle_dl_update(self, task_id):
        self._active_panel.refresh(task_id)
        task = self._manager.get_task(task_id)
        
        if self._last_selected_task == task_id and task:
            self._update_selected_task_detail(task)
        
        if self._last_selected_task == task_id and (not task or task.status == DownloadStatus.CANCELLED):
            self._clear_right_panel()
        
        if task:
            if task.status == DownloadStatus.DOWNLOADING:
                self._history_panel.update_entry(task.url, "Downloading")
            elif task.status == DownloadStatus.COMPLETED:
                self._history_panel.update_entry(task.url, "Completed", task.filename)
                self._set_status(f"[✓] Done: {task.title[:50]}")
            elif task.status == DownloadStatus.CANCELLED:
                self._history_panel.update_entry(task.url, "Cancelled")
            elif task.status == DownloadStatus.ERROR:
                self._history_panel.update_entry(task.url, "Error")
        
        tasks = self._manager.get_all_tasks()
        active = sum(1 for t in tasks if t.status == DownloadStatus.DOWNLOADING)
        paused = sum(1 for t in tasks if t.status == DownloadStatus.PAUSED)
        queued = sum(1 for t in tasks if t.status == DownloadStatus.QUEUED)
        done = sum(1 for t in tasks if t.status == DownloadStatus.COMPLETED)
        self._act_count_lbl.config(text=f"[{active} active]")
        self._dl_count_var.set(f" {active} active  {paused} paused  {queued} queued  {done} done")
    
    def _on_task_select(self, task_id, task=None):
        self._last_selected_task = task_id
        if task is None:
            task = self._manager.get_task(task_id)
        if not task:
            self._clear_right_panel()
            return
        
        icons = {
            DownloadStatus.DOWNLOADING: "⬇",
            DownloadStatus.COMPLETED: "✓",
            DownloadStatus.PAUSED: "⏸",
            DownloadStatus.CANCELLED: "✕",
            DownloadStatus.ERROR: "⚠",
            DownloadStatus.QUEUED: "⏳",
        }
        
        text = (f"{icons.get(task.status,'·')} {task.status.value}\n\n"
                f"Title:\n{task.title[:100]}\n\n"
                f" Platform: {task.platform}\n"
                f" Progress: {task.progress:.1f}%\n"
                f" Speed: {task.speed or '—'}\n"
                f" ETA: {task.eta or '—'}\n"
                f" Size: {task.total_size or '—'}\n"
                f" File: {(task.filename or '—')[:40]}\n\n"
                f" URL:\n{task.url[:100]}\n")
        
        if task.error_msg:
            text += f"\n⚠ Error:\n{task.error_msg}"
        
        self._show_detail_text(text)
        self._playlist_frame.pack_forget()
        
        thumb = getattr(task, "thumbnail_url", "")
        if thumb:
            self._set_thumb_placeholder("⏳ Loading...")
            threading.Thread(target=self._load_thumb_for_url, args=(thumb,), daemon=True).start()
        else:
            self._set_thumb_placeholder("No Thumbnail\nAvailable")
    
    def _update_selected_task_detail(self, task):
        icons = {
            DownloadStatus.DOWNLOADING: "⬇",
            DownloadStatus.COMPLETED: "✓",
            DownloadStatus.PAUSED: "⏸",
            DownloadStatus.CANCELLED: "✕",
            DownloadStatus.ERROR: "⚠",
            DownloadStatus.QUEUED: "⏳",
        }
        text = (f"{icons.get(task.status,'·')} {task.status.value}\n\n"
                f"Title:\n{task.title[:100]}\n\n"
                f" Platform: {task.platform}\n"
                f" Progress: {task.progress:.1f}%\n"
                f" Speed: {task.speed or '—'}\n"
                f" ETA: {task.eta or '—'}\n"
                f" Size: {task.total_size or '—'}\n"
                f" File: {(task.filename or '—')[:40]}\n\n"
                f" URL:\n{task.url[:100]}\n")
        if task.error_msg:
            text += f"\n⚠ Error:\n{task.error_msg}"
        self._show_detail_text(text)
    
    def _apply_theme(self, theme):
        self._theme = theme
        key = next((k for k, v in THEMES.items() if v.get("name") == theme.get("name")), "hacker_green")
        self._settings.set("theme", key)
        self.configure(bg=theme["bg"])
        
        st = ttk.Style()
        st.configure("TNotebook", background=theme["bg"])
        st.configure("TNotebook.Tab", background=theme["bg2"], foreground=theme["text_dim"],
                     font=(theme["font_mono"], 10, "bold"))
        st.map("TNotebook.Tab", background=[("selected", theme["bg3"])],
               foreground=[("selected", theme["accent"])])
        
        self._thumb_canvas.config(bg=theme["bg2"], highlightbackground=theme["border"])
        self._detail_text.config(bg=theme["bg2"], fg=theme["text"])
        self._pl_listbox.config(bg=theme["bg2"], fg=theme["text"],
                                selectbackground=theme["btn_hover"], selectforeground=theme["accent"])
        
        for p in (self._url_panel, self._active_panel, self._history_panel, self._settings_panel):
            try:
                p.apply_theme(theme)
            except Exception:
                pass
        self._set_status(f"[🎨] Theme: {theme['name']}")
    
    def _set_status(self, msg):
        self._status_var.set(msg)
    
    def _clear_right_panel(self):
        self._thumb_canvas.delete("all")
        self._thumb_canvas.create_text(
            160, 95, text="No task selected\nClick any download\nto see details",
            fill=self._theme["text_dim"], font=(self._theme["font_mono"], 10), justify="center")
        self._show_detail_text("Click on any download\nto see details")
        try:
            self._playlist_frame.pack_forget()
        except Exception:
            pass
    
    def _on_close(self):
        active = [t for t in self._manager.get_all_tasks()
                  if t.status in (DownloadStatus.DOWNLOADING, DownloadStatus.QUEUED)]
        if active:
            if not messagebox.askyesno("Quit", f"{len(active)} download(s) in progress.\nCancel and quit?", parent=self):
                return
            self._manager.cancel_all()
        self.destroy()


def main():
    app = VideoVortexApp()
    app.mainloop()


if __name__ == "__main__":
    main()