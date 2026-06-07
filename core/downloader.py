"""
Parallel video/audio downloader engine using yt-dlp DIRECT integration.
FIXED: YouTube & Playlist downloads working properly with pause/resume.
FIXED: Individual cancel button now properly stops downloads.
FIXED: Download complete status now shows "Completed" immediately.
ADDED: Snapchat support with custom headers and format handling
"""

import threading
import os
import uuid
import time
from enum import Enum
from typing import Callable, Optional, Dict, List
from dataclasses import dataclass, field
import yt_dlp

class DownloadStatus(Enum):
    QUEUED = "Queued"
    DOWNLOADING = "Downloading"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    ERROR = "Error"


@dataclass
class DownloadTask:
    id: str
    url: str
    title: str
    platform: str
    format_id: str
    is_audio: bool
    output_dir: str
    audio_quality: str = "192"
    
    status: DownloadStatus = DownloadStatus.QUEUED
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    downloaded: str = ""
    total_size: str = ""
    filename: str = ""
    error_msg: str = ""
    added_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    
    # Bypass / feature flags
    bypass_geo: bool = True
    bypass_age: bool = True
    geo_bypass_country: str = "US"
    use_cookies: bool = False
    cookies_file: str = ""
    cookies_browser: str = ""
    use_proxy: bool = False
    proxy_url: str = ""
    max_resolution: int = 16000
    embed_subs: bool = False
    embed_thumbnail: bool = False
    embed_metadata: bool = True
    remove_sponsor: bool = True
    throttle_rate: str = ""
    sleep_interval: float = 0.0
    no_playlist: bool = False
    write_subs: bool = False
    
    # internals
    thumbnail_url: str = field(default="", repr=False)
    _pause_event: threading.Event = field(default_factory=threading.Event, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _ydl: Optional[yt_dlp.YoutubeDL] = field(default=None, repr=False)
    _should_stop: bool = field(default=False, repr=False)
    _worker_thread: Optional[threading.Thread] = field(default=None, repr=False)


class DownloadManager:
    """
    Manages multiple concurrent yt-dlp downloads using direct yt-dlp integration.
    Thread-safe with pause/resume support.
    """
    MAX_PARALLEL = 10
    
    def __init__(self, on_update: Optional[Callable[[str], None]] = None):
        self.tasks: Dict[str, DownloadTask] = {}
        self.lock = threading.Lock()
        self.semaphore = threading.Semaphore(self.MAX_PARALLEL)
        self.on_update = on_update or (lambda tid: None)
    
    # Public API
    
    def add_download(
        self,
        url: str,
        title: str,
        platform: str,
        format_id: str,
        output_dir: str,
        is_audio: bool = False,
        audio_quality: str = "192",
        bypass_geo: bool = True,
        bypass_age: bool = True,
        geo_bypass_country: str = "US",
        use_cookies: bool = False,
        cookies_file: str = "",
        cookies_browser: str = "",
        use_proxy: bool = False,
        proxy_url: str = "",
        embed_subs: bool = False,
        embed_thumbnail: bool = False,
        embed_metadata: bool = True,
        remove_sponsor: bool = True,
        max_resolution: int = 16000,
        sleep_interval: float = 0.0,
        throttle_rate: str = "",
        no_playlist: bool = False,
        write_subs: bool = False,
    ) -> str:
        """Create and immediately start a download. Returns task ID."""
        tid = str(uuid.uuid4())[:8]
        task = DownloadTask(
            id=tid,
            url=url,
            title=title,
            platform=platform,
            format_id=format_id,
            is_audio=is_audio,
            output_dir=output_dir,
            audio_quality=audio_quality,
            bypass_geo=bypass_geo,
            bypass_age=bypass_age,
            geo_bypass_country=geo_bypass_country,
            use_cookies=use_cookies,
            cookies_file=cookies_file,
            cookies_browser=cookies_browser,
            use_proxy=use_proxy,
            proxy_url=proxy_url,
            embed_subs=embed_subs,
            embed_thumbnail=embed_thumbnail,
            embed_metadata=embed_metadata,
            remove_sponsor=remove_sponsor,
            max_resolution=max_resolution,
            sleep_interval=sleep_interval,
            throttle_rate=throttle_rate,
            no_playlist=no_playlist,
            write_subs=write_subs,
        )
        task._pause_event.set()
        task._should_stop = False
        with self.lock:
            self.tasks[tid] = task
        t = threading.Thread(target=self._worker, args=(tid,), daemon=True)
        task._worker_thread = t
        t.start()
        return tid
    
    def pause(self, task_id: str):
        task = self.tasks.get(task_id)
        if task and task.status == DownloadStatus.DOWNLOADING:
            task._pause_event.clear()
            task.status = DownloadStatus.PAUSED
            if task._ydl:
                try:
                    task._ydl.params['quiet'] = True
                except Exception:
                    pass
            self.on_update(task_id)
    
    def resume(self, task_id: str):
        task = self.tasks.get(task_id)
        if task and task.status == DownloadStatus.PAUSED:
            task._pause_event.set()
            task._should_stop = False
            task.status = DownloadStatus.DOWNLOADING
            t = threading.Thread(target=self._worker, args=(task_id,), daemon=True)
            task._worker_thread = t
            t.start()
            self.on_update(task_id)
    
    def cancel(self, task_id: str):
        """Cancel a specific download - COMPLETELY STOPS IT"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        task._should_stop = True
        task._pause_event.set()
        task.status = DownloadStatus.CANCELLED
        
        if task._ydl:
            try:
                task._ydl.params['quiet'] = True
            except Exception:
                pass
        
        self.on_update(task_id)
    
    def cancel_all(self):
        for tid in list(self.tasks.keys()):
            st = self.tasks[tid].status
            if st in (DownloadStatus.DOWNLOADING, DownloadStatus.QUEUED, DownloadStatus.PAUSED):
                self.cancel(tid)
    
    def remove(self, task_id: str):
        self.cancel(task_id)
        with self.lock:
            self.tasks.pop(task_id, None)
        self.on_update(task_id)
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[DownloadTask]:
        with self.lock:
            return list(self.tasks.values())
    
    # Internal worker
    
    def _worker(self, task_id: str):
        task = self.tasks.get(task_id)
        if not task:
            return
        
        self.semaphore.acquire()
        try:
            if task._should_stop or task.status == DownloadStatus.CANCELLED:
                return
            
            if task.status == DownloadStatus.COMPLETED:
                return
            
            task.status = DownloadStatus.DOWNLOADING
            task._should_stop = False
            self.on_update(task_id)
            
            ydl_opts = self._build_opts(task)
            
            # Snapchat specific format selection override
            is_snapchat = "snapchat" in task.platform.lower() or "snapchat" in task.url.lower()
            if is_snapchat:
                # Snapchat ke liye simplest format use karo
                if not task.format_id or task.format_id == "best":
                    ydl_opts['format'] = 'best[ext=mp4]/best'
                ydl_opts['merge_output_format'] = None  # No merging needed for Snapchat
            
            # Track if download completed via hook
            download_finished = False
            
            def progress_hook(d):
                nonlocal download_finished
                
                if task._should_stop or task.status == DownloadStatus.CANCELLED:
                    task.status = DownloadStatus.CANCELLED
                    self.on_update(task_id)
                    raise Exception("Cancelled by user")
                
                if not task._pause_event.is_set():
                    task.status = DownloadStatus.PAUSED
                    self.on_update(task_id)
                    raise Exception("Paused by user")
                
                if d['status'] == 'downloading':
                    total_bytes = d.get('total_bytes')
                    total_bytes_estimate = d.get('total_bytes_estimate')
                    
                    if total_bytes and total_bytes > 0:
                        task.progress = (d['downloaded_bytes'] / total_bytes) * 100
                        task.total_size = self._format_size(total_bytes)
                    elif total_bytes_estimate and total_bytes_estimate > 0:
                        task.progress = (d['downloaded_bytes'] / total_bytes_estimate) * 100
                        task.total_size = self._format_size(total_bytes_estimate)
                    else:
                        task.progress = 0
                        task.total_size = f"{self._format_size(d['downloaded_bytes'])} (unknown total)"
                    
                    if d.get('speed'):
                        task.speed = self._format_speed(d['speed'])
                    if d.get('eta'):
                        task.eta = self._format_time(d['eta'])
                    
                    task.downloaded = f"{task.progress:.1f}%" if task.progress > 0 else f"{self._format_size(d['downloaded_bytes'])}"
                    self.on_update(task_id)
                
                elif d['status'] == 'finished':
                    # DOWNLOAD COMPLETE! - Immediately update status
                    download_finished = True
                    task.progress = 100.0
                    task.downloaded = "100%"
                    task.speed = ""
                    task.eta = ""
                    task.status = DownloadStatus.COMPLETED
                    task.finished_at = time.time()
                    self.on_update(task_id)
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                task._ydl = ydl
                try:
                    info = ydl.extract_info(task.url, download=True)
                    
                    if task._should_stop or task.status == DownloadStatus.CANCELLED:
                        task.status = DownloadStatus.CANCELLED
                        self.on_update(task_id)
                        return
                    
                    if info:
                        if 'requested_downloads' in info and info['requested_downloads']:
                            task.filename = info['requested_downloads'][0].get('filepath', '')
                        elif '_filename' in info:
                            task.filename = info['_filename']
                    
                    # Agar progress_hook ne already COMPLETED set kar diya hai toh dobara mat karo
                    if not download_finished:
                        if (task.status != DownloadStatus.PAUSED and 
                            task.status != DownloadStatus.CANCELLED and 
                            not task._should_stop):
                            task.status = DownloadStatus.COMPLETED
                            task.progress = 100
                            task.finished_at = time.time()
                            self.on_update(task_id)
                            
                except Exception as e:
                    # Snapchat specific error handling
                    if is_snapchat and "unable to download" in str(e).lower():
                        # Try alternative method for Snapchat
                        try:
                            alt_opts = ydl_opts.copy()
                            alt_opts['format'] = 'best'
                            alt_opts['extract_flat'] = False
                            with yt_dlp.YoutubeDL(alt_opts) as ydl2:
                                info2 = ydl2.extract_info(task.url, download=True)
                                if info2:
                                    task.status = DownloadStatus.COMPLETED
                                    task.progress = 100
                                    task.finished_at = time.time()
                                    self.on_update(task_id)
                                    return
                        except:
                            pass
                    
                    if task._should_stop or task.status == DownloadStatus.CANCELLED:
                        task.status = DownloadStatus.CANCELLED
                    elif not task._pause_event.is_set():
                        task.status = DownloadStatus.PAUSED
                    else:
                        task.status = DownloadStatus.ERROR
                        task.error_msg = str(e)
                    self.on_update(task_id)
                finally:
                    task._ydl = None
                    
        except Exception as e:
            if task._should_stop:
                task.status = DownloadStatus.CANCELLED
            elif not task._pause_event.is_set():
                task.status = DownloadStatus.PAUSED
            else:
                task.status = DownloadStatus.ERROR
                task.error_msg = str(e)
            self.on_update(task_id)
        finally:
            self.semaphore.release()
    
    def _build_opts(self, task: DownloadTask) -> dict:
        import platform
        
        os.makedirs(task.output_dir, exist_ok=True)
        
        opts = {
            'outtmpl': os.path.join(task.output_dir, '%(title).100s.%(ext)s'),
            'noplaylist': task.no_playlist,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'retries': 10,
            'fragment_retries': 10,
            'continuedl': True,
        }
        
        # Age restriction bypass
        if task.bypass_age:
            opts['age_limit'] = 99
        
        # Geo bypass
        if task.bypass_geo:
            opts['geo_bypass'] = True
            opts['geo_bypass_country'] = task.geo_bypass_country
        
        # Cookies
        if task.cookies_browser and task.cookies_browser.lower() not in ("", "none"):
            opts['cookiesfrombrowser'] = (task.cookies_browser,)
        elif task.use_cookies and task.cookies_file and os.path.exists(task.cookies_file):
            opts['cookiefile'] = task.cookies_file
        
        # Proxy
        if task.use_proxy and task.proxy_url:
            opts['proxy'] = task.proxy_url
        
        # Rate limit
        if task.throttle_rate:
            opts['ratelimit'] = self._parse_rate(task.throttle_rate)
        
        # Sleep interval
        if task.sleep_interval > 0:
            opts['sleep_interval'] = task.sleep_interval
        
        # Check if it's Snapchat
        is_snapchat = "snapchat" in task.platform.lower() or "snapchat" in task.url.lower()
        
        if is_snapchat:
            # Cross-platform User-Agent (Windows, Mac, Linux sab par kaam karega)
            system = platform.system()
            if system == "Windows":
                user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            elif system == "Darwin":
                user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            else:  # Linux and others
                user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            
            opts['user_agent'] = user_agent
            opts['headers'] = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            # Snapchat ke liye simple format selection
            if task.is_audio:
                opts['format'] = 'bestaudio/best'
            else:
                opts['format'] = 'best[ext=mp4]/best'
                opts['merge_output_format'] = None
        else:
            # Format selection for other platforms
            if task.is_audio:
                opts['format'] = 'bestaudio/best'
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': task.audio_quality,
                }]
            else:
                max_h = min(task.max_resolution, 16000)
                if task.format_id and task.format_id != "best":
                    opts['format'] = f"{task.format_id}+bestaudio/best"
                else:
                    opts['format'] = f'bestvideo[height<={max_h}]+bestaudio/best[height<={max_h}]/best'
                opts['merge_output_format'] = 'mp4'
        
        # YouTube specific: SponsorBlock (only for non-Snapchat)
        plat = task.platform.lower()
        if not is_snapchat and "youtube" in plat and task.remove_sponsor:
            opts['postprocessors'] = opts.get('postprocessors', [])
            opts['postprocessors'].append({
                'key': 'SponsorBlock',
                'categories': ['sponsor', 'intro', 'outro', 'selfpromo', 'preview', 'filler']
            })
        
        # Metadata (skip for Snapchat to avoid issues)
        if not is_snapchat and task.embed_metadata:
            opts['postprocessors'] = opts.get('postprocessors', [])
            opts['postprocessors'].append({'key': 'FFmpegMetadata'})
        
        # Thumbnail (skip for Snapchat)
        if not is_snapchat and task.embed_thumbnail:
            opts['writethumbnail'] = True
            opts['embedthumbnail'] = True
        
        # Subtitles (skip for Snapchat)
        if not is_snapchat and task.embed_subs:
            opts['writesubtitles'] = True
            opts['writeautomaticsub'] = True
            opts['subtitleslangs'] = ['en', 'ur', 'ar']
            opts['embedsubs'] = True
        
        return opts

    @staticmethod
    def _format_size(bytes_val: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} TB"
    
    @staticmethod
    def _format_speed(speed: float) -> str:
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if speed < 1024:
                return f"{speed:.1f} {unit}"
            speed /= 1024
        return f"{speed:.1f} TB/s"
    
    @staticmethod
    def _format_time(seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds//60}m {seconds%60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    @staticmethod
    def _parse_rate(rate: str) -> int:
        rate = rate.upper().strip()
        if rate.endswith('K'):
            return int(float(rate[:-1]) * 1000)
        elif rate.endswith('M'):
            return int(float(rate[:-1]) * 1000000)
        else:
            try:
                return int(rate)
            except:
                return 0