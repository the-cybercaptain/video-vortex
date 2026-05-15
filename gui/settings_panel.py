"""Settings panel with all bypass options."""

import tkinter as tk
from tkinter import ttk, filedialog
from typing import Callable

from gui.widgets import (ThemedFrame, ThemedLabel, ThemedButton,
                          ThemedEntry, ThemedCheckbutton)
from gui.themes import get_theme, THEMES, THEME_NAMES


class SettingsPanel(ThemedFrame):
    def __init__(self, parent, theme: dict, settings, on_theme_change: Callable,
                 on_bypass_change: Callable = None, **kwargs):
        super().__init__(parent, theme, **kwargs)
        self._theme = theme
        self._settings = settings
        self._on_tc = on_theme_change
        self._on_bypass = on_bypass_change or (lambda: None)
        self._build_ui()
    
    def _build_ui(self):
        t = self._theme
        
        canvas = tk.Canvas(self, bg=t["bg"], highlightthickness=0)
        vsb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        inner = ThemedFrame(canvas, t)
        win = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        
        ThemedLabel(inner, t, text="⚙ SETTINGS",
                    font=(t["font_mono"], 12, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        
        self._inner = inner
        self._canvas = canvas
        
        self._build_theme_section(inner)
        self._build_output_section(inner)
        self._build_parallel_section(inner)
        self._build_bypass_section(inner)
        self._build_advanced_section(inner)
        self._build_about_section(inner)
    
    def _section(self, parent, title: str) -> ThemedFrame:
        t = self._theme
        frm = ThemedFrame(parent, t, highlightthickness=1, highlightbackground=t["border"])
        frm.pack(fill="x", padx=12, pady=6)
        ThemedLabel(frm, t, text=title, font=(t["font_mono"], 10, "bold"),
                    color_key="accent").pack(anchor="w", padx=10, pady=(8, 0))
        return frm
    
    def _build_theme_section(self, parent):
        t = self._theme
        sect = self._section(parent, "🎨 Theme")
        grid = ThemedFrame(sect, t)
        grid.pack(fill="x", padx=8, pady=4)
        
        self._theme_btns = {}
        col = 0
        for key, th in THEMES.items():
            btn = tk.Button(
                grid, text=th["name"], bg=th["bg"], fg=th["accent"],
                activebackground=th["btn_hover"], activeforeground=th["accent3"],
                font=(th["font_mono"], 9, "bold"), relief="flat", bd=1,
                padx=12, pady=6, cursor="hand2",
                command=lambda k=key: self._apply_theme(k),
            )
            btn.grid(row=col // 4, column=col % 4, padx=4, pady=4, sticky="ew")
            self._theme_btns[key] = btn
            col += 1
        
        cur = self._settings.get("theme", "hacker_green")
        self._highlight_theme_btn(cur)
    
    def _build_output_section(self, parent):
        t = self._theme
        sect = self._section(parent, "📁 Default Save Location")
        row = ThemedFrame(sect, t)
        row.pack(fill="x", padx=8, pady=4)
        
        self._outdir_var = tk.StringVar(value=self._settings.get("output_dir"))
        tk.Entry(row, textvariable=self._outdir_var, width=50,
                 bg=t["entry_bg"], fg=t["text"], insertbackground=t["accent"],
                 relief="flat", bd=0, highlightthickness=1, highlightbackground=t["border"],
                 font=(t["font_mono"], 10)).pack(side="left", ipady=5)
        ThemedButton(row, t, text=" Browse ", command=self._browse_out).pack(side="left", padx=6)
        ThemedButton(row, t, text=" Save ", command=self._save_dir, accent=True).pack(side="left")
    
    def _build_parallel_section(self, parent):
        t = self._theme
        sect = self._section(parent, "⚡ Parallel Downloads")
        row = ThemedFrame(sect, t)
        row.pack(fill="x", padx=8, pady=4)
        
        ThemedLabel(row, t, text="Max simultaneous:").pack(side="left", padx=(0, 8))
        self._par_var = tk.IntVar(value=self._settings.get("max_parallel", 3))
        for v in (1, 2, 3, 4, 5, 10, 15, 20):
            tk.Radiobutton(
                row, text=str(v), variable=self._par_var, value=v,
                command=self._save_parallel, bg=t["bg"], fg=t["text"],
                selectcolor=t["bg2"], activebackground=t["btn_hover"],
                font=(t["font_mono"], 10), relief="flat",
            ).pack(side="left", padx=4)
    
    def _build_bypass_section(self, parent):
        t = self._theme
        sect = self._section(parent, "🔓 Bypass & Restrictions Removal")
        
        self._age_var = tk.BooleanVar(value=self._settings.get("bypass_age", True))
        ThemedCheckbutton(sect, t, text=" Bypass Age Restriction (18+ content)",
                          variable=self._age_var, command=self._save_bypass).pack(anchor="w", padx=8, pady=2)
        
        self._geo_var = tk.BooleanVar(value=self._settings.get("bypass_geo", True))
        ThemedCheckbutton(sect, t, text=" Bypass Geo-Restriction / Region Lock",
                          variable=self._geo_var, command=self._save_bypass).pack(anchor="w", padx=8, pady=2)
        
        geo_row = ThemedFrame(sect, t)
        geo_row.pack(fill="x", padx=24, pady=2)
        ThemedLabel(geo_row, t, text="Fake Country Code:").pack(side="left", padx=(0, 8))
        self._country_var = tk.StringVar(value=self._settings.get("geo_bypass_country", "US"))
        country_combo = ttk.Combobox(
            geo_row, textvariable=self._country_var,
            values=["US", "GB", "CA", "AU", "DE", "FR", "JP", "IN", "BR", "NL", "SE", "SG"],
            state="normal", width=8, font=(t["font_mono"], 9))
        country_combo.pack(side="left")
        country_combo.bind("<<ComboboxSelected>>", lambda _: self._save_bypass())
        country_combo.bind("<FocusOut>", lambda _: self._save_bypass())
        
        # Cookies
        ThemedLabel(sect, t, text="🍪 Cookies (for age-verified / login-protected):",
                    font=(t["font_mono"], 9, "bold"), color_key="accent3").pack(anchor="w", padx=8, pady=(8, 2))
        
        browser_row = ThemedFrame(sect, t)
        browser_row.pack(fill="x", padx=8, pady=2)
        ThemedLabel(browser_row, t, text="From Browser:").pack(side="left", padx=(0, 8))
        self._browser_var = tk.StringVar(value=self._settings.get("cookies_browser", ""))
        browser_combo = ttk.Combobox(
            browser_row, textvariable=self._browser_var,
            values=["", "chrome", "firefox", "edge", "opera", "safari", "brave", "chromium"],
            state="readonly", width=14, font=(t["font_mono"], 9))
        browser_combo.pack(side="left")
        browser_combo.bind("<<ComboboxSelected>>", lambda _: self._save_bypass())
        
        file_row = ThemedFrame(sect, t)
        file_row.pack(fill="x", padx=8, pady=2)
        ThemedLabel(file_row, t, text="From File:").pack(side="left", padx=(0, 8))
        self._cookies_file_var = tk.StringVar(value=self._settings.get("cookies_file", ""))
        tk.Entry(file_row, textvariable=self._cookies_file_var, width=40,
                 bg=t["entry_bg"], fg=t["text"], insertbackground=t["accent"],
                 relief="flat", bd=0, highlightthickness=1, highlightbackground=t["border"],
                 font=(t["font_mono"], 9)).pack(side="left", ipady=4)
        ThemedButton(file_row, t, text=" Browse ", command=self._browse_cookies).pack(side="left", padx=6)
        ThemedButton(file_row, t, text=" Save ", command=self._save_bypass, accent=True).pack(side="left")
        
        # Proxy
        ThemedLabel(sect, t, text="🌐 Proxy (to bypass country bans):",
                    font=(t["font_mono"], 9, "bold"), color_key="accent3").pack(anchor="w", padx=8, pady=(8, 2))
        proxy_row = ThemedFrame(sect, t)
        proxy_row.pack(fill="x", padx=8, pady=2)
        self._proxy_var = tk.BooleanVar(value=self._settings.get("use_proxy", False))
        ThemedCheckbutton(proxy_row, t, text="Enable Proxy", variable=self._proxy_var,
                          command=self._save_bypass).pack(side="left", padx=(0, 8))
        self._proxy_url_var = tk.StringVar(value=self._settings.get("proxy_url", ""))
        tk.Entry(proxy_row, textvariable=self._proxy_url_var, width=38,
                 bg=t["entry_bg"], fg=t["text"], insertbackground=t["accent"],
                 relief="flat", bd=0, highlightthickness=1, highlightbackground=t["border"],
                 font=(t["font_mono"], 9)).pack(side="left", ipady=4)
        ThemedLabel(proxy_row, t, text="e.g. socks5://127.0.0.1:1080",
                    color_key="text_dim", font=(t["font_mono"], 8)).pack(side="left", padx=8)
        ThemedButton(proxy_row, t, text=" Save ", command=self._save_bypass, accent=True).pack(side="left")
    
    def _build_advanced_section(self, parent):
        t = self._theme
        sect = self._section(parent, "🔧 Advanced Download Options")
        
        res_row = ThemedFrame(sect, t)
        res_row.pack(fill="x", padx=8, pady=4)
        ThemedLabel(res_row, t, text="Max Resolution:").pack(side="left", padx=(0, 8))
        self._max_res_var = tk.StringVar(value=str(self._settings.get("max_resolution", 16000)))
        res_combo = ttk.Combobox(
            res_row, textvariable=self._max_res_var,
            values=["480", "720", "1080", "1440", "2160", "4320", "7680", "16000"],
            state="normal", width=8, font=(t["font_mono"], 9))
        res_combo.pack(side="left")
        res_combo.bind("<<ComboboxSelected>>", lambda _: self._save_advanced())
        res_combo.bind("<FocusOut>", lambda _: self._save_advanced())
        ThemedLabel(res_row, t, text="p (16000 = up to 16K)", color_key="text_dim",
                    font=(t["font_mono"], 8)).pack(side="left", padx=8)
        
        self._sponsor_var = tk.BooleanVar(value=self._settings.get("remove_sponsor", True))
        ThemedCheckbutton(sect, t, text=" SponsorBlock — Remove Sponsor/Intro/Outro (YouTube)",
                          variable=self._sponsor_var, command=self._save_advanced).pack(anchor="w", padx=8, pady=2)
        
        self._subs_var = tk.BooleanVar(value=self._settings.get("embed_subs", False))
        ThemedCheckbutton(sect, t, text=" Embed Subtitles (EN/UR/AR + Auto)",
                          variable=self._subs_var, command=self._save_advanced).pack(anchor="w", padx=8, pady=2)
        
        self._thumb_var = tk.BooleanVar(value=self._settings.get("embed_thumbnail", False))
        ThemedCheckbutton(sect, t, text=" Embed Thumbnail into file",
                          variable=self._thumb_var, command=self._save_advanced).pack(anchor="w", padx=8, pady=2)
        
        self._meta_var = tk.BooleanVar(value=self._settings.get("embed_metadata", True))
        ThemedCheckbutton(sect, t, text=" Embed Metadata (title, artist, etc.)",
                          variable=self._meta_var, command=self._save_advanced).pack(anchor="w", padx=8, pady=2)
        
        sleep_row = ThemedFrame(sect, t)
        sleep_row.pack(fill="x", padx=8, pady=4)
        ThemedLabel(sleep_row, t, text="Sleep Between Requests:").pack(side="left", padx=(0, 8))
        self._sleep_var = tk.StringVar(value=str(self._settings.get("sleep_interval", 0)))
        sleep_entry = ThemedEntry(sleep_row, t, textvariable=self._sleep_var, width=6)
        sleep_entry.pack(side="left")
        sleep_entry.bind("<FocusOut>", lambda _: self._save_advanced())
        ThemedLabel(sleep_row, t, text="seconds (0 = off, 2-5 = safe for rate-limited platforms)",
                    color_key="text_dim", font=(t["font_mono"], 8)).pack(side="left", padx=8)
        
        rate_row = ThemedFrame(sect, t)
        rate_row.pack(fill="x", padx=8, pady=4)
        ThemedLabel(rate_row, t, text="Speed Limit:").pack(side="left", padx=(0, 8))
        self._rate_var = tk.StringVar(value=self._settings.get("throttle_rate", ""))
        rate_combo = ttk.Combobox(
            rate_row, textvariable=self._rate_var,
            values=["", "500K", "1M", "2M", "5M", "10M", "20M", "50M"],
            state="normal", width=8, font=(t["font_mono"], 9))
        rate_combo.pack(side="left")
        rate_combo.bind("<<ComboboxSelected>>", lambda _: self._save_advanced())
        rate_combo.bind("<FocusOut>", lambda _: self._save_advanced())
        ThemedLabel(rate_row, t, text="(empty = unlimited)", color_key="text_dim",
                    font=(t["font_mono"], 8)).pack(side="left", padx=8)
    
    def _build_about_section(self, parent):
        t = self._theme
        sect = self._section(parent, "ℹ About")
        ThemedLabel(sect, t,
                    text=("VideoVortex — Ultimate Multi-Platform Video Downloader\n"
                        "Powered by yt-dlp | Python + tkinter\n\n"
                        "Supported Platforms:\n"
                        "✓ YouTube, TikTok, Instagram, Twitter/X, Facebook\n"
                        "✓ Snapchat (Spotlight & Public Stories)\n"
                        "✓ Twitch, Vimeo, Dailymotion, Reddit, Rumble\n"
                        "✓ SoundCloud, Bandcamp, and 1000+ more!\n\n"
                        "Features:\n"
                        "✓ Age restriction bypass\n"
                        "✓ Geo/Region restriction bypass\n"
                        "✓ Cookie-based login bypass\n"
                        "✓ Proxy support\n"
                        "✓ Up to 16K (15360p) video quality\n"
                        "✓ SponsorBlock integration\n"
                        "✓ Subtitle embedding\n"
                        "✓ Pause / Resume downloads\n"
                        "✓ Playlist batch downloads\n\n"
                        "Developed by CYBER CAPTAIN"),
                    color_key="text_dim", font=(t["font_mono"], 9),
                    justify="left").pack(anchor="w", padx=8, pady=4)
    
    def _apply_theme(self, key: str):
        theme = get_theme(key)
        self._settings.set("theme", key)
        self._on_tc(theme)
        self._highlight_theme_btn(key)
    
    def _highlight_theme_btn(self, key: str):
        for k, btn in self._theme_btns.items():
            th = THEMES[k]
            if k == key:
                btn.config(relief="solid", bd=2, highlightbackground=th["accent"], highlightthickness=2)
            else:
                btn.config(relief="flat", bd=1)
    
    def _browse_out(self):
        d = filedialog.askdirectory(initialdir=self._outdir_var.get())
        if d:
            self._outdir_var.set(d)
    
    def _save_dir(self):
        d = self._outdir_var.get()
        if d:
            self._settings.set("output_dir", d)
    
    def _save_parallel(self):
        self._settings.set("max_parallel", self._par_var.get())
    
    def _browse_cookies(self):
        f = filedialog.askopenfilename(title="Select cookies.txt",
                                        filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if f:
            self._cookies_file_var.set(f)
            self._save_bypass()
    
    def _save_bypass(self):
        self._settings.set("bypass_age", self._age_var.get())
        self._settings.set("bypass_geo", self._geo_var.get())
        self._settings.set("geo_bypass_country", self._country_var.get().strip().upper())
        self._settings.set("cookies_browser", self._browser_var.get())
        self._settings.set("cookies_file", self._cookies_file_var.get())
        self._settings.set("use_proxy", self._proxy_var.get())
        self._settings.set("proxy_url", self._proxy_url_var.get())
        self._on_bypass()
    
    def _save_advanced(self):
        try:
            max_res = int(self._max_res_var.get())
        except ValueError:
            max_res = 16000
        try:
            sleep = float(self._sleep_var.get())
        except ValueError:
            sleep = 0.0
        
        self._settings.set("max_resolution", max_res)
        self._settings.set("remove_sponsor", self._sponsor_var.get())
        self._settings.set("embed_subs", self._subs_var.get())
        self._settings.set("embed_thumbnail", self._thumb_var.get())
        self._settings.set("embed_metadata", self._meta_var.get())
        self._settings.set("sleep_interval", sleep)
        self._settings.set("throttle_rate", self._rate_var.get())
        self._on_bypass()
    
    def apply_theme(self, theme: dict):
        self._theme = theme
        self.config(bg=theme["bg"])
        self._highlight_theme_btn(self._settings.get("theme", "hacker_green"))