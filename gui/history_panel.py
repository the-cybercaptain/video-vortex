"""Download history panel with search/filter."""

import tkinter as tk
from tkinter import ttk
import time

from gui.widgets import ThemedFrame, ThemedLabel, ThemedButton, ThemedEntry


class HistoryPanel(ThemedFrame):
    def __init__(self, parent, theme: dict, history_mgr, **kwargs):
        super().__init__(parent, theme, **kwargs)
        self._theme = theme
        self._history = history_mgr
        self._build_ui()
    
    def _build_ui(self):
        t = self._theme
        
        hdr = ThemedFrame(self, t)
        hdr.pack(fill="x", padx=10, pady=(8, 4))
        
        ThemedLabel(hdr, t, text="◎ DOWNLOAD HISTORY",
                    font=(t["font_mono"], 10, "bold")).pack(side="left")
        
        ThemedButton(hdr, t, text=" Clear All ", command=self._clear_all,
                     font=(t["font_mono"], 8)).pack(side="right")
        
        s_row = ThemedFrame(self, t)
        s_row.pack(fill="x", padx=10, pady=(0, 4))
        
        ThemedLabel(s_row, t, text="Filter:").pack(side="left", padx=(0, 6))
        self._filter_var = tk.StringVar()
        fe = ThemedEntry(s_row, t, textvariable=self._filter_var, width=40)
        fe.pack(side="left")
        self._filter_var.trace_add("write", lambda *_: self.refresh())
        
        self._status_var = tk.StringVar(value="All")
        sm = ttk.Combobox(s_row, textvariable=self._status_var,
                          values=["All", "Completed", "Cancelled", "Error"],
                          state="readonly", width=12, font=(t["font_mono"], 9))
        sm.pack(side="left", padx=8)
        sm.bind("<<ComboboxSelected>>", lambda _: self.refresh())
        
        cols = ("Time", "Platform", "Title", "Status", "URL")
        self._tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        widths = [140, 100, 280, 90, 260]
        for col, w in zip(cols, widths):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, minwidth=60)
        
        vsb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y", padx=(0, 10))
        self._tree.pack(fill="both", expand=True, padx=10, pady=4)
        self._tree.bind("<Delete>", self._delete_selected)
        
        self._apply_tree_style()
        self.refresh()
    
    def refresh(self, *_):
        self._tree.delete(*self._tree.get_children())
        items = self._history.get_all()
        q = self._filter_var.get().lower()
        sf = self._status_var.get()
        
        for item in items:
            if sf != "All" and item["status"] != sf:
                continue
            if q and q not in (item["title"] + item["url"] + item["platform"]).lower():
                continue
            
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(item["timestamp"]))
            tags = (item["status"].lower(),)
            self._tree.insert("", "end", tags=tags, values=(
                ts, item["platform"], item["title"][:50],
                item["status"], item["url"][:60],
            ))
    
    def add_entry(self, url, title, platform, status, filename=""):
        self._history.add(url, title, platform, status, filename)
        self.refresh()
    
    def update_entry(self, url, status, filename=""):
        self._history.update_status(url, status, filename)
        self.refresh()
    
    def _clear_all(self):
        self._history.clear()
        self.refresh()
    
    def _delete_selected(self, _):
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        self._history.delete_entry(idx)
        self.refresh()
    
    def _apply_tree_style(self):
        t = self._theme
        st = ttk.Style()
        st.theme_use("clam")
        st.configure("Treeview",
                     background=t["bg2"], foreground=t["text"],
                     fieldbackground=t["bg2"], rowheight=26,
                     font=(t["font_mono"], 9))
        st.configure("Treeview.Heading",
                     background=t["bg3"], foreground=t["accent"],
                     font=(t["font_mono"], 9, "bold"))
        st.map("Treeview",
               background=[("selected", t["btn_hover"])],
               foreground=[("selected", t["accent"])])
        self._tree.tag_configure("completed", foreground=t["success"])
        self._tree.tag_configure("cancelled", foreground=t["text_dim"])
        self._tree.tag_configure("error", foreground=t["error"])
    
    def apply_theme(self, theme: dict):
        self._theme = theme
        self.config(bg=theme["bg"])
        self._apply_tree_style()