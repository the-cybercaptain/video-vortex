"""Active downloads panel with progress bars and controls."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Optional

from gui.widgets import (ThemedFrame, ThemedLabel, ThemedButton, ProgressBar)
from core.downloader import DownloadManager, DownloadStatus, DownloadTask


class ActiveDownloadsPanel(ThemedFrame):
    """Scrollable list of active download task cards."""
    
    def __init__(self, parent, theme: dict, manager: DownloadManager,
                 on_select: Callable, **kwargs):
        super().__init__(parent, theme, **kwargs)
        self._theme = theme
        self._mgr = manager
        self._on_sel = on_select
        self._cards: Dict[str, "_TaskCard"] = {}
        self._build_ui()
        self._poll()
    
    def _build_ui(self):
        t = self._theme
        
        hdr = ThemedFrame(self, t)
        hdr.pack(fill="x", padx=10, pady=(8, 0))
        
        ThemedLabel(hdr, t, text="▼ ACTIVE DOWNLOADS",
                    font=(t["font_mono"], 11, "bold")).pack(side="left")
        
        self._count_lbl = ThemedLabel(hdr, t, text="[0]", color_key="text_dim",
                                       font=(t["font_mono"], 10))
        self._count_lbl.pack(side="left", padx=8)
        
        # Control buttons
        self._pause_all_btn = ThemedButton(hdr, t, text="⏸ Pause All",
                                            command=self._pause_all,
                                            font=(t["font_mono"], 9, "bold"),
                                            padx=8, pady=3)
        self._pause_all_btn.pack(side="right", padx=2)
        
        self._resume_all_btn = ThemedButton(hdr, t, text="▶ Resume All",
                                             command=self._resume_all,
                                             font=(t["font_mono"], 9, "bold"),
                                             padx=8, pady=3)
        self._resume_all_btn.pack(side="right", padx=2)
        
        self._cancel_all_btn = ThemedButton(hdr, t, text="✕ Cancel All",
                                             command=self._cancel_all,
                                             font=(t["font_mono"], 9, "bold"),
                                             padx=8, pady=3)
        self._cancel_all_btn.pack(side="right", padx=2)
        
        self._remove_all_btn = ThemedButton(hdr, t, text="🗑 Remove All",
                                             command=self._remove_all,
                                             font=(t["font_mono"], 9, "bold"),
                                             padx=8, pady=3)
        self._remove_all_btn.pack(side="right", padx=2)
        
        # Scrollable container
        container = ThemedFrame(self, t)
        container.pack(fill="both", expand=True, padx=10, pady=4)
        
        self._canvas = tk.Canvas(container, bg=t["bg"], highlightthickness=0, bd=0)
        vsb = tk.Scrollbar(container, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        
        self._inner = ThemedFrame(self._canvas, t)
        self._win = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        
        self._inner.bind("<Configure>", self._on_inner_conf)
        self._canvas.bind("<Configure>", self._on_canvas_conf)
        self._canvas.bind_all("<MouseWheel>", lambda e: self._canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        
        self._empty_lbl = ThemedLabel(
            self._inner, t,
            text="\n    No active downloads.\n    Paste a URL above to start.\n",
            color_key="text_dim", font=(t["font_mono"], 11),
        )
        self._empty_lbl.pack(pady=30)
    
    def _on_inner_conf(self, _):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
    
    def _on_canvas_conf(self, e):
        self._canvas.itemconfig(self._win, width=e.width)
    
    def add_task(self, task: DownloadTask):
        if self._empty_lbl.winfo_ismapped():
            self._empty_lbl.pack_forget()
        
        card = _TaskCard(
            self._inner, self._theme, task,
            on_pause=lambda tid: self._mgr.pause(tid),
            on_resume=lambda tid: self._mgr.resume(tid),
            on_cancel=lambda tid: self._mgr.cancel(tid),
            on_remove=self._remove_card,
            on_click=lambda tid: self._on_task_click(tid, task),
        )
        card.pack(fill="x", pady=4, padx=2)
        self._cards[task.id] = card
        self._canvas.yview_moveto(1.0)
    
    def _on_task_click(self, task_id, task):
        self._on_sel(task_id, task)
    
    def refresh(self, task_id: Optional[str] = None):
        if task_id:
            card = self._cards.get(task_id)
            if card:
                task = self._mgr.get_task(task_id)
                if task:
                    card.update_task(task)
        else:
            for tid in list(self._cards.keys()):
                if self._mgr.get_task(tid) is None:
                    c = self._cards.pop(tid, None)
                    if c:
                        c.destroy()
            
            for tid, card in self._cards.items():
                task = self._mgr.get_task(tid)
                if task:
                    card.update_task(task)
        
        tasks = self._mgr.get_all_tasks()
        active = sum(1 for t in tasks if t.status == DownloadStatus.DOWNLOADING)
        paused = sum(1 for t in tasks if t.status == DownloadStatus.PAUSED)
        completed = sum(1 for t in tasks if t.status == DownloadStatus.COMPLETED)
        
        self._count_lbl.config(text=f"[{active} active, {paused} paused, {completed} done]")
        
        has_downloading = any(t.status == DownloadStatus.DOWNLOADING for t in tasks)
        has_paused = any(t.status == DownloadStatus.PAUSED for t in tasks)
        has_cancelled_or_error = any(
            t.status in (DownloadStatus.CANCELLED, DownloadStatus.ERROR, DownloadStatus.COMPLETED)
            for t in tasks)
        has_active = any(t.status in (DownloadStatus.DOWNLOADING, DownloadStatus.PAUSED, DownloadStatus.QUEUED)
                        for t in tasks)
        
        self._pause_all_btn.config(state="normal" if has_downloading else "disabled")
        self._resume_all_btn.config(state="normal" if has_paused else "disabled")
        self._cancel_all_btn.config(state="normal" if has_active else "disabled")
        self._remove_all_btn.config(state="normal" if has_cancelled_or_error and not has_active else "disabled")
        
        if not self._cards and not tasks:
            self._empty_lbl.pack(pady=30)
        elif self._empty_lbl.winfo_ismapped() and self._cards:
            self._empty_lbl.pack_forget()
    
    def _remove_card(self, task_id: str):
        task = self._mgr.get_task(task_id)
        if task and task.status in (DownloadStatus.DOWNLOADING, DownloadStatus.QUEUED, DownloadStatus.PAUSED):
            self._mgr.cancel(task_id)
        self.after(100, lambda: self._do_remove(task_id))
    
    def _do_remove(self, task_id: str):
        self._mgr.remove(task_id)
        card = self._cards.pop(task_id, None)
        if card:
            card.destroy()
        self.refresh()
    
    def _pause_all(self):
        for task in self._mgr.get_all_tasks():
            if task.status == DownloadStatus.DOWNLOADING:
                self._mgr.pause(task.id)
        self.refresh()
    
    def _resume_all(self):
        for task in self._mgr.get_all_tasks():
            if task.status == DownloadStatus.PAUSED:
                self._mgr.resume(task.id)
        self.refresh()
    
    def _cancel_all(self):
        for task in self._mgr.get_all_tasks():
            if task.status in (DownloadStatus.DOWNLOADING, DownloadStatus.QUEUED, DownloadStatus.PAUSED):
                self._mgr.cancel(task.id)
        self.refresh()
    
    def _remove_all(self):
        tasks = self._mgr.get_all_tasks()
        for task in tasks:
            if task.status in (DownloadStatus.CANCELLED, DownloadStatus.COMPLETED, DownloadStatus.ERROR):
                self._mgr.remove(task.id)
        for card in list(self._cards.values()):
            card.destroy()
        self._cards.clear()
        self.refresh()
    
    def _poll(self):
        self.refresh()
        self.after(500, self._poll)
    
    def apply_theme(self, theme: dict):
        self._theme = theme
        self.config(bg=theme["bg"])
        self._canvas.config(bg=theme["bg"])
        self._inner.config(bg=theme["bg"])
        for card in self._cards.values():
            card.apply_theme(theme)


class _TaskCard(ThemedFrame):
    """Single download task row with progress bar and controls."""
    
    def __init__(self, parent, theme: dict, task: DownloadTask, on_pause, on_resume,
                 on_cancel, on_remove, on_click):
        super().__init__(parent, theme, highlightthickness=1, highlightbackground=theme["border"])
        self._theme = theme
        self._task_id = task.id
        self._task = task
        self._on_pause = on_pause
        self._on_resume = on_resume
        self._on_cancel = on_cancel
        self._on_remove = on_remove
        self._on_click = on_click
        
        t = theme
        
        # Row 1: Title + Status
        r1 = ThemedFrame(self, t)
        r1.pack(fill="x", padx=8, pady=(6, 2))
        
        self._title_lbl = ThemedLabel(r1, t, text=task.title[:50], font=(t["font_mono"], 10, "bold"))
        self._title_lbl.pack(side="left")
        
        self._status_lbl = ThemedLabel(r1, t, text=task.status.value,
                                        font=(t["font_mono"], 8, "bold"))
        self._status_lbl.pack(side="right")
        
        # Row 2: Progress bar
        r2 = ThemedFrame(self, t)
        r2.pack(fill="x", padx=8, pady=2)
        
        self._bar = ProgressBar(r2, t, width=100, height=14)
        self._bar.pack(fill="x", expand=True)
        
        # Row 3: Speed / ETA / Size
        r3 = ThemedFrame(self, t)
        r3.pack(fill="x", padx=8, pady=2)
        
        self._speed_lbl = ThemedLabel(r3, t, text="", color_key="text_dim",
                                       font=(t["font_mono"], 8))
        self._speed_lbl.pack(side="left")
        
        self._eta_lbl = ThemedLabel(r3, t, text="", color_key="text_dim",
                                     font=(t["font_mono"], 8))
        self._eta_lbl.pack(side="left", padx=10)
        
        self._size_lbl = ThemedLabel(r3, t, text="", color_key="text_dim",
                                      font=(t["font_mono"], 8))
        self._size_lbl.pack(side="right")
        
        self._dl_lbl = ThemedLabel(r3, t, text="", color_key="accent",
                                    font=(t["font_mono"], 8, "bold"))
        self._dl_lbl.pack(side="right", padx=4)
        
        # Row 4: Buttons
        r4 = ThemedFrame(self, t)
        r4.pack(fill="x", padx=8, pady=(2, 6))
        
        self._pause_btn = ThemedButton(r4, t, text="⏸", command=self._pause,
                                        font=(t["font_mono"], 9), padx=6)
        self._pause_btn.pack(side="left", padx=2)
        
        self._resume_btn = ThemedButton(r4, t, text="▶", command=self._resume,
                                         font=(t["font_mono"], 9), padx=6)
        self._resume_btn.pack(side="left", padx=2)
        
        self._cancel_btn = ThemedButton(r4, t, text="✕", command=self._cancel,
                                         font=(t["font_mono"], 9), padx=6)
        self._cancel_btn.pack(side="left", padx=2)
        
        self._remove_btn = ThemedButton(r4, t, text="🗑", command=self._remove,
                                         font=(t["font_mono"], 9), padx=6)
        self._remove_btn.pack(side="right", padx=2)
        
        self.update_task(task)
        self._bind_click_recursive(self)
    
    def _bind_click_recursive(self, widget):
        """Sare child widgets pe click binding lagao taake kahi bhi click kaam kare."""
        try:
            # Buttons pe bind mat karo — unka apna kaam hai
            if not isinstance(widget, tk.Button):
                widget.bind("<Button-1>", lambda e: self._on_click(self._task_id))
        except Exception:
            pass
        for child in widget.winfo_children():
            self._bind_click_recursive(child)
    
    def update_task(self, task: DownloadTask):
        self._task = task
        st = task.status
        
        self._title_lbl.config(text=task.title[:50])
        self._status_lbl.config(text=st.value)
        self._bar.set_progress(task.progress)
        
        if task.speed:
            self._speed_lbl.config(text=f"⚡ {task.speed}")
        if task.eta:
            self._eta_lbl.config(text=f"⏱ {task.eta}")
        if task.total_size:
            self._size_lbl.config(text=f"📦 {task.total_size}")
        if task.downloaded:
            self._dl_lbl.config(text=f" {task.downloaded}")
        
        # Button states
        if st == DownloadStatus.DOWNLOADING:
            self._pause_btn.config(state="normal")
            self._resume_btn.config(state="disabled")
            self._cancel_btn.config(state="normal")
            self._remove_btn.config(state="disabled")
        elif st == DownloadStatus.PAUSED:
            self._pause_btn.config(state="disabled")
            self._resume_btn.config(state="normal")
            self._cancel_btn.config(state="normal")
            self._remove_btn.config(state="disabled")
        elif st == DownloadStatus.QUEUED:
            self._pause_btn.config(state="disabled")
            self._resume_btn.config(state="disabled")
            self._cancel_btn.config(state="normal")
            self._remove_btn.config(state="disabled")
        elif st in (DownloadStatus.CANCELLED, DownloadStatus.COMPLETED, DownloadStatus.ERROR):
            self._pause_btn.config(state="disabled")
            self._resume_btn.config(state="disabled")
            self._cancel_btn.config(state="disabled")
            self._remove_btn.config(state="normal")
        
        color_map = {
            DownloadStatus.COMPLETED: self._theme["success"],
            DownloadStatus.ERROR: self._theme["error"],
            DownloadStatus.PAUSED: self._theme["warn"],
            DownloadStatus.CANCELLED: self._theme["text_dim"],
            DownloadStatus.DOWNLOADING: self._theme["accent"],
            DownloadStatus.QUEUED: self._theme["accent2"],
        }
        self.config(highlightbackground=color_map.get(st, self._theme["border"]))
    
    def _pause(self):
        self._on_pause(self._task_id)
    
    def _resume(self):
        self._on_resume(self._task_id)
    
    def _cancel(self):
        self._on_cancel(self._task_id)
    
    def _remove(self):
        self._on_remove(self._task_id)
    
    def apply_theme(self, theme: dict):
        self._theme = theme
        self.config(bg=theme["bg"], highlightbackground=theme["border"])
        try:
            self._bar.apply_theme(theme)
        except Exception:
            pass