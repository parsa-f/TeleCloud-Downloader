import os
import threading
import telebot
from collections import OrderedDict

# =============================================================
# Paths and constants
# =============================================================
TOKEN           = os.environ.get('DOWNLOADER_BOT_TOKEN')
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID', '')
DOWNLOAD_DIR    = '/root/downloads'
COOKIES_DIR     = '/root/cookies'
COOKIES_STATE   = '/root/cookies_enabled.json'
USER_LANGS_FILE = '/app/user_configs/user_langs.json'
USER_CONFIGS_DIR = '/app/user_configs'

# =============================================================
# PostgreSQL (user storage — replaces local SQLite to save disk)
# =============================================================
DATABASE_URL = os.environ.get('DATABASE_URL')

# =============================================================
# GitHub per-user upload (each user sets their own token)
# =============================================================
GITHUB_DEFAULT_REPO = os.environ.get('GITHUB_DEFAULT_REPO', '')  # owner/repo fallback

# =============================================================
# AWS S3 / Railway Bucket (injected automatically by Railway)
# Railway uses bare names (ACCESS_KEY_ID, BUCKET, ENDPOINT);
# we also accept AWS_-prefixed names for portability.
# =============================================================
AWS_ACCESS_KEY_ID     = os.environ.get('AWS_ACCESS_KEY_ID') or os.environ.get('ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY') or os.environ.get('ACCESS_KEY_SECRET')
AWS_BUCKET_NAME       = (os.environ.get('AWS_BUCKET_NAME')
                         or os.environ.get('BUCKET')
                         or os.environ.get('RAILWAY_BUCKET_NAME'))
AWS_ENDPOINT_URL      = os.environ.get('AWS_ENDPOINT_URL') or os.environ.get('ENDPOINT')
AWS_DEFAULT_REGION    = (os.environ.get('AWS_DEFAULT_REGION')
                         or os.environ.get('REGION', 'auto'))
RAILWAY_PUBLIC_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')

# Local file storage for S3 fallback / Railway Volume
UPLOAD_VOLUME = '/root/storage'
os.makedirs(UPLOAD_VOLUME, exist_ok=True)

# =============================================================
# Multi-tenant admin & registration settings
# =============================================================
# The single Telegram user_id that has full admin privileges.
ADMIN_ID = int(os.environ.get('ADMIN_ID', '0'))

# Default upload destination is Telegram (2GB via Local Bot API).
# Users start in tg_upload_mode; they can switch to Drive from the menu.
gdrive_redirects = {}  # cid -> {fp, folder_name, task_info} when gd chosen w/o Drive
tg_upload_mode = set()
if ADMIN_ID > 0:
    tg_upload_mode.add(ADMIN_ID)

# When True, any user who sends /start can self-register.
# When False, users must request access and wait for admin approval.
REGISTRATION_OPEN = os.environ.get('REGISTRATION_OPEN', 'false').lower() in ('1', 'true', 'yes')

# Global daily quota defaults (overridable per-user in the DB).
MAX_DAILY_FILES = int(os.environ.get('MAX_DAILY_FILES', '20'))
MAX_DAILY_BYTES = int(os.environ.get('MAX_DAILY_BYTES', str(5 * 1024 ** 3)))  # 5 GB

# Global monthly quota defaults (overridable per-user in the DB).
MAX_MONTHLY_FILES = int(os.environ.get('MAX_MONTHLY_FILES', '100'))
MAX_MONTHLY_BYTES = int(os.environ.get('MAX_MONTHLY_BYTES', str(20 * 1024 ** 3)))  # 20 GB

# Google Colab notebook URL shown to users during Drive onboarding.
COLAB_URL = os.environ.get(
    'COLAB_URL',
    'https://colab.research.google.com/drive/1Ltyqs4i0UAuR6FpBrn3ygMuqlnPo_igV?usp=sharing'
)

MAX_RETRIES  = 3
RETRY_DELAY  = 10

# Maximum number of downloads that may run in parallel.
# Raise this only if your server has enough RAM and bandwidth.
MAX_CONCURRENT_DOWNLOADS = int(os.environ.get('MAX_CONCURRENT_DOWNLOADS', '2'))

# =============================================================
# Per-user runtime state
# =============================================================
user_state       = {}
# pending file uploads awaiting destination pick: cid -> {'fp':..., 'status_msg_id':...}
pending_uploads  = {}

# Default quality per user (video only)
# Possible values: 'manual', 'best', '1080', '720', '480'
user_quality = {}

# Media mode: True = music (audio), False = video (default)
user_audio_mode = {}

# Download mode per user
# Possible values: 'auto', 'ytdlp', 'torrent', 'direct'
user_download_mode = {}

# Video container format (when media == video)
# Possible values: 'mp4', 'mkv', 'default'
user_video_format = {}

# Audio codec (when media == audio)
# Possible values: 'mp3', 'm4a', 'flac', 'default'
user_audio_format = {}

# Audio bitrate/quality (when media == audio)
# Possible values: '320', '128', 'default'
user_audio_quality = {}

# Subtitle language preference
# Possible values: 'en', 'fa', 'off'
user_subtitle = {}

# Embed chapter metadata in video files
# Possible values: True / False
user_chapters = {}

# =============================================================
# Link cache
# =============================================================
class BoundedCache(OrderedDict):
    def __init__(self, maxsize=2000):
        super().__init__()
        self.maxsize = maxsize

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            self.popitem(last=False)

url_cache  = BoundedCache(2000)
cache_lock = threading.Lock()

# =============================================================
# Shared objects
# =============================================================
import telebot.apihelper as apihelper
TELEGRAM_LOCAL = os.environ.get('TELEGRAM_LOCAL', '1').strip().lower() in ('1', 'true', 'yes', 'on')
if TELEGRAM_LOCAL:
    apihelper.API_URL = "http://localhost:8081/bot{0}/{1}"
    apihelper.FILE_URL = "http://localhost:8081"
bot = telebot.TeleBot(TOKEN, parse_mode=None)
# Wrap answer_callback_query so an expired/invalid query id (user clicks an
# old button after a restart) never crashes the whole callback handler.
_orig_answer = bot.answer_callback_query
def _safe_answer(call_id, *a, **k):
    try:
        return _orig_answer(call_id, *a, **k)
    except Exception:
        return None
bot.answer_callback_query = _safe_answer
# Set explicit timeouts for all short API calls (edit, send_message, etc.).
# Large-file uploads override this per-call via timeout=upload_timeout in
# uploaders/telegram_upload.py, so these values only affect small payloads.
apihelper.CONNECT_TIMEOUT = 10   # TCP connection phase
apihelper.READ_TIMEOUT    = 60   # max time to wait for Telegram's HTTP response
pending_queue  = []
queue_lock     = threading.Lock()

# current_tasks: maps chat_id → the task dict that worker is executing for that user.
# Protected by current_tasks_lock for thread-safe reads/writes from any thread.
current_tasks      = {}                # type: dict[int, dict]
current_tasks_lock = threading.Lock()

# stop_event: used exclusively for rclone upload cancellation.
# Per-download cancellation is handled via task['_stop'] (a threading.Event
# injected into each task by downloader_queue before dispatch).
stop_event     = threading.Event()
rclone_process = None

# =============================================================
# Create required directories & initialise DB
# =============================================================
os.makedirs(DOWNLOAD_DIR,    exist_ok=True)
os.makedirs(COOKIES_DIR,     exist_ok=True)
os.makedirs(USER_CONFIGS_DIR, exist_ok=True)

from db import init_db
init_db()
