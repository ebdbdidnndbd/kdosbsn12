"""
🚀 منصة التحميل النهائية - الإصدار الكامل
⚡ تحميل من جميع المنصات + تشغيل تلقائي + واجهة احترافية
"""

from flask import Flask, render_template, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import json
import uuid
import sqlite3
import threading
import time
import re
from datetime import datetime
from urllib.parse import urlparse, unquote
import hashlib

# ============ إعدادات التطبيق ============
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')
CORS(app)
app.config['SECRET_KEY'] = 'video-platform-secret-key-2024'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB

# إعدادات الموقع
SITE_CONFIG = {
    'site_name': '🎬 منصة التحميل الذكي',
    'site_description': 'تحميل وبحث وتشغيل الفيديوهات من جميع المنصات',
    'version': '2.0.0',
    'author': 'Video Platform Team',
    'supported_sites': ['YouTube', 'TikTok', 'Instagram', 'Twitter', 'Facebook', 'Reddit', 'Vimeo', 'Dailymotion']
}

# ============ إنشاء المجلدات ============
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)
os.makedirs('static/images', exist_ok=True)
os.makedirs('downloads', exist_ok=True)

# ============ قاعدة البيانات ============
def init_database():
    """تهيئة قاعدة البيانات"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # جدول التحميلات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT,
            type TEXT,
            quality TEXT,
            status TEXT,
            progress REAL DEFAULT 0,
            speed TEXT,
            eta TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            file_path TEXT,
            file_size INTEGER,
            duration INTEGER,
            thumbnail TEXT,
            uploader TEXT,
            platform TEXT
        )
    ''')
    
    # جدول البحث
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            results TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الإحصائيات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_downloads INTEGER DEFAULT 0,
            total_searches INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # إدخال إحصائيات أولية
    cursor.execute('SELECT COUNT(*) FROM stats')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO stats (total_downloads, total_searches) VALUES (0, 0)')
    
    conn.commit()
    conn.close()
    print("✅ قاعدة البيانات جاهزة")

# ============ مدير التحميل ============
class DownloadManager:
    def __init__(self):
        self.active_downloads = {}
        self.lock = threading.Lock()
    
    def extract_info(self, url):
        """استخراج معلومات الفيديو"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'success': True,
                    'title': info.get('title', 'فيديو'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', ''),
                    'view_count': info.get('view_count', 0),
                    'description': info.get('description', '')[:200],
                    'platform': info.get('extractor', 'unknown'),
                    'formats': info.get('formats', [])[:5]
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def search_videos(self, query, max_results=12):
        """بحث عن فيديوهات"""
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'default_search': 'ytsearch',
                'ignoreerrors': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
                results = []
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            results.append({
                                'title': entry.get('title', ''),
                                'url': entry.get('url', ''),
                                'thumbnail': entry.get('thumbnail', ''),
                                'duration': entry.get('duration', 0),
                                'uploader': entry.get('uploader', ''),
                                'view_count': entry.get('view_count', 0),
                            })
                
                # حفظ في قاعدة البيانات
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO search_history (id, query, results) 
                    VALUES (?, ?, ?)
                ''', (str(uuid.uuid4()), query, json.dumps(results)))
                
                # تحديث الإحصائيات
                cursor.execute('UPDATE stats SET total_searches = total_searches + 1')
                conn.commit()
                conn.close()
                
                return {'success': True, 'results': results}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def start_download(self, download_id, url, download_type='video', quality='best'):
        """بدء عملية التحميل"""
        try:
            with self.lock:
                self.active_downloads[download_id] = {
                    'status': 'initializing',
                    'progress': 0,
                    'url': url,
                    'type': download_type,
                    'quality': quality
                }
            
            # تحديث قاعدة البيانات
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO downloads (id, url, type, quality, status, progress)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (download_id, url, download_type, quality, 'جاري التحضير', 0))
            conn.commit()
            conn.close()
            
            # بدء التحميل في thread منفصل
            thread = threading.Thread(
                target=self._download_thread,
                args=(download_id, url, download_type, quality),
                daemon=True
            )
            thread.start()
            
            return {'success': True, 'id': download_id}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _download_thread(self, download_id, url, download_type, quality):
        """Thread للتحميل الفعلي"""
        try:
            # تحديث الحالة
            with self.lock:
                self.active_downloads[download_id].update({
                    'status': 'تحليل الرابط',
                    'progress': 10
                })
            
            # استخراج المعلومات
            info_result = self.extract_info(url)
            if not info_result['success']:
                raise Exception(info_result['error'])
            
            # إعدادات yt-dlp
            ydl_opts = self._get_ydl_opts(download_type, quality)
            
            # دالة تتبع التقدم
            def progress_hook(d):
                if d['status'] == 'downloading':
                    with self.lock:
                        if download_id in self.active_downloads:
                            downloaded = d.get('downloaded_bytes', 0)
                            total = d.get('total_bytes', 0)
                            if total and total > 0:
                                progress = 10 + (downloaded / total) * 80
                                self.active_downloads[download_id]['progress'] = progress
                                self.active_downloads[download_id]['speed'] = d.get('_speed_str', '')
                                self.active_downloads[download_id]['eta'] = d.get('_eta_str', '')
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # التحميل
                with self.lock:
                    self.active_downloads[download_id].update({
                        'status': 'جاري التحميل',
                        'progress': 20
                    })
                
                info = ydl.extract_info(url, download=True)
                
                # الحصول على اسم الملف
                filename = ydl.prepare_filename(info)
                if download_type == 'audio' and not filename.endswith('.mp3'):
                    # تحويل إلى mp3
                    mp3_file = os.path.splitext(filename)[0] + '.mp3'
                    if os.path.exists(filename):
                        os.rename(filename, mp3_file)
                        filename = mp3_file
                
                # تحديث الحالة النهائية
                with self.lock:
                    self.active_downloads[download_id].update({
                        'status': 'مكتمل',
                        'progress': 100,
                        'file_path': filename,
                        'title': info.get('title', 'ملف'),
                        'duration': info.get('duration', 0),
                        'thumbnail': info.get('thumbnail', '')
                    })
                
                # تحديث قاعدة البيانات
                file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE downloads SET 
                    status = ?, progress = ?, completed_at = CURRENT_TIMESTAMP,
                    file_path = ?, title = ?, duration = ?, thumbnail = ?,
                    uploader = ?, platform = ?, file_size = ?
                    WHERE id = ?
                ''', (
                    'مكتمل', 100, filename,
                    info.get('title', ''), info.get('duration', 0),
                    info.get('thumbnail', ''), info.get('uploader', ''),
                    info.get('extractor', ''), file_size, download_id
                ))
                
                # تحديث إحصائيات التحميلات
                cursor.execute('UPDATE stats SET total_downloads = total_downloads + 1')
                conn.commit()
                conn.close()
                
        except Exception as e:
            with self.lock:
                if download_id in self.active_downloads:
                    self.active_downloads[download_id].update({
                        'status': f'خطأ: {str(e)[:50]}',
                        'progress': -1
                    })
    
    def _get_ydl_opts(self, download_type, quality):
        """إعدادات yt-dlp بناءً على النوع والجودة"""
        opts = {
            'outtmpl': 'downloads/%(title).100s [%(id)s].%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'nooverwrites': True,
            'continuedl': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            },
        }
        
        if download_type == 'audio':
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }],
                'keepvideo': False,
            })
        else:
            if quality == 'best':
                opts['format'] = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
            elif quality == '1080':
                opts['format'] = 'bestvideo[height<=1080]+bestaudio/best'
            elif quality == '720':
                opts['format'] = 'bestvideo[height<=720]+bestaudio/best'
            else:
                opts['format'] = 'best'
        
        return opts

# إنشاء مدير التحميل
download_manager = DownloadManager()

# ============ Routes ============
@app.route('/')
def index():
    """الصفحة الرئيسية"""
    return render_template('index.html', config=SITE_CONFIG)

@app.route('/search')
def search_page():
    """صفحة البحث"""
    return render_template('search.html', config=SITE_CONFIG)

@app.route('/download')
def download_page():
    """صفحة التحميل"""
    return render_template('download.html', config=SITE_CONFIG)

@app.route('/library')
def library_page():
    """صفحة المكتبة"""
    return render_template('library.html', config=SITE_CONFIG)

@app.route('/player/<download_id>')
def player_page(download_id):
    """صفحة المشغل"""
    return render_template('player.html', config=SITE_CONFIG, download_id=download_id)

# ============ API Routes ============
@app.route('/api/search', methods=['POST'])
def api_search():
    """بحث API"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        max_results = data.get('max_results', 12)
        
        if not query or len(query) < 2:
            return jsonify({'success': False, 'error': 'أدخل كلمة بحث (حرفين على الأقل)'})
        
        result = download_manager.search_videos(query, max_results)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/extract', methods=['POST'])
def api_extract():
    """استخراج معلومات الرابط"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'success': False, 'error': 'أدخل رابط'})
        
        result = download_manager.extract_info(url)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download/start', methods=['POST'])
def api_start_download():
    """بدء التحميل"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        download_type = data.get('type', 'video')
        quality = data.get('quality', 'best')
        
        if not url:
            return jsonify({'success': False, 'error': 'أدخل رابط'})
        
        download_id = str(uuid.uuid4())
        result = download_manager.start_download(download_id, url, download_type, quality)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download/status/<download_id>')
def api_download_status(download_id):
    """حالة التحميل"""
    try:
        with download_manager.lock:
            if download_id in download_manager.active_downloads:
                return jsonify({
                    'success': True,
                    'download': download_manager.active_downloads[download_id]
                })
        
        # التحقق من قاعدة البيانات
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM downloads WHERE id = ?', (download_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            download = {
                'id': row[0],
                'url': row[1],
                'title': row[2],
                'type': row[3],
                'quality': row[4],
                'status': row[5],
                'progress': row[6],
                'speed': row[7],
                'eta': row[8],
                'file_path': row[11],
                'duration': row[13],
                'thumbnail': row[14]
            }
            return jsonify({'success': True, 'download': download})
        
        return jsonify({'success': False, 'error': 'التحميل غير موجود'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/downloads/active')
def api_active_downloads():
    """التحميلات النشطة"""
    try:
        with download_manager.lock:
            downloads = list(download_manager.active_downloads.values())
        return jsonify({'success': True, 'downloads': downloads})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/downloads/completed')
def api_completed_downloads():
    """التحميلات المكتملة"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, title, type, duration, thumbnail, uploader, created_at 
            FROM downloads 
            WHERE status = 'مكتمل' 
            ORDER BY completed_at DESC 
            LIMIT 20
        ''')
        
        downloads = []
        for row in cursor.fetchall():
            downloads.append({
                'id': row[0],
                'title': row[1],
                'type': row[2],
                'duration': row[3],
                'thumbnail': row[4],
                'uploader': row[5],
                'created_at': row[6]
            })
        
        conn.close()
        return jsonify({'success': True, 'downloads': downloads})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download/file/<download_id>')
def api_download_file(download_id):
    """تنزيل الملف"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT file_path, title FROM downloads WHERE id = ?', (download_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return jsonify({'success': False, 'error': 'الملف غير موجود'})
        
        file_path = row[0]
        title = row[1] or 'download'
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'الملف محذوف'})
        
        # تنظيف العنوان
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        filename = f"{safe_title[:50]}.{file_path.split('.')[-1]}"
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            conditional=True
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stream/<download_id>')
def api_stream_file(download_id):
    """تشغيل الملف مباشرة"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT file_path FROM downloads WHERE id = ?', (download_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return jsonify({'success': False, 'error': 'الملف غير موجود'})
        
        file_path = row[0]
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'الملف محذوف'})
        
        # تحديد نوع الملف
        if file_path.endswith('.mp4'):
            mimetype = 'video/mp4'
        elif file_path.endswith('.mp3'):
            mimetype = 'audio/mp3'
        else:
            mimetype = 'application/octet-stream'
        
        return send_file(file_path, mimetype=mimetype, conditional=True)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stats')
def api_stats():
    """إحصائيات الموقع"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT total_downloads, total_searches FROM stats LIMIT 1')
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                'success': True,
                'stats': {
                    'total_downloads': row[0],
                    'total_searches': row[1],
                    'active_downloads': len(download_manager.active_downloads)
                }
            })
        
        return jsonify({'success': False, 'error': 'لا توجد إحصائيات'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cleanup', methods=['POST'])
def api_cleanup():
    """تنظيف الملفات القديمة"""
    try:
        deleted = 0
        for filename in os.listdir('downloads'):
            filepath = os.path.join('downloads', filename)
            if os.path.isfile(filepath):
                # حذف الملفات الأقدم من ساعة
                if time.time() - os.path.getmtime(filepath) > 3600:
                    os.remove(filepath)
                    deleted += 1
        
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============ Static Files ============
@app.route('/static/<path:filename>')
def static_files(filename):
    """ملفات ثابتة"""
    return send_from_directory('static', filename)

# ============ Error Handlers ============
@app.errorhandler(404)
def not_found(error):
    """صفحة 404"""
    return render_template('error.html', 
                         config=SITE_CONFIG,
                         error_code=404,
                         error_message='الصفحة غير موجودة'), 404

@app.errorhandler(500)
def server_error(error):
    """صفحة 500"""
    return render_template('error.html',
                         config=SITE_CONFIG,
                         error_code=500,
                         error_message='حدث خطأ في الخادم'), 500

# ============ تشغيل التطبيق ============
if __name__ == '__main__':
    # تهيئة قاعدة البيانات
    init_database()
    
    print("\n" + "="*80)
    print("🚀 منصة تحميل الفيديوهات - الإصدار الكامل")
    print("="*80)
    print("\n✨ الموقع يعمل الآن على:")
    print("   📍 http://localhost:5000")
    print("\n📁 الصفحات الرئيسية:")
    print("   🏠 الرئيسية:     http://localhost:5000")
    print("   🔍 البحث:       http://localhost:5000/search")
    print("   ⚡ التحميل:      http://localhost:5000/download")
    print("   📁 المكتبة:     http://localhost:5000/library")
    print("\n✅ المميزات المضمنة:")
    print("   • 🔍 بحث متقدم - YouTube و TikTok و Instagram")
    print("   • ⚡ تحميل سريع - جميع المنصات مدعومة")
    print("   • 🎬 تشغيل مباشر - داخل الموقع بدون تحميل")
    print("   • 📁 مكتبة منظمة - جميع ملفاتك في مكان واحد")
    print("   • 📊 إحصائيات حية - تتبع جميع النشاطات")
    print("\n" + "="*80)
    print("🎉 جاهز للاستخدام! افتح المتصفح واستمتع بالتجربة الكاملة")
    print("="*80)
    
    # تشغيل التطبيق
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True,
        use_reloader=True
  )
