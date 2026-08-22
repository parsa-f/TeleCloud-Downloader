import os
import re
import time
import glob
import shutil
import logging
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

_tg_call_log = logging.getLogger(__name__)

from config import DOWNLOAD_DIR

# =============================================================
# Clean URL of tracking parameters
# =============================================================
TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'si', 'feature', 'app', 'fbclid', 'gclid', 'ref', 'igshid',
    'mc_eid', 's', '_hsenc', '_hsmi', 'oly_enc_id', 'oly_anon_id',
}

def clean_url(url: str) -> str:
    try:
        parsed  = urlparse(url)
        params  = parse_qs(parsed.query, keep_blank_values=True)
        cleaned = {k: v for k, v in params.items() if k not in TRACKING_PARAMS}
        new_q   = urlencode(cleaned, doseq=True)
        return urlunparse(parsed._replace(query=new_q))
    except Exception:
        return url

# =============================================================
# Disk / size helpers
# =============================================================
def check_disk_space(min_gb: float = 2.0) -> bool:
    st = os.statvfs(DOWNLOAD_DIR)
    return (st.f_bavail * st.f_frsize) / (1024 ** 3) >= min_gb

def get_free_space() -> str:
    st = os.statvfs(DOWNLOAD_DIR)
    return f"{(st.f_bavail * st.f_frsize) / (1024 ** 3):.1f}GB"

def cleanup_path(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
    except Exception:
        pass

def get_file_size(path) -> int:
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for f in glob.glob(os.path.join(path, '**'), recursive=True):
        if os.path.isfile(f):
            total += os.path.getsize(f)
    return total

# =============================================================
# Number formatting
# =============================================================
def fmt_size(b) -> str:
    if b is None:
        return "?"
    b = int(b or 0)
    if b <= 0:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f}{unit}"
        b /= 1024
    return f"{b:.1f}TB"

def fmt_speed(bps) -> str:
    if not bps or float(bps) <= 0:
        return "?/s"
    return fmt_size(bps) + "/s"

# =============================================================
# Progress bar (Rich Progress Card)
# =============================================================
def make_progress_bar(percent: float, width: int = 20) -> str:
    percent = max(0.0, min(100.0, float(percent)))
    filled = int(percent / 100 * width)
    return "▓" * filled + "░" * (width - filled)

def build_rich_progress_card(status_icon: str, title: str, percent: float,
                             downloaded, total, speed, eta, source: str,
                             quality: str, cid=None) -> str:
    """Build a professional progress card."""
    from locales import t as _t
    # Truncate title to 35 characters
    safe_title = title if title else _t(cid, 'progress_title_unknown') if cid else "Unknown"
    tl = safe_title[:32] + "..." if len(safe_title) > 35 else safe_title

    bar = make_progress_bar(percent, width=20)

    dl_str  = fmt_size(downloaded)
    tot_str = fmt_size(total)
    spd_str = fmt_speed(speed)

    # ETA formatting
    if isinstance(eta, (int, float)) and eta > 0:
        eta_str = _t(cid, 'eta_seconds', eta=int(eta)) if cid else f"~{int(eta)}s"
    else:
        eta_str = _t(cid, 'eta_unknown') if cid else "Unknown"

    quality_label = f" {quality}" if quality else ""

    return (
        f"{status_icon} {tl}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{bar} {percent:.0f}%\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 {dl_str} / {tot_str} • ⚡ {spd_str}\n"
        f"⏱ {eta_str} • 🌐 {source}{quality_label}"
    )

# =============================================================
# User-friendly error messages
# =============================================================
def friendly_error(err: str, get_free_space_fn=None, cid=None) -> str:
    from locales import t as _t
    e = str(err).lower()
    # Only claim "login required" when the error actually points to auth,
    # not for any 403/private mention (YouTube uses those for rate-limits
    # and unavailable videos even with valid cookies).
    if ('sign in' in e or 'log in to view' in e or 'login required' in e
            or 'cookies' in e.replace('cookiefile', '')
            or 'confirm you' in e or ('age' in e and 'restricted' in e)):
        return _t(cid, 'err_login') if cid else (
            "🔒 محتوا نیاز به لاگین دارد.\n"
            "➡️ از منوی 🍪 مدیریت کوکی، کوکی سایت را اضافه کنید.")
    if '404' in e or 'not found' in e:
        return _t(cid, 'err_404') if cid else (
            "🔗 لینک پیدا نشد (404).\n"
            "➡️ لینک را بررسی کنید — ممکن است حذف شده یا private باشد.\n"
            "💡 اگه لینک share از اپ بود، لینک مستقیم مرورگر را امتحان کنید.")
    if 'no video' in e or 'no media' in e:
        return _t(cid, 'err_no_video') if cid else (
            "🎬 ویدیویی در این لینک پیدا نشد.\n"
            "➡️ مطمئن شوید لینک مستقیم ویدیو است.")
    if 'network' in e or 'connection' in e or 'timeout' in e or 'resolve' in e:
        return _t(cid, 'err_network') if cid else (
            "🌐 خطای شبکه — اتصال برقرار نشد.\n"
            "➡️ چند ثانیه دیگر دوباره امتحان میکنم.")
    if 'disk' in e or 'no space' in e:
        free = get_free_space_fn() if get_free_space_fn else get_free_space()
        return (_t(cid, 'err_disk', free=free) if cid else
                f"💾 فضای دیسک کافی نیست! آزاد: {free}\n➡️ لطفاً با ادمین تماس بگیرید.")
    if 'unsupported' in e or 'no extractor' in e:
        return _t(cid, 'err_unsupported') if cid else (
            "🚫 این سایت پشتیبانی نمیشود.\n"
            "➡️ از گزینه 🌐 لینک مستقیم استفاده کنید.")
    if 'copyright' in e or 'blocked' in e:
        return _t(cid, 'err_copyright') if cid else "⛔ این محتوا به دلیل کپی‌رایت قابل دانلود نیست."
    if 'format' in e or 'requested format' in e:
        return _t(cid, 'err_format') if cid else (
            "📹 کیفیت انتخابی موجود نیست.\n"
            "➡️ کیفیت پایین‌تری انتخاب کنید.")
    if 'aria2c' in e or 'torrent' in e:
        return _t(cid, 'err_torrent') if cid else (
            "🧲 خطا در دانلود تورنت.\n"
            "➡️ لینک مگنت را بررسی کنید یا تورنت دیگری امتحان کنید.")
    if 'rclone' in e or 'drive' in e:
        return _t(cid, 'err_rclone') if cid else (
            "☁️ خطا در آپلود به گوگل درایو.\n"
            "➡️ تنظیمات rclone را بررسی کنید.")
    short = str(err)[:200] if len(str(err)) > 200 else str(err)
    return (_t(cid, 'err_technical', err=short) if cid else
            f"⚙️ خطای فنی:\n{short}")


# =============================================================
# Telegram API safe-call wrapper — handles FloodWait (429)
# =============================================================
def safe_tg_call(fn, *args, retries: int = 5, **kwargs):
    """
    Call any pyTelegramBotAPI function safely.

    On a 429 FloodWait response Telegram tells us exactly how long to wait
    in the error message ("Retry After X").  We honour that, sleep, and retry
    up to `retries` times before giving up silently.

    All other ApiTelegramException errors (e.g. message not modified, chat not
    found) are re-raised immediately so the caller's own except-blocks can
    react (or suppress) them as before.

    Non-API exceptions (network, disk, etc.) are also re-raised unchanged.

    Usage — replace:
        bot.edit_message_text(text, chat_id, mid)
    with:
        safe_tg_call(bot.edit_message_text, text, chat_id, mid)
    """
    from telebot.apihelper import ApiTelegramException

    for attempt in range(retries + 1):
        try:
            return fn(*args, **kwargs)

        except ApiTelegramException as exc:
            # 429 Too Many Requests — honour the Retry-After header
            if exc.error_code == 429 or "retry after" in str(exc).lower():
                m = re.search(r'retry after (\d+)', str(exc), re.IGNORECASE)
                wait = int(m.group(1)) if m else 30
                wait += 1   # add 1-second buffer
                _tg_call_log.warning(
                    "FloodWait: sleeping %ds before retry %d/%d for %s",
                    wait, attempt + 1, retries, fn.__name__,
                )
                time.sleep(wait)
                continue   # retry

            # Any other Telegram API error (message not modified, etc.)
            # → re-raise so the caller decides what to do
            raise

    # All retries exhausted — log and return None instead of crashing
    _tg_call_log.error(
        "safe_tg_call: gave up after %d FloodWait retries for %s",
        retries, fn.__name__,
    )
    return None