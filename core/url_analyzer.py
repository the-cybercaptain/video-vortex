"""
URL validation, phishing detection, platform identification.
"""

import re
import urllib.parse
from typing import Dict, Tuple

PLATFORM_MAP: Dict[str, str] = {
    # ── Major video ──
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "youtube.com/shorts": "YouTube Shorts",
    "music.youtube.com": "YouTube Music",
    "tiktok.com": "TikTok",
    "vm.tiktok.com": "TikTok",
    "instagram.com": "Instagram",
    "instagr.am": "Instagram",
    "twitter.com": "Twitter/X",
    "x.com": "Twitter/X",
    "facebook.com": "Facebook",
    "fb.watch": "Facebook",
    "fb.com": "Facebook",
    "twitch.tv": "Twitch",
    "clips.twitch.tv": "Twitch Clip",
    "vimeo.com": "Vimeo",
    "player.vimeo.com": "Vimeo",
    "dailymotion.com": "Dailymotion",
    "dai.ly": "Dailymotion",
    "reddit.com": "Reddit",
    "redd.it": "Reddit",
    "rumble.com": "Rumble",
    "rumble.cc": "Rumble",
    "odysee.com": "Odysee",
    "lbry.tv": "LBRY",
    "kick.com": "Kick",
    # ── Audio / Music ──
    "soundcloud.com": "SoundCloud",
    "snd.sc": "SoundCloud",
    "bandcamp.com": "Bandcamp",
    "bcbits.com": "Bandcamp",
    "mixcloud.com": "Mixcloud",
    "open.spotify.com": "Spotify",
    "podcasts.apple.com": "Apple Podcasts",
    "music.apple.com": "Apple Music",
    "deezer.com": "Deezer",
    "tidal.com": "Tidal",
    "napster.com": "Napster",
    "zingmp3.vn": "ZingMP3",
    "nhaccuatui.com": "NhacCuaTui",
    # ── Asian platforms ──
    "bilibili.com": "Bilibili",
    "b23.tv": "Bilibili",
    "nicovideo.jp": "NicoNico",
    "nico.ms": "NicoNico",
    "weibo.com": "Weibo",
    "m.weibo.cn": "Weibo",
    "douyin.com": "Douyin",
    "iesdouyin.com": "Douyin",
    "kuaishou.com": "Kuaishou",
    "gifshow.com": "Kuaishou",
    "ixigua.com": "iXigua",
    "youku.com": "Youku",
    "qq.com": "Tencent Video",
    "v.qq.com": "Tencent Video",
    "mgtv.com": "Mango TV",
    "acfun.cn": "AcFun",
    # ── Indian short-video ──
    "sharechat.com": "ShareChat",
    "moj.app": "Moj",
    "joshapp.com": "Josh",
    "mxplayer.in": "MX Player",
    "taka.live": "Taka",
    "chingari.io": "Chingari",
    # ── Social / Messaging ──
    "pinterest.com": "Pinterest",
    "pin.it": "Pinterest",
    "linkedin.com": "LinkedIn",
    "lnkd.in": "LinkedIn",
    "t.me": "Telegram",
    "telegram.org": "Telegram",
    "discord.com": "Discord",
    "cdn.discordapp.com": "Discord",
    "snapchat.com": "Snapchat",
    "story.snapchat.com": "Snapchat Story",
    "www.snapchat.com": "Snapchat",
    "snapchat.com/add": "Snapchat Profile",
    "snapchat.com/spotlight": "Snapchat Spotlight",
    # ── Image hosts ──
    "imgur.com": "Imgur",
    "i.imgur.com": "Imgur",
    "giphy.com": "GIPHY",
    "media.giphy.com": "GIPHY",
    "9gag.com": "9GAG",
    "imgflip.com": "Imgflip",
    # ── Streaming / Hosting ──
    "streamable.com": "Streamable",
    "streamja.com": "Streamja",
    "streamff.com": "Streamff",
    "sendvid.com": "Sendvid",
    "vidyard.com": "Vidyard",
    "wistia.com": "Wistia",
    "gofile.io": "Gofile",
    "loom.com": "Loom",
    "panopto.com": "Panopto",
    "echo360.org": "Echo360",
    "web.microsoftstream.com": "Microsoft Stream",
    # ── OTT / Premium ──
    "hotstar.com": "Disney+ Hotstar",
    "netflix.com": "Netflix",
    "primevideo.com": "Amazon Prime",
    "disneyplus.com": "Disney+",
    "hbomax.com": "HBO Max",
    "peacocktv.com": "Peacock",
    "paramountplus.com": "Paramount+",
    "crunchyroll.com": "Crunchyroll",
    "funimation.com": "Funimation",
    "vrv.co": "VRV",
    "dplus.com": "Discovery+",
    # ── News / Media ──
    "dailymail.co.uk": "DailyMail",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "nbc.com": "NBC",
    "cbs.com": "CBS",
    "abc.com": "ABC",
    "fox.com": "FOX",
    "cnn.com": "CNN",
    "nytimes.com": "NYTimes",
    "wsj.com": "WSJ",
    "bloomberg.com": "Bloomberg",
    "theguardian.com": "The Guardian",
    "reuters.com": "Reuters",
    "apnews.com": "AP News",
    # ── Education / Talks ──
    "ted.com": "TED",
    "udemy.com": "Udemy",
    "coursera.org": "Coursera",
    "skillshare.com": "Skillshare",
    # ── Tech / Gaming ──
    "vox.com": "Vox",
    "theverge.com": "The Verge",
    "polygon.com": "Polygon",
    "ign.com": "IGN",
    "gamespot.com": "GameSpot",
    "giantbomb.com": "Giant Bomb",
    "kotaku.com": "Kotaku",
    "pcgamer.com": "PC Gamer",
    # ── Entertainment ──
    "screenrant.com": "ScreenRant",
    "collider.com": "Collider",
    "variety.com": "Variety",
    "hollywoodreporter.com": "Hollywood Reporter",
    "deadline.com": "Deadline",
    "tmz.com": "TMZ",
    "people.com": "People",
    # ── Creator platforms ──
    "patreon.com": "Patreon",
    "onlyfans.com": "OnlyFans",
    "fanbox.cc": "Pixiv FANBOX",
    "pixiv.net": "Pixiv",
    "gumroad.com": "Gumroad",
    "substack.com": "Substack",
    # ── Iranian ──
    "aparat.com": "Aparat",
    "telewebion.com": "Telewebion",
    # ── Miscellaneous ──
    "kickstarter.com": "Kickstarter",
    "buzzfeed.com": "BuzzFeed",
    "mashable.com": "Mashable",
    "vice.com": "Vice",
}


PHISHING_PATTERNS = [
    r"paypal.*\.(?!com$)\w+",
    r"google.*\.(?!com$|co\.\w+$)\w+",
    r"facebook.*\.(?!com$|net$)\w+",
    r"apple.*\.(?!com$)\w+",
    r"amazon.*\.(?!com$|co\.\w+$)\w+",
    r"secure.*login",
    r"account.*verify",
    r"\.xyz/.*free",
    r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}",
    
    # ── Naye Advanced Patterns ──
    r"netflix.*\.(?!com$)\w+",          # Fake Netflix scam domains
    r"instagram.*\.(?!com$)\w+",        # Fake Instagram login traps
    r"crypto.*bonus",                   # Crypto scam links
    r"claim.*reward",                   # Scam click-bait words
    r"update.*billing",                 # Phishing traps for bank details
    r"free.*giveaway",                  # Standard spam links
    r"signin.*verification",            # Fake dashboard entries
    r"support-vortex.*",                # Attackers trying to spoof your own site name
]


SUSPICIOUS_TLDS = {
    ".tk", ".ml", ".ga", ".cf", ".gq",
    ".xyz", ".top", ".club", ".online", ".site",
    ".icu", ".buzz",
    
    # ── Naye Dangerous TLDs ──
    ".zip",     # Iska misuse bohot barh gaya hai (files ko hide karne ke liye)
    ".mov",     # Video file extensions ko spoof karne ke liye use hota hai
    ".download",# Direct malware downloading sites ke liye
    ".stream",  # Fake streaming dashboards
    ".cricket", # High spam rate domain suffix
    ".work",    # Sasta aur dangerous TLD
    ".date",    # Scam dating panels
    ".win"      # Betting/Spam rewards
}


def is_valid_url(url: str) -> Tuple[bool, str]:
    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, "URL must start with http:// or https://"
        if not parsed.netloc:
            return False, "URL has no domain"
        return True, "OK"
    except Exception as e:
        return False, str(e)


def check_phishing(url: str) -> Tuple[bool, str]:
    url_lower = url.lower()
    parsed = urllib.parse.urlparse(url_lower)
    hostname = parsed.netloc.lstrip("www.")
    
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname):
        return True, "Raw IP address used as host - suspicious"
    
    for tld in SUSPICIOUS_TLDS:
        if hostname.endswith(tld):
            return True, f"Suspicious TLD detected: {tld}"
    
    for pattern in PHISHING_PATTERNS:
        if re.search(pattern, url_lower):
            if any(good in hostname for good in PLATFORM_MAP):
                continue
            return True, "Suspicious pattern detected in URL"
    
    if hostname.count(".") >= 4:
        return True, "Unusual number of subdomains"
    
    try:
        hostname.encode("ascii")
    except UnicodeEncodeError:
        return True, "Non-ASCII characters in domain"
    
    return False, "URL appears safe"


def detect_platform(url: str) -> str:
    parsed = urllib.parse.urlparse(url.lower())
    host = parsed.netloc.lstrip("www.")
    
    for key, name in PLATFORM_MAP.items():
        if host == key or host.endswith("." + key):
            return name
    
    return "Unknown / Generic"


def is_playlist_url(url: str) -> bool:
    """
    Detect if URL points to a playlist (multiple videos)
    Snapchat URLs are single videos, not playlists
    """
    url_lower = url.lower()
    
    # SNAPCHAT: Stories, Spotlight, Public profiles sab SINGLE VIDEOS hain
    # Agar explicitly "playlist" word nahi hai toh false return karo
    if "snapchat.com" in url_lower:
        # Sirf agar URL mein "playlist" explicitly likha ho tabhi True
        if "playlist" in url_lower:
            return True
        return False  # Snapchat par normal videos playlists nahi hain
    
    # YOUTUBE Playlist detection
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        if re.search(r"[/&]list=", url_lower) or "/playlist" in url_lower:
            return True
    
    # TIKTOK Profile (multiple videos wali page)
    if "tiktok.com" in url_lower:
        if re.search(r"tiktok\.com/@[^/]+$", url_lower):
            return True
    
    # OTHER PLATFORMS Playlist patterns
    patterns = [
        r"/playlist",
        r"/sets/",      # SoundCloud sets
        r"/album/",     # Music albums
        r"/collection/",
        r"/watchlist",
    ]
    
    return any(re.search(p, url_lower) for p in patterns)


def analyze_url(url: str) -> Dict:
    url = url.strip()
    valid, valid_reason = is_valid_url(url)
    if not valid:
        return {
            "valid": False, "valid_reason": valid_reason,
            "phishing": False, "phishing_reason": "",
            "platform": "Unknown", "is_playlist": False,
        }
    phishing, phishing_reason = check_phishing(url)
    platform = detect_platform(url)
    playlist = is_playlist_url(url)
    return {
        "valid": True,
        "valid_reason": "Valid URL",
        "phishing": phishing,
        "phishing_reason": phishing_reason,
        "platform": platform,
        "is_playlist": playlist,
    }