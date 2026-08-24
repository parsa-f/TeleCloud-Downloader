import os
import re
import subprocess
import time
import html
from collections import deque
from pathlib import Path

from config import bot, stop_event, DRIVE_FOLDER_ID, USER_CONFIGS_DIR
from utils import build_rich_progress_card, cleanup_path, fmt_size

# ──────────────────────────────────────────────────────────────
# Per-user rclone config resolution
# ──────────────────────────────────────────────────────────────

def _user_config_path(user_id: int) -> Path:
    """Return the per-user rclone config path (may not exist)."""
    return Path(USER_CONFIGS_DIR) / f"rclone_{user_id}.conf"


def get_rclone_config_args(user_id) -> list[str]:
    """
    Return the rclone --config flag list appropriate for ``user_id``.

    Security rules (evaluated in order):
      1. If ``/app/user_configs/rclone_<user_id>.conf`` exists → use it.
      2. If it does NOT exist AND user_id is the admin → use the system-wide
         default config (``/root/.config/rclone/rclone.conf``).
      3. If it does NOT exist AND user_id is NOT the admin → raise
         RuntimeError with a Persian error message so the upload is blocked
         and the user is instructed to connect their Drive first.

    Both ``user_id`` and ``ADMIN_ID`` are compared as strings to prevent
    silent type-mismatch bugs (e.g. int vs str).
    """
    from config import ADMIN_ID  # late import to avoid circular dependency

    # ── Step 1: personal config ───────────────────────────────────────────
    if user_id is not None:
        user_conf = _user_config_path(user_id)
        if user_conf.exists():
            return ["--config", str(user_conf)]

    # ── Steps 2 & 3: no personal config found ────────────────────────────
    # Admin is now treated exactly like a regular user: they MUST connect
    # their own Drive (rclone_<uid>.conf) before uploading. No system default.
    raise RuntimeError(
        "❌ شما هنوز گوگل درایو خود را متصل نکردهاید. "
        "لطفاً از بخش تنظیمات (☁️ اتصال گوگل درایو) اقدام کنید."
    )


# ──────────────────────────────────────────────────────────────
# Source → Google Drive folder name mapping
# ──────────────────────────────────────────────────────────────
SOURCE_FOLDER_MAP = {
    'youtube':          'YouTube',
    'youtube playlist': 'YouTube',
    'soundcloud':       'SoundCloud',
    'twitter':          'Twitter',
    'x':                'Twitter',
    'instagram':        'Instagram',
    'tiktok':           'TikTok',
    'vimeo':            'Vimeo',
    'twitch':           'Twitch',
    'reddit':           'Reddit',
    'facebook':         'Facebook',
    'torrent':          'Torrent',
    'direct':           'Direct',
    'direct link':      'Direct',
    'telegram':         'Telegram',
    'ناشناس':           'Other',
    'other':            'Other',
}

def _source_to_folder(source: str) -> str:
    key = (source or '').lower().strip()
    return SOURCE_FOLDER_MAP.get(key, 'Other')

def _to_direct_download_link(link: str) -> str:
    if not link:
        return link
    m = re.search(r'/file/d/([a-zA-Z0-9_-]+)', link)
    if m:
        file_id = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    m2 = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', link)
    if m2:
        file_id = m2.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    if 'export=download' in link:
        return link
    return link

def _cancel_markup(cid=None):
    from telebot import types
    from locales import t
    m = types.InlineKeyboardMarkup()
    label = t(cid, 'cancel_btn') if cid else "❌ لغو"
    m.add(types.InlineKeyboardButton(label, callback_data="cancel_task"))
    return m


def _remember_rclone_output(output_tail, line: str):
    """Keep a compact, log-safe tail of rclone output for failures."""
    if not line:
        return
    for part in re.split(r'[\r\n]+', line):
        part = part.strip()
        if part:
            output_tail.append(part[:2000])

def parse_rclone_speed(s):
    if not s: return 0
    s = s.upper()
    mul = 1
    if 'G' in s: mul = 1024**3
    elif 'M' in s: mul = 1024**2
    elif 'K' in s: mul = 1024
    val = re.sub(r'[^\d.]', '', s)
    return float(val) * mul if val else 0

def parse_rclone_eta(s):
    if not s: return 0
    h  = re.search(r'(\d+)h', s)
    m  = re.search(r'(\d+)m', s)
    sc = re.search(r'(\d+)s', s)
    eta = 0
    if h:  eta += int(h.group(1))  * 3600
    if m:  eta += int(m.group(1))  * 60
    if sc: eta += int(sc.group(1))
    return eta

def upload_to_gdrive_cancellable(
    path: str,
    status_msg,
    folder_name=None,
    is_folder=False,
    task_info=None,
    user_id: int | None = None,
):
    from locales import t

    if task_info is None:
        task_info = {}

    chat_id = status_msg.chat.id
    cid     = chat_id
    # Prefer explicit user_id; fall back to chat_id (1:1 chats only)
    uid     = user_id if user_id is not None else chat_id
    source  = task_info.get('source', 'Other')
    quality = task_info.get('quality', '')
    title   = task_info.get('title', os.path.basename(path))

    source_folder = _source_to_folder(source)

    if folder_name:
        drive_dest = f"gdrive:BotDownloader/{source_folder}/{folder_name}"
    else:
        drive_dest = f"gdrive:BotDownloader/{source_folder}"

    if not is_folder:
        total_size = os.path.getsize(path)
    else:
        total_size = sum(
            os.path.getsize(os.path.join(d, f))
            for d, _, fs in os.walk(path) for f in fs
        )

    # ── Resolve rclone config (raises RuntimeError if none found) ──────────
    try:
        config_args = get_rclone_config_args(uid)
    except RuntimeError as cfg_err:
        try:
            bot.edit_message_text(f"❌ {cfg_err}", chat_id, status_msg.message_id)
        except Exception:
            bot.send_message(chat_id, f"❌ {cfg_err}")
        cleanup_path(path)
        return
    # ───────────────────────────────────────────────────────────────────────

    # ── Only pass --drive-root-folder-id for admin when configured ────
    from config import ADMIN_ID
    is_admin = str(uid) == str(ADMIN_ID)
    root_folder_args = ["--drive-root-folder-id", DRIVE_FOLDER_ID] if is_admin and DRIVE_FOLDER_ID else []
    # ───────────────────────────────────────────────────────────────────────

    try:
        card = build_rich_progress_card(
            "☁️", title, 0, 0, total_size, 0, 0, source, quality, cid=cid)
        bot.edit_message_text(
            card, chat_id, status_msg.message_id,
            reply_markup=_cancel_markup(cid))
    except Exception:
        pass

    # ── Validate token isn't empty before spawning rclone ───────────────────
    user_conf = _user_config_path(uid) if uid is not None else None
    if user_conf and user_conf.exists():
        try:
            import configparser
            cp = configparser.ConfigParser()
            cp.read(str(user_conf))
            tok = cp.get('gdrive', 'token', fallback='')
            if not tok or tok.strip() == '{}':
                raise RuntimeError(
                    "❌ توکن گوگل درایو خالی است. لطفاً دوباره مرحله اتصال "
                    "(☁️ اتصال گوگل درایو) را با client_id شخصی انجام دهید."
                )
        except RuntimeError:
            raise
        except Exception:
            pass

    cmd = [
        "rclone", "copy", path, drive_dest,
        "--progress",
        "--disable-http2",
        "--drive-chunk-size", "16M",
        "--retries", "8",
        "--low-level-retries", "30",
        "--retries-sleep", "10s",
        "--contimeout", "1m",
        "--timeout", "10m",
    ] + root_folder_args + config_args
    output_tail = deque(maxlen=80)

    # ── Thread-safe: proc is stack-local; no global state is touched ────────
    # Each concurrent invocation of this function owns its own Popen object.
    # Threads can never alias or overwrite each other's process reference.
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8', errors='replace')

    # Grab the per-task stop event once, outside the loop, for efficiency.
    # task_info['_stop'] is injected by downloader_queue before dispatch.
    task_stop_event = task_info.get('_stop')

    last_update = time.time()

    while True:
        # ── Dual cancellation check ─────────────────────────────────────────
        # Condition 1: global stop_event → bot is shutting down entirely.
        # Condition 2: task_stop_event  → user clicked "Cancel" for THIS task.
        # Both terminate only the LOCAL proc, so sibling uploads are unaffected.
        cancelled = stop_event.is_set() or (
            task_stop_event is not None and task_stop_event.is_set()
        )
        if cancelled:
            try:
                proc.terminate()
            except Exception:
                pass
            cleanup_path(path)
            try:
                bot.edit_message_text(
                    t(cid, 'upload_cancelled'), chat_id, status_msg.message_id)
            except Exception:
                pass
            return
        # ───────────────────────────────────────────────────────────────────

        line = proc.stdout.readline()
        if line:
            _remember_rclone_output(output_tail, line)
        if not line and proc.poll() is not None:
            break

        if time.time() - last_update > 4:
            m_pct = re.search(r'(\d+)%', line)
            m_spd = re.search(r',\s*([\d.]+\s*[a-zA-Z]+/s)', line)
            m_eta = re.search(r'ETA\s+([0-9hms]+)', line)

            if m_pct:
                pct        = float(m_pct.group(1))
                spd_raw    = m_spd.group(1) if m_spd else ""
                eta_raw    = m_eta.group(1) if m_eta else ""
                speed      = parse_rclone_speed(spd_raw)
                eta        = parse_rclone_eta(eta_raw)
                downloaded = (pct / 100.0) * total_size

                card = build_rich_progress_card(
                    "☁️", title, pct, downloaded, total_size,
                    speed, eta, source, quality, cid=cid)
                try:
                    bot.edit_message_text(
                        card, chat_id, status_msg.message_id,
                        reply_markup=_cancel_markup(cid))
                except Exception:
                    pass
                last_update = time.time()

    ret = proc.wait()

    name = os.path.basename(path)

    if ret == 0:
        cleanup_path(path)
        try:
            bot.edit_message_text(
                t(cid, 'getting_gdrive_link'),
                chat_id, status_msg.message_id)
        except Exception:
            pass

        try:
            if is_folder:
                remote_file_path = drive_dest
            else:
                remote_file_path = drive_dest.rstrip('/') + '/' + name

            # Get shareable link directly via rclone link
            direct_link = None
            raw_link    = None
            lr = subprocess.run(
                ["rclone", "link", remote_file_path] + root_folder_args + config_args,
                capture_output=True, text=True, timeout=60)
            raw_link    = lr.stdout.strip() if lr.returncode == 0 else None
            direct_link = _to_direct_download_link(raw_link) if raw_link else None

            safe_title     = html.escape(title)
            folder_display = f"BotDownloader/{source_folder}" + (f"/{folder_name}" if folder_name else "")

            final_txt = t(cid, 'gdrive_upload_done',
                          title=safe_title,
                          size=fmt_size(total_size),
                          source=source,
                          quality=quality,
                          folder=html.escape(folder_display))
            if direct_link:
                final_txt += t(cid, 'gdrive_direct_link', link=direct_link)
            elif raw_link:
                final_txt += t(cid, 'gdrive_view_link', link=raw_link)
            else:
                final_txt += t(cid, 'gdrive_link_error')

            try:
                bot.edit_message_text(
                    final_txt, chat_id, status_msg.message_id,
                    parse_mode='HTML', disable_web_page_preview=True)
            except Exception:
                bot.send_message(
                    chat_id, final_txt,
                    parse_mode='HTML', disable_web_page_preview=True)

        except Exception as e:
            try:
                bot.edit_message_text(
                    t(cid, 'gdrive_upload_fallback', name=name, e=e),
                    chat_id, status_msg.message_id)
            except Exception:
                pass
    else:
        details = "\n".join(list(output_tail)[-12:])
        print(
            f"[gdrive_upload] rclone copy failed ret={ret} "
            f"path={path!r} dest={drive_dest!r}\n{details}",
            flush=True,
        )
        err_text = t(cid, 'gdrive_upload_error')
        if details:
            err_text += "\n\n<code>" + html.escape(details[-3500:]) + "</code>"
        try:
            bot.edit_message_text(
                err_text, chat_id, status_msg.message_id, parse_mode='HTML')
        except Exception:
            try:
                bot.edit_message_text(
                    t(cid, 'gdrive_upload_error'), chat_id, status_msg.message_id)
            except Exception:
                pass

def upload_file_to_gdrive_folder(
    file_path: str,
    status_msg,
    folder_name="Telegram",
    task_info=None,
    user_id: int | None = None,
):
    if task_info is None:
        task_info = {}
    if 'source' not in task_info:
        task_info['source'] = 'Telegram'
    upload_to_gdrive_cancellable(
        file_path, status_msg,
        folder_name=folder_name,
        task_info=task_info,
        user_id=user_id,
    )
