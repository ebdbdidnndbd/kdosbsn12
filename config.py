"""
⚙️ إعدادات الموقع
"""

import os
from datetime import datetime

# ============ إعدادات الموقع ============
class Config:
    # إعدادات الموقع
    SITE_NAME = "🎬 منصة التحميل الذكي"
    SITE_DESCRIPTION = "تحميل وبحث وتشغيل الفيديوهات من جميع المنصات"
    SITE_VERSION = "2.0.0"
    SITE_AUTHOR = "Video Platform Team"
    SITE_URL = "http://localhost:5000"
    
    # إعدادات الخادم
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-2024')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB
    
    # إعدادات قاعدة البيانات
    DATABASE_PATH = 'database.db'
    
    # إعدادات التحميل
    DOWNLOAD_FOLDER = 'downloads'
    MAX_DOWNLOAD_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
    ALLOWED_EXTENSIONS = {'.mp4', '.mp3', '.webm', '.mkv', '.avi', '.mov'}
    
    # إعدادات yt-dlp
    YDL_OPTIONS = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'nooverwrites': True,
        'continuedl': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    # المنصات المدعومة
    SUPPORTED_PLATFORMS = [
        'YouTube',
        'TikTok',
        'Instagram',
        'Twitter',
        'Facebook',
        'Reddit',
        'Vimeo',
        'Dailymotion',
        'SoundCloud',
        'Twitch'
    ]
    
    # إعدادات الواجهة
    THEME_COLORS = {
        'primary': '#2563eb',
        'secondary': '#3b82f6',
        'success': '#10b981',
        'danger': '#ef4444',
        'warning': '#f59e0b',
        'dark': '#0f172a',
        'light': '#f8fafc'
    }
    
    # إعدادات البحث
    SEARCH_LIMIT = 12
    SEARCH_CACHE_TIME = 300  # ثانية
    
    # إعدادات التخزين
    CLEANUP_INTERVAL = 3600  # ثانية (ساعة واحدة)

# ============ متغيرات الموقع ============
config = Config()
