"""
Fetch video metadata via yt-dlp with all bypass flags enabled.
FIXED: Playlist doesn't try to fetch first video's formats.
ADDED: Snapchat support with fallback mechanism
"""

import subprocess
import json
import os
from typing import Optional, List, Dict
import urllib.request


def _run_ytdlp(args: List[str], cookies_browser: str = "", cookies_file: str = "",
               bypass_geo: bool = True, bypass_age: bool = True) -> Dict:
    """Run yt-dlp with JSON output and return parsed dict."""
    base = ["yt-dlp", "--no-warnings", "--quiet"]
    
    if bypass_age:
        base += ["--age-limit", "99"]
    
    if bypass_geo:
        base += ["--geo-bypass", "--geo-bypass-country", "US"]
    
    if cookies_browser and cookies_browser.lower() not in ("", "none"):
        base += ["--cookies-from-browser", cookies_browser]
    elif cookies_file and os.path.exists(cookies_file):
        base += ["--cookies", cookies_file]
    
    cmd = base + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if result.returncode != 0:
            return {"error": result.stderr.strip() or "yt-dlp error"}
        return json.loads(result.stdout)
    except FileNotFoundError:
        return {"error": "yt-dlp not found. Please install: pip install yt-dlp"}
    except subprocess.TimeoutExpired:
        return {"error": "Request timed out (45s)"}
    except json.JSONDecodeError as e:
        return {"error": f"Could not parse yt-dlp output: {e}"}
    except Exception as e:
        return {"error": str(e)}


def fetch_snapchat_info(url: str, cookies_browser: str = "", cookies_file: str = "") -> Dict:
    """Fetch metadata for a Snapchat video with fallback."""
    
    # Pehle try with normal method
    data = _run_ytdlp(
        ["--dump-single-json", "--no-playlist", url],
        cookies_browser=cookies_browser,
        cookies_file=cookies_file,
    )
    
    # Agar error hai toh flat playlist method try karo
    if "error" in data:
        data = _run_ytdlp(
            ["--flat-playlist", url],
            cookies_browser=cookies_browser,
            cookies_file=cookies_file,
        )
    
    if "error" in data:
        # Agar still error hai toh basic info return karo
        return {
            "title": "Snapchat Video",
            "uploader": "Snapchat User",
            "duration": "N/A",
            "thumbnail": "",
            "webpage_url": url,
            "formats": [{
                "format_id": "best",
                "label": "Best Quality",
                "height": 720,
                "ext": "mp4",
                "filesize": None,
                "has_audio": True,
            }],
            "audio_formats": [],
            "platform": "Snapchat",
        }
    
    # Check if it's a playlist/story collection
    if data.get("_type") == "playlist" or data.get("entries"):
        entries_data = []
        for entry in data.get("entries", []):
            entry_url = entry.get("webpage_url") or entry.get("url", "")
            entries_data.append({
                "title": entry.get("title", "Snapchat Story"),
                "url": entry_url if entry_url else url,
                "duration": entry.get("duration", 0),
                "thumbnail": entry.get("thumbnail", ""),
            })
        
        return {
            "title": data.get("title", "Snapchat Stories"),
            "uploader": data.get("uploader", "Snapchat User"),
            "duration": "N/A",
            "thumbnail": data.get("thumbnail", ""),
            "webpage_url": url,
            "entries": entries_data,
            "formats": [],
            "audio_formats": [],
            "platform": "Snapchat",
        }
    
    # Single video processing
    formats_raw = data.get("formats", [])
    
    formats = []
    seen_res = set()
    for f in formats_raw:
        height = f.get("height")
        vcodec = f.get("vcodec", "none")
        if vcodec == "none":
            continue
        
        label = f"{height}p" if height else f.get("format_note", "Unknown")
        if label in seen_res:
            continue
        seen_res.add(label)
        
        formats.append({
            "format_id": f.get("format_id", "best"),
            "label": label,
            "height": height or 0,
            "ext": f.get("ext", "mp4"),
            "filesize": f.get("filesize") or f.get("filesize_approx"),
            "has_audio": f.get("acodec") != "none",
        })
    
    formats.sort(key=lambda x: x["height"], reverse=True)
    
    # Agar koi format nahi mila toh default add karo
    if not formats:
        formats = [{
            "format_id": "best",
            "label": "Best Quality",
            "height": 720,
            "ext": "mp4",
            "filesize": None,
            "has_audio": True,
        }]
    
    duration_sec = data.get("duration", 0)
    duration_str = _fmt_duration(duration_sec) if duration_sec else "N/A"
    
    thumbnail = data.get("thumbnail", "")
    if not thumbnail:
        entries = data.get("entries", [])
        if entries and entries[0].get("thumbnail"):
            thumbnail = entries[0]["thumbnail"]
    
    title = data.get("title", "Snapchat Video")
    if title == "Snapchat Video" or "snapchat" in title.lower():
        video_id = data.get("id", "")
        if video_id:
            title = f"Snapchat_Video_{video_id}"
    
    return {
        "title": title,
        "uploader": data.get("uploader") or data.get("channel", "Snapchat User"),
        "duration": duration_str,
        "duration_sec": duration_sec,
        "thumbnail": thumbnail,
        "webpage_url": data.get("webpage_url", url),
        "view_count": data.get("view_count"),
        "like_count": data.get("like_count"),
        "formats": formats,
        "audio_formats": [],
        "is_live": data.get("is_live", False),
        "platform": "Snapchat",
        "age_limit": data.get("age_limit", 0),
    }


def fetch_video_info(url: str, cookies_browser: str = "", cookies_file: str = "") -> Dict:
    """Fetch metadata for a single video URL."""
    # Check if it's a Snapchat URL
    if "snapchat.com" in url.lower() or "story.snapchat.com" in url.lower():
        return fetch_snapchat_info(url, cookies_browser, cookies_file)
    
    data = _run_ytdlp(
        ["--dump-single-json", "--no-playlist", url],
        cookies_browser=cookies_browser,
        cookies_file=cookies_file,
    )
    
    if "error" in data:
        return data
    
    formats_raw = data.get("formats", [])
    
    formats = []
    seen_res = set()
    for f in reversed(formats_raw):
        height = f.get("height")
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        format_id = f.get("format_id", "")
        filesize = f.get("filesize") or f.get("filesize_approx")
        ext = f.get("ext", "")
        
        if vcodec == "none":
            continue
        
        label = f"{height}p" if height else format_id
        if label in seen_res:
            continue
        seen_res.add(label)
        
        formats.append({
            "format_id": format_id,
            "label": label,
            "height": height or 0,
            "ext": ext,
            "filesize": filesize,
            "has_audio": acodec != "none",
        })
    
    formats.sort(key=lambda x: x["height"], reverse=True)
    
    audio_formats = []
    seen_abr = set()
    for f in formats_raw:
        vcodec = f.get("vcodec", "none")
        abr = f.get("abr")
        if vcodec != "none" or not abr:
            continue
        label = f"{int(abr)}kbps"
        if label in seen_abr:
            continue
        seen_abr.add(label)
        audio_formats.append({
            "format_id": f.get("format_id", ""),
            "label": label,
            "abr": abr,
            "ext": f.get("ext", ""),
            "filesize": f.get("filesize") or f.get("filesize_approx"),
        })
    audio_formats.sort(key=lambda x: x["abr"], reverse=True)
    
    duration_sec = data.get("duration", 0)
    duration_str = _fmt_duration(duration_sec) if duration_sec else "N/A"
    
    thumbnail = data.get("thumbnail", "")
    if not thumbnail:
        video_id = data.get("id", "")
        if video_id:
            thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    
    return {
        "title": data.get("title", "Unknown"),
        "uploader": data.get("uploader") or data.get("channel", "Unknown"),
        "duration": duration_str,
        "duration_sec": duration_sec,
        "thumbnail": thumbnail,
        "webpage_url": data.get("webpage_url", url),
        "view_count": data.get("view_count"),
        "like_count": data.get("like_count"),
        "upload_date": data.get("upload_date", ""),
        "formats": formats,
        "audio_formats": audio_formats,
        "is_live": data.get("is_live", False),
        "platform": data.get("extractor_key", "Unknown"),
        "age_limit": data.get("age_limit", 0),
        "availability": data.get("availability", ""),
    }


def fetch_playlist_info(url: str, cookies_browser: str = "", cookies_file: str = "") -> Dict:
    """Fetch playlist metadata - DOES NOT fetch individual video formats."""
    data = _run_ytdlp(
        ["--dump-single-json", "--flat-playlist", url],
        cookies_browser=cookies_browser,
        cookies_file=cookies_file,
    )
    
    if "error" in data:
        return data
    
    entries = data.get("entries", [])
    entry_list = []
    for entry in entries:
        entry_url = entry.get("webpage_url") or entry.get("url", "")
        if entry_url and not entry_url.startswith("http"):
            entry_url = f"https://www.youtube.com/watch?v={entry_url}"
        
        thumb = entry.get("thumbnail", "")
        if not thumb:
            vid_id = entry.get("id", "")
            if vid_id and not vid_id.startswith("http"):
                thumb = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
        
        entry_list.append({
            "title": entry.get("title", "Unknown"),
            "url": entry_url,
            "duration": _fmt_duration(entry.get("duration", 0)),
            "thumbnail": thumb,
        })
    
    playlist_thumbnail = data.get("thumbnail", "")
    if not playlist_thumbnail and entry_list:
        playlist_thumbnail = entry_list[0].get("thumbnail", "")
    
    return {
        "title": data.get("title", "Playlist"),
        "uploader": data.get("uploader") or data.get("channel", "Unknown"),
        "playlist_count": data.get("playlist_count", len(entries)),
        "thumbnail": playlist_thumbnail,
        "entries": entry_list,
        "formats": [],
        "audio_formats": [],
    }


def download_thumbnail(url: str, dest_path: str) -> bool:
    if not url:
        return False
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            with open(dest_path, "wb") as f:
                f.write(data)
        return True
    except Exception:
        return False


def _fmt_duration(seconds) -> str:
    try:
        s = int(seconds)
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{sec:02d}"
        return f"{m}:{sec:02d}"
    except Exception:
        return "N/A"


def fmt_filesize(size_bytes: Optional[int]) -> str:
    if not size_bytes:
        return "? MB"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes/1024**2:.1f} MB"
    else:
        return f"{size_bytes/1024**3:.2f} GB"