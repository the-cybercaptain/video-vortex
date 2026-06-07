"""Custom themed tkinter widgets for VideoVortex."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class ThemedFrame(tk.Frame):
    def __init__(self, parent, theme: dict, **kwargs):
        super().__init__(parent, bg=kwargs.pop("bg", theme["bg"]), **kwargs)
        self.theme = theme
    
    def apply_theme(self, theme: dict):
        self.theme = theme
        self.config(bg=theme["bg"])


class ThemedLabel(tk.Label):
    def __init__(self, parent, theme: dict, text="", color_key="text", **kwargs):
        super().__init__(
            parent,
            text=text,
            bg=kwargs.pop("bg", theme["bg"]),
            fg=kwargs.pop("fg", theme[color_key]),
            font=kwargs.pop("font", (theme["font_mono"], 10)),
            **kwargs,
        )
        self.theme = theme
    
    def apply_theme(self, theme: dict):
        self.theme = theme
        self.config(bg=theme["bg"])


class ThemedButton(tk.Button):
    def __init__(self, parent, theme: dict, text="", command=None, accent=False, **kwargs):
        fg = theme["accent"] if accent else theme["text"]
        self._t = theme
        self._ac = accent
        super().__init__(
            parent,
            text=text,
            command=command,
            bg=kwargs.pop("bg", theme["btn_bg"]),
            fg=kwargs.pop("fg", fg),
            activebackground=theme["btn_hover"],
            activeforeground=theme["accent"] if accent else theme["text_bright"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=kwargs.pop("font", (theme["font_mono"], 10)),
            **kwargs,
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _on_enter(self, _):
        self.config(bg=self._t["btn_hover"], fg=self._t["accent"] if self._ac else self._t["text_bright"])
    
    def _on_leave(self, _):
        self.config(bg=self._t["btn_bg"], fg=self._t["accent"] if self._ac else self._t["text"])
    
    def apply_theme(self, theme: dict):
        self._t = theme
        self.config(
            bg=theme["btn_bg"],
            fg=theme["accent"] if self._ac else theme["text"],
            activebackground=theme["btn_hover"],
        )


class ThemedEntry(tk.Entry):
    def __init__(self, parent, theme: dict, **kwargs):
        super().__init__(
            parent,
            bg=kwargs.pop("bg", theme["entry_bg"]),
            fg=kwargs.pop("fg", theme["accent"]),
            insertbackground=theme["accent"],
            relief="flat",
            bd=1,
            highlightthickness=1,
            highlightcolor=theme["entry_border"],
            highlightbackground=theme["border"],
            font=kwargs.pop("font", (theme["font_mono"], 11)),
            **kwargs,
        )
        self.theme = theme
    
    def apply_theme(self, theme: dict):
        self.theme = theme
        self.config(
            bg=theme["entry_bg"], fg=theme["accent"],
            insertbackground=theme["accent"],
            highlightcolor=theme["entry_border"],
            highlightbackground=theme["border"],
        )


class GlowLabel(tk.Label):
    """Label with pulsing accent color for titles."""
    def __init__(self, parent, theme: dict, text="", **kwargs):
        self._theme = theme
        self._toggle = False
        super().__init__(
            parent,
            text=text,
            bg=kwargs.pop("bg", theme["bg"]),
            fg=kwargs.pop("fg", theme["accent"]),
            font=kwargs.pop("font", (theme["font_mono"], 14, "bold")),
            **kwargs,
        )
        self._pulse()
    
    def _pulse(self):
        if not self.winfo_exists():
            return
        col = self._theme["accent"] if self._toggle else self._theme["accent3"]
        try:
            self.config(fg=col)
        except Exception:
            return
        self._toggle = not self._toggle
        self.after(900, self._pulse)
    
    def apply_theme(self, theme: dict):
        self._theme = theme
        self.config(bg=theme["bg"], fg=theme["accent"])


class ProgressBar(ttk.Progressbar):
    """Themed progress bar."""
    _style_count = 0
    
    def __init__(self, parent, theme: dict, width=300, height=16, **kwargs):
        ProgressBar._style_count += 1
        self._style_name = f"VV{ProgressBar._style_count}.Horizontal.TProgressbar"
        self._theme = theme
        
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except:
            pass
        
        style.configure(
            self._style_name,
            background=theme["progress_fg"],
            troughcolor=theme["progress_bg"],
            bordercolor=theme["border"],
            darkcolor=theme["progress_fg"],
            lightcolor=theme["progress_fg"],
        )
        
        super().__init__(
            parent,
            mode="determinate",
            length=width,
            style=self._style_name,
            **kwargs,
        )
    
    def set_progress(self, pct: float):
        self["value"] = pct
    
    def apply_theme(self, theme: dict):
        self._theme = theme
        style = ttk.Style()
        style.configure(
            self._style_name,
            background=theme["progress_fg"],
            troughcolor=theme["progress_bg"],
            bordercolor=theme["border"],
            darkcolor=theme["progress_fg"],
            lightcolor=theme["progress_fg"],
        )


class ThemedCheckbutton(tk.Checkbutton):
    """Themed checkbutton."""
    def __init__(self, parent, theme: dict, text="", variable=None, **kwargs):
        self._theme = theme
        super().__init__(
            parent,
            text=text,
            variable=variable,
            bg=theme["bg"],
            fg=theme["text"],
            selectcolor=theme["bg2"],
            activebackground=theme["btn_hover"],
            activeforeground=theme["accent"],
            font=(theme["font_mono"], 9),
            relief="flat",
            cursor="hand2",
            **kwargs,
        )