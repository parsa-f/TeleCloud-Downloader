import os
import html
from pathlib import Path
from downloader_queue import enqueue as _raw_enqueue
import re
import threading
import yt_dlp
from telebot import types
from urllib.parse import urlparse

import config
from config import (bot, cache_lock, url_cache,
                    user_state, ADMIN_ID, REGISTRATION_OPEN,
                    USER_CONFIGS_DIR)

import db
from cookies import (active_cookies_file, save_cookie_data,
                     cookie_exists, is_cookie_enabled, get_cookie_path)
from utils import clean_url, get_free_space, fmt_size, friendly_error
from menu import main_menu_markup, cookie_list_markup, cancel_markup
from dest_helpers import (get_dest, should_ask_dest, get_quality,
                          get_quality_label, is_audio_mode, get_audio_mode_label,
                          get_audio_format, get_audio_quality, get_video_format,
                          get_subtitle, get_chapters)
from downloaders.youtube import get_format_sizes
from uploaders.gdrive_upload import upload_file_to_gdrive_folder
from downloaders.social import _is_ytdlp_url
from locales import t
from user_langs import get_lang, has_lang, set_lang

_LOCAL_API_ROOT = "/var/lib/telegram-bot-api"


def _resolve_local_bot_api_path(file_path: str) -> str:
    """
    Rebuild an absolute local Bot API path when get_file() returns relative
    paths. If local storage is unavailable, keep original path for cloud
    download fallback.
    """
    if file_path.startswith('/'):
        return file_path
    try:
        from glob import glob as _glob
        token_dirs = _glob(os.path.join(_LOCAL_API_ROOT, "*:*"))
        if not token_dirs and os.path.isdir(_LOCAL_API_ROOT):
            token_dirs = [
                os.path.join(_LOCAL_API_ROOT, d)
                for d in os.listdir(_LOCAL_API_ROOT)
                if os.path.isdir(os.path.join(_LOCAL_API_ROOT, d))
                and not d.endswith('.binlog')
            ]
        if token_dirs:
            return os.path.join(token_dirs[0], file_path)
    except Exception:
        return file_path
    return file_path


# =============================================================
# Quota-aware enqueue wrapper
# =============================================================
def enqueue(task: dict):
    """
    Wrap _raw_enqueue with a quota check.
    - Admin always bypasses.
    - For regular users: call db.check_and_update_quota.
      If denied, send an error to the chat and do NOT enqueue.
    The file_size_bytes estimate is 0 at enqueue time; the real
    size accounting happens inside the downloader after download.
    """
    cid = task.get('chat_id')
    if cid == ADMIN_ID:
        return _raw_enqueue(task)

    allowed, reason = db.check_and_update_quota(cid, file_size_bytes=0)
    if not allowed:
        try:
            bot.send_message(cid, reason)
        except Exception:
            pass
        return None
    return _raw_enqueue(task)


YT_FMT_MAP = {
    '1080': ('bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best', False),
    '720':  ('bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best',  False),
    '480':  ('bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best',  False),
    'best': ('bestvideo+bestaudio/best', False),
}

YT_LABELS = {
    '1080': '1080p', '720': '720p', '480': '480p',
    'best': '⭐ بهترین',
}

# Tracks pending join requests to avoid duplicate admin notifications
_pending_join_requests: set = set()


def _display_name_from_user(user) -> str:
    return ((user.first_name or '') + ' ' + (user.last_name or '')).strip() or ''


def _pretend_unknown_command(cid: int, message) -> None:
    """
    Security hardening: for non-admin users probing admin commands,
    respond like a normal unknown input instead of revealing admin-only behavior.
    """
    bot.reply_to(message, t(cid, 'unknown_link'), reply_markup=main_menu_markup(cid))


def _iter_task_paths(task: dict) -> list[str]:
    paths = []
    main_path = task.get('_active_path')
    if isinstance(main_path, str) and main_path:
        paths.append(main_path)
    extra = task.get('_active_paths') or []
    if isinstance(extra, list):
        for item in extra:
            if isinstance(item, str) and item:
                paths.append(item)
    deduped = []
    seen = set()
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        deduped.append(p)
    return deduped


def disable_user_and_stop_tasks(user_id: int) -> int:
    """
    Soft-disable user access and stop active tasks.
    Returns number of active tasks signaled.
    """
    from utils import cleanup_path

    db.reject_user(user_id)
    with config.queue_lock:
        config.pending_queue[:] = [
            task for task in config.pending_queue
            if task.get('chat_id') != user_id
        ]
    stopped = 0
    with config.current_tasks_lock:
        user_tasks = [
            task for task in config.current_tasks.values()
            if task.get('chat_id') == user_id
        ]
    for task in user_tasks:
        stop_event = task.get('_stop')
        if stop_event is not None:
            try:
                stop_event.set()
                stopped += 1
            except Exception:
                pass
        for path in _iter_task_paths(task):
            cleanup_path(path)
    return stopped


# =============================================================
# /start
# =============================================================
@bot.message_handler(commands=['start'])
def start(message):
    import db
    cid = message.chat.id
    db.touch_user_identity(
        cid,
        message.from_user.username,
        _display_name_from_user(message.from_user),
    )

    # Auto-promote first user as admin if ADMIN_ID was never configured
    if config.ADMIN_ID == 0:
        try:
            db.approve_user(cid)
            config.ADMIN_ID = cid
        except Exception:
            pass

    # Language picker first
    if not has_lang(cid):
        mk = types.InlineKeyboardMarkup()
        mk.row(
            types.InlineKeyboardButton("English", callback_data="lang|en"),
            types.InlineKeyboardButton("فارسی",   callback_data="lang|fa"),
        )
        bot.send_message(cid, t(cid, 'lang_select'), reply_markup=mk)
        return

    # Admin always has full access
    if cid == ADMIN_ID:
        db.approve_user(cid)
        user_state[cid] = None
        bot.send_message(cid, t(cid, 'bot_ready'), reply_markup=main_menu_markup(cid))
        return

    # Ensure user row exists
    db.add_user(cid, approved=REGISTRATION_OPEN)

    if db.is_approved(cid):
        user_state[cid] = None
        bot.send_message(cid, t(cid, 'bot_ready'), reply_markup=main_menu_markup(cid))
        return

    # Registration closed — show join-request button
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton(
        t(cid, 'btn_request_access'),
        callback_data="joinreq|request",
    ))
    bot.send_message(cid, t(cid, 'registration_closed'), reply_markup=mk)


# =============================================================
# Admin command: /adduser <id>
# =============================================================
@bot.message_handler(commands=['adduser'])
def cmd_adduser(message):
    cid = message.chat.id
    if cid != ADMIN_ID:
        _pretend_unknown_command(cid, message)
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, t(cid, 'admin_adduser_usage'))
        return
    try:
        uid = int(parts[1])
    except ValueError:
        bot.reply_to(message, t(cid, 'admin_adduser_usage'))
        return
    db.approve_user(uid)
    bot.reply_to(message, t(cid, 'admin_adduser_done', user_id=uid))
    # Notify the newly approved user
    try:
        bot.send_message(uid, t(uid, 'join_approved_user_notify'),
                         reply_markup=main_menu_markup(uid))
    except Exception:
        pass


# =============================================================
# Admin command: /deluser <id>
# =============================================================
@bot.message_handler(commands=['deluser'])
def cmd_deluser(message):
    cid = message.chat.id
    if cid != ADMIN_ID:
        _pretend_unknown_command(cid, message)
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, t(cid, 'admin_deluser_usage'))
        return
    try:
        uid = int(parts[1])
    except ValueError:
        bot.reply_to(message, t(cid, 'admin_deluser_usage'))
        return
    if uid == ADMIN_ID:
        bot.reply_to(message, t(cid, 'admin_user_self_blocked'))
        return
    disable_user_and_stop_tasks(uid)
    bot.reply_to(message, t(cid, 'admin_deluser_done', user_id=uid))


# =============================================================
# Admin command: /users
# =============================================================
@bot.message_handler(commands=['users'])
def cmd_users(message):
    cid = message.chat.id
    if cid != ADMIN_ID:
        _pretend_unknown_command(cid, message)
        return
    from callbacks import render_admin_users_list
    render_admin_users_list(chat_id=cid, page=1, query=None, message_id=None)


# =============================================================
# Admin command: /setquota <id> <files> <GB>
# =============================================================
@bot.message_handler(commands=['setquota'])
def cmd_setquota(message):
    cid = message.chat.id
    if cid != ADMIN_ID:
        _pretend_unknown_command(cid, message)
        return
    parts = message.text.split()
    if len(parts) < 4:
        bot.reply_to(message, t(cid, 'admin_setquota_usage'))
        return
    try:
        uid   = int(parts[1])
        files = int(parts[2])
        gb    = float(parts[3])
    except ValueError:
        bot.reply_to(message, t(cid, 'admin_setquota_usage'))
        return
    bytes_ = int(gb * 1024 ** 3)
    db.set_custom_quota(uid, files, bytes_)
    # 5-arg form: /setquota <id> <daily_files> <daily_GB> <monthly_files> <monthly_GB>
    if len(parts) >= 6:
        try:
            m_files = int(parts[4])
            m_gb    = float(parts[5])
        except ValueError:
            bot.reply_to(message, t(cid, 'admin_setquota_usage'))
            return
        m_bytes = int(m_gb * 1024 ** 3)
        db.set_custom_quota_monthly(uid, m_files, m_bytes)
        bot.reply_to(message, t(cid, 'admin_setquota_done_full',
                                 user_id=uid, files=files, gb=gb,
                                 m_files=m_files, m_gb=m_gb))
    else:
        bot.reply_to(message, t(cid, 'admin_setquota_done',
                                 user_id=uid, files=files, gb=gb))


# =============================================================
# Admin command: /togglereg
# =============================================================
@bot.message_handler(commands=['togglereg'])
def cmd_togglereg(message):
    cid = message.chat.id
    if cid != ADMIN_ID:
        _pretend_unknown_command(cid, message)
        return
    config.REGISTRATION_OPEN = not config.REGISTRATION_OPEN
    status_key = 'admin_togglereg_open' if config.REGISTRATION_OPEN else 'admin_togglereg_closed'
    bot.reply_to(message,
                 t(cid, 'admin_togglereg_done', status=t(cid, status_key)))


# =============================================================
# Per-user GitHub upload config: /setgithub <TOKEN> <owner/repo>
# =============================================================
@bot.message_handler(commands=['setgithub'])
def cmd_setgithub(message):
    cid = message.chat.id
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message,
                     "استفاده:\n/setgithub <TOKEN> <owner/repo>\nمثال:\n/setgithub ghp_xxx amirh00sain/myuploads")
        return
    token = parts[1].strip()
    repo = parts[2].strip()
    if '/' not in repo:
        bot.reply_to(message, "ریپو باید به فرم owner/repo باشه")
        return
    db.set_github_token(cid, token)
    db.set_github_repo(cid, repo)
    bot.reply_to(message, f"توکن GitHub و ریپو ست شد:\n repo: {repo}\nحالا مقصد رو روی GitHub بذار (تنظیمات → Upload)")


# =============================================================
# Admin command: /broadcast <message>
# =============================================================
@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    cid  = message.chat.id
    if cid != ADMIN_ID:
        _pretend_unknown_command(cid, message)
        return
    text = message.text.partition(' ')[2].strip()
    if not text:
        bot.reply_to(message, t(cid, 'admin_broadcast_usage'))
        return
    users = db.get_all_approved_users()
    sent  = 0
    for uid in users:
        try:
            bot.send_message(uid, text)
            sent += 1
        except Exception:
            pass
    bot.reply_to(message, t(cid, 'admin_broadcast_done', count=sent))



# =============================================================
# Incoming files (cookies, upload to drive)
# =============================================================
@bot.message_handler(content_types=['document', 'video', 'audio', 'photo', 'voice', 'video_note'])
def handle_incoming_files(message):
    import db
    cid   = message.chat.id
    state = user_state.get(cid)
    db.touch_user_identity(
        cid,
        message.from_user.username,
        _display_name_from_user(message.from_user),
    )

    if cid != ADMIN_ID and not db.is_approved(cid):
        bot.reply_to(message, t(cid, 'not_approved'))
        return

    # ── rclone.conf upload — multi-tenant Google Drive setup ──────────────
    if (
        message.content_type == 'document'
        and message.document.file_name == 'rclone.conf'
    ):
        _handle_rclone_conf_upload(message, cid)
        return
    # ─────────────────────────────────────────────────────────────────────

    if message.content_type == 'document' and message.document.file_name.endswith('.txt'):
        fname = message.document.file_name
        if state == 'await_cookie_file' or 'cookie' in fname.lower():
            try:
                info = bot.get_file(message.document.file_id)
                _fp = _resolve_local_bot_api_path(info.file_path)
                if _fp.startswith('/'):
                    data = Path(_fp).read_bytes()
                else:
                    data = bot.download_file(_fp)
                base = os.path.splitext(fname)[0].lower()
                base = re.sub(r'[^a-zA-Z0-9_\-]', '_', base)
                if base in ('cookies', 'cookie', 'cookies_txt', ''):
                    with cache_lock:
                        url_cache[(cid, 'pending_cookie')] = data
                    user_state[cid] = 'await_cookie_name'
                    bot.reply_to(message, t(cid, 'cookie_received_ask_name'))
                else:
                    save_cookie_data(base, data, cid)
                    user_state[cid] = None
                    bot.reply_to(message, t(cid, 'cookie_saved', name=base),
                                 reply_markup=main_menu_markup(cid))
            except Exception as e:
                bot.reply_to(message, t(cid, 'cookie_error', e=e))
            return

    if state == 'await_cookie_file':
        bot.reply_to(message, t(cid, 'cookie_need_txt'))
        return

    from config import DOWNLOAD_DIR
    status_msg = bot.reply_to(message, t(cid, 'receiving_file'))
    try:
        if message.content_type == 'document':
            fid, fname = message.document.file_id, message.document.file_name
        elif message.content_type == 'video':
            fid, fname = message.video.file_id, f"video_{message.video.file_id}.mp4"
        elif message.content_type == 'audio':
            fid = message.audio.file_id
            fname = getattr(message.audio, 'file_name', f"audio_{fid}.mp3")
        elif message.content_type == 'photo':
            fid, fname = message.photo[-1].file_id, f"photo_{message.photo[-1].file_id}.jpg"
        elif message.content_type == 'voice':
            fid, fname = message.voice.file_id, f"voice_{message.voice.file_id}.ogg"
        elif message.content_type == 'video_note':
            fid, fname = message.video_note.file_id, f"vidnote_{message.video_note.file_id}.mp4"
        else:
            bot.edit_message_text(t(cid, 'unsupported_type'), cid, status_msg.message_id)
            return

        info = bot.get_file(fid)
        file_path = _resolve_local_bot_api_path(info.file_path)
        fp = os.path.join(DOWNLOAD_DIR, fname)
        if file_path.startswith('/') and os.path.exists(file_path):
            # Local Bot API server: read the file directly from the shared volume.
            with open(file_path, 'rb') as _src, open(fp, 'wb') as _dst:
                _dst.write(_src.read())
        else:
            # Fallback: download via cloud Telegram API (works without Local API)
            data = bot.download_file(info.file_path)
            with open(fp, 'wb') as f:
                f.write(data)

        # If the user already set a default destination (not 'manual'), upload
        # straight to it — no menu. Otherwise show the per-file picker.
        from dest_helpers import should_ask_dest
        import db as _db
        default_dest = _db.get_upload_dest(cid)
        if default_dest in ('gd', 's3', 'github'):
            try:
                bot.edit_message_text(f"⏳ آپلود به: {default_dest}...", cid, status_msg.message_id)
            except Exception:
                pass
            from uploaders.smart_dest import smart_dest
            smart_dest(fp, status_msg, dest=default_dest, folder_name="FilesFromTel",
                       task_info={'chat_id': cid, 'user_id': cid})
            return

        # Ask which destination to use for THIS file (per-file choice).
        # Telegram option removed: the file is already in Telegram.
        from menu import destination_pick_markup
        config.pending_uploads[cid] = {'fp': fp, 'status_msg_id': status_msg.message_id}
        bot.edit_message_text(
            "فایل دریافت شد. مقصد آپلود رو انتخاب کن:",
            cid, status_msg.message_id,
            reply_markup=destination_pick_markup(cid))

    except Exception as e:
        text = f"❌ {friendly_error(str(e), cid=cid)}"
        try:
            bot.edit_message_text(text, cid, status_msg.message_id)
        except Exception:
            bot.send_message(cid, text)


# =============================================================
# rclone.conf handler — multi-tenant Google Drive onboarding
# =============================================================
# Maximum accepted size for an rclone.conf file.
# A real rclone.conf with OAuth tokens is well under 5 KB;
# 512 KB is a generous ceiling that still blocks malicious large files.
_MAX_RCLONE_CONF_BYTES = 512 * 1024  # 512 KB


def _handle_rclone_conf_upload(message, cid: int) -> None:
    """
    Persist a user-supplied rclone.conf to:
        /app/user_configs/rclone_<user_id>.conf

    The file is validated to contain the bare minimum rclone remote
    declaration before it is saved, so garbage files are rejected early.
    A Persian success message is sent on success; a descriptive error
    message is sent on any failure.
    """
    status_msg = bot.reply_to(message, "⏳ در حال پردازش فایل rclone.conf…")

    try:
        # ── Bug 5 fix: reject oversized files BEFORE reading into RAM ─────
        # Telegram always populates file_size; the Local Bot API lifts the
        # normal 20 MB cap to 2 GB, so we must enforce our own limit here.
        reported_size = message.document.file_size or 0
        if reported_size > _MAX_RCLONE_CONF_BYTES:
            bot.edit_message_text(
                f"❌ فایل ارسالی بیش از حد بزرگ است ({reported_size // 1024} KB).\n"
                "یک فایل <code>rclone.conf</code> معتبر باید کمتر از 512 KB باشد.",
                cid,
                status_msg.message_id,
                parse_mode='HTML',
            )
            return
        # ─────────────────────────────────────────────────────────────────

        # Download the file from Telegram / local bot-api server
        file_info = bot.get_file(message.document.file_id)
        file_path = _resolve_local_bot_api_path(file_info.file_path)

        if file_path.startswith('/'):
            # Local Bot-API server — file already on shared volume.
            # Double-check the on-disk size in case file_size was spoofed
            # or the Telegram metadata was stale.
            disk_size = os.path.getsize(file_path)
            if disk_size > _MAX_RCLONE_CONF_BYTES:
                bot.edit_message_text(
                    f"❌ فایل ارسالی بیش از حد بزرگ است ({disk_size // 1024} KB).\n"
                    "یک فایل <code>rclone.conf</code> معتبر باید کمتر از 512 KB باشد.",
                    cid,
                    status_msg.message_id,
                    parse_mode='HTML',
                )
                return
            raw_data = Path(file_path).read_bytes()
        else:
            # Cloud Telegram servers
            raw_data = bot.download_file(file_path)

        conf_text = raw_data.decode('utf-8', errors='replace')

        # ── Basic sanity check ────────────────────────────────────────────
        if '[gdrive]' not in conf_text or 'type = drive' not in conf_text:
            bot.edit_message_text(
                "❌ فایل ارسالی معتبر نیست.\n"
                "لطفاً فایل <code>rclone.conf</code> را که از اسکریپت Colab دریافت کردید ارسال کنید.",
                cid,
                status_msg.message_id,
                parse_mode='HTML',
            )
            return

        # ── Persist ───────────────────────────────────────────────────────
        dest = os.path.join(USER_CONFIGS_DIR, f"rclone_{cid}.conf")
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(conf_text)

        bot.edit_message_text(
            "✅ درایو شما با موفقیت متصل شد!\n"
            "فایل‌های شما از این به بعد در پوشه <b>TeleCloud-Downloads</b> ذخیره می‌شوند.",
            cid,
            status_msg.message_id,
            parse_mode='HTML',
        )

    except Exception as exc:
        try:
            bot.edit_message_text(
                f"❌ خطا در پردازش فایل: <code>{html.escape(str(exc))}</code>",
                cid,
                status_msg.message_id,
                parse_mode='HTML',
            )
        except Exception:
            bot.send_message(cid, f"❌ خطا: {exc}")


# =============================================================
# Main text message handler
# =============================================================
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    cid   = message.chat.id
    text  = message.text.strip() if message.text else ""
    state = user_state.get(cid)
    db.touch_user_identity(
        cid,
        message.from_user.username,
        _display_name_from_user(message.from_user),
    )

    # Auth gate (admins bypass, approved users pass, others are blocked)
    if cid != ADMIN_ID and not db.is_approved(cid):
        # Allow the language selection to pass through as a callback, not here
        bot.send_message(cid, t(cid, 'not_approved'))
        return

    if isinstance(state, str) and state.startswith('await_cookie_rename|'):
        old_name = state.split('|')[1]
        new_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', text).lower()
        if not new_name:
            bot.send_message(cid, t(cid, 'cookie_invalid_name'))
            return
        try:
            os.rename(get_cookie_path(old_name, cid), get_cookie_path(new_name, cid))
            from cookies import (_cookie_lock as _ck_lock, _cookies_state as _ck_state,
                                 _save_cookies_state as _ck_save, _state_key as _ck_key)
            with _ck_lock:
                st = _ck_state()
                st[_ck_key(cid, new_name)] = st.pop(_ck_key(cid, old_name), True)
                _ck_save(st)
            user_state[cid] = None
            bot.send_message(cid, t(cid, 'cookie_rename_done', new_name=new_name),
                             reply_markup=main_menu_markup(cid))
        except Exception as e:
            bot.send_message(cid, t(cid, 'cookie_error', e=e))
        return

    if state == 'await_cookie_name':
        name = re.sub(r'[^a-zA-Z0-9_\-]', '_', text).lower()
        if not name:
            bot.send_message(cid, t(cid, 'cookie_invalid_name'))
            return
        with cache_lock:
            pending = url_cache.get((cid, 'pending_cookie'))
        if pending:
            save_cookie_data(name, pending if isinstance(pending, bytes) else pending.encode('utf-8'), cid)
            with cache_lock:
                url_cache.pop((cid, 'pending_cookie'), None)
            user_state[cid] = None
            bot.send_message(cid, t(cid, 'cookie_saved', name=name), reply_markup=main_menu_markup(cid))
        else:
            bot.send_message(cid, t(cid, 'cookie_data_not_found'))
            user_state[cid] = None
        return

    if state == 'await_cookie_text':
        if "# Netscape" in text or "\t" in text:
            with cache_lock:
                url_cache[(cid, 'pending_cookie')] = text.encode('utf-8')
            user_state[cid] = 'await_cookie_name'
            bot.send_message(cid, t(cid, 'cookie_text_received'))
        else:
            bot.send_message(cid, t(cid, 'cookie_invalid_format'))
        return

    if isinstance(state, str) and state.startswith('await_playlist_count|'):
        _handle_playlist_count(cid, text, state)
        return

    if isinstance(state, str) and state.startswith('await_scpl_count|'):
        _handle_scpl_custom_count(cid, text, state)
        return

    if cid == ADMIN_ID and state == 'await_admin_user_search':
        user_state[cid] = None
        from callbacks import render_admin_users_list
        query = text.strip()
        render_admin_users_list(
            chat_id=cid,
            page=1,
            query=query if query else None,
            message_id=None,
        )
        return

    if _handle_menu(cid, text, message):
        return

    if text.startswith(("http://", "https://")):
        text = clean_url(text)

    _handle_url(message, cid, text, state)


# =============================================================
# Menu dispatcher
# =============================================================
def _handle_menu(cid, text, message) -> bool:
    # Collect both FA and EN button labels so either language works
    if text in (t(cid, 'btn_settings'), "تنظیمات ⚙️", "Settings ⚙️"):
        from menu import settings_inline_markup
        user_state[cid] = None
        bot.send_message(cid, t(cid, 'settings_panel_title'),
                         reply_markup=settings_inline_markup(cid))
        return True

    # ── Profile button ────────────────────────────────────────
    if text in (t(cid, 'btn_profile'), "👤 پروفایل من", "👤 My Profile"):
        _send_profile_stats(cid)
        return True

    if text in (t(cid, 'btn_ytdlp'), "🔽 دانلود با yt-dlp", "🔽 Download with yt-dlp"):
        user_state[cid] = 'ytdlp'
        bot.send_message(cid, t(cid, 'ytdlp_activated'))
        return True

    if text in (t(cid, 'btn_torrent'), "🧲 دانلود تورنت", "🧲 Download Torrent"):
        user_state[cid] = 'torrent'
        bot.send_message(cid, t(cid, 'ask_magnet'))
        return True

    if text in (t(cid, 'btn_direct'), "🌐 دانلود لینک مستقیم", "🌐 Direct Link Download"):
        user_state[cid] = 'direct'
        bot.send_message(cid, t(cid, 'ask_direct'))
        return True

    if text in (t(cid, 'btn_cookie'), "🍪 مدیریت کوکی", "🍪 Cookie Manager"):
        user_state[cid] = None
        bot.send_message(cid, t(cid, 'cookie_manage'), reply_markup=cookie_list_markup(cid))
        return True

    if text in (t(cid, 'btn_queue'), "📊 وضعیت صف", "📊 Queue Status"):
        from downloader_queue import get_queue_items
        q_items = get_queue_items()
        with config.current_tasks_lock:
            active_tasks = list(config.current_tasks.values())
        lines   = []
        unknown = t(cid, 'queue_unknown')
        if active_tasks:
            for act in active_tasks:
                a_title = act.get('title') or act.get('url', unknown)
                lines.append(t(cid, 'queue_running', type=act['type'], title=a_title))
        else:
            lines.append(t(cid, 'queue_nothing_running'))
        if not q_items:
            lines.append(t(cid, 'queue_empty'))
            bot.send_message(cid, "\n".join(lines) + f"\n\n💾 {get_free_space()}")
        else:
            lines.append(t(cid, 'queue_waiting', count=len(q_items)))
            for i, item in enumerate(q_items):
                i_title = item.get('title') or item.get('url', unknown)
                lines.append(f"{i+1}. {item['type']} | {i_title}")
            markup = types.InlineKeyboardMarkup(row_width=5)
            btns = [types.InlineKeyboardButton(f"❌ {i+1}", callback_data=f"qrm|{i}") for i in range(len(q_items))]
            markup.add(*btns)
            markup.row(types.InlineKeyboardButton(t(cid, 'queue_clear_btn'), callback_data="qclear"))
            markup.row(types.InlineKeyboardButton(t(cid, 'queue_refresh_btn'), callback_data="qrefresh"))
            bot.send_message(cid, "\n".join(lines) + f"\n\n💾 {get_free_space()}", reply_markup=markup)
        return True

    if text in (t(cid, 'btn_cancel'), "❌ لغو عملیات فعلی", "❌ Cancel Current Task"):
        with config.current_tasks_lock:
            # Collect all tasks that belong to this user (multiple possible
            # if MAX_CONCURRENT_DOWNLOADS > 1 and this user queued several).
            my_tasks = [tk for tk in config.current_tasks.values()
                        if tk.get('chat_id') == cid]
        if my_tasks or config.rclone_process:
            for tk in my_tasks:
                tk['_stop'].set()
            if config.rclone_process:
                config.stop_event.set()  # rclone checks the global event
                try:
                    config.rclone_process.terminate()
                except Exception:
                    pass
            bot.send_message(cid, t(cid, 'cancel_requested'))
        else:
            bot.send_message(cid, t(cid, 'cancel_nothing'))
        return True

    if text in (t(cid, 'btn_help'), "ℹ️ راهنما", "ℹ️ Help"):
        bot.send_message(cid, _build_help_text(cid), reply_markup=main_menu_markup(cid))
        return True

    if text in (t(cid, 'btn_change_lang'), "تغییر زبان 🌐", "Change Language 🌐"):
        mk = types.InlineKeyboardMarkup()
        mk.row(
            types.InlineKeyboardButton("English", callback_data="lang|en"),
            types.InlineKeyboardButton("فارسی",   callback_data="lang|fa"),
        )
        bot.send_message(cid, t(cid, 'lang_select'), reply_markup=mk)
        return True

    return False


def _build_help_text(cid: int) -> str:
    """
    Up-to-date usage guide shown by the Help button.
    Keeps instructions aligned with the current menu flow.
    """
    lang = get_lang(cid)

    if lang == 'fa':
        text = (
            "📖 راهنمای سریع\n\n"
            "1) /start را بزنید و زبان را انتخاب کنید.\n"
            "2) لینک بفرستید (YouTube/Instagram/Direct/Magnet).\n"
            "3) از دکمه ⚙️ تنظیمات برای انتخاب حالت‌ها استفاده کنید:\n"
            "   - Media: ویدیو یا صوت\n"
            "   - Format / Quality\n"
            "   - Upload: تلگرام / گوگل درایو / پرسش هر بار\n"
            "   - Subtitle / Chapters\n"
            "4) برای لینک‌های محدود، از 🍪 Cookie Manager کوکی اضافه کنید.\n"
            "5) وضعیت دانلودها را از 📊 Queue Status ببینید.\n"
            "6) اطلاعات مصرف روزانه را از 👤 My Profile ببینید.\n\n"
            "☁️ اتصال گوگل درایو:\n"
            "از داخل ⚙️ تنظیمات روی گزینه Google Drive بزنید و فایل rclone.conf را ارسال کنید.\n\n"
            "❌ لغو عملیات فعلی:\n"
            "با دکمه «Cancel Current Task» دانلود/آپلود جاری متوقف می‌شود."
        )
        if cid == ADMIN_ID:
            text += (
                "\n\n🔐 دستورات ادمین:\n"
                "/adduser <id>\n"
                "/deluser <id>\n"
                "/setquota <id> <files> <GB> [<monthly_files> <monthly_GB>]\n"
                "/users\n"
                "/togglereg\n"
                "/broadcast <message>"
            )
        return text

    text = (
        "📖 Quick Help\n\n"
        "1) Press /start and choose your language.\n"
        "2) Send a link (YouTube/Instagram/Direct/Magnet).\n"
        "3) Open ⚙️ Settings to configure:\n"
        "   - Media mode (video/audio)\n"
        "   - Format and quality\n"
        "   - Upload destination (Telegram/Google Drive/Ask every time)\n"
        "   - Subtitle and chapters\n"
        "4) For restricted content, add site cookies in 🍪 Cookie Manager.\n"
        "5) Check active/waiting downloads in 📊 Queue Status.\n"
        "6) View your daily usage in 👤 My Profile.\n\n"
        "☁️ Google Drive setup:\n"
        "In ⚙️ Settings, tap Google Drive and send your rclone.conf file.\n\n"
        "❌ Cancel current task:\n"
        "Use the 'Cancel Current Task' button to stop running download/upload jobs."
    )
    if cid == ADMIN_ID:
        text += (
            "\n\n🔐 Admin commands:\n"
            "/adduser <id>\n"
            "/deluser <id>\n"
            "/setquota <id> <files> <GB> [<monthly_files> <monthly_GB>]\n"
            "/users\n"
            "/togglereg\n"
            "/broadcast <message>"
        )
    return text


# =============================================================
# Link detection and routing
# =============================================================
def _resolve_redirect(url: str, timeout: int = 5) -> str:
    """Follow HTTP redirects and return the final URL.
    Fixes short links like on.soundcloud.com, t.co, bit.ly, etc.
    """
    try:
        import urllib.request
        req = urllib.request.Request(
            url, method='HEAD',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.url
    except Exception:
        return url


def _handle_url(message, cid, text, state):
    # ── Resolve redirect/short links before routing ──────────
    if text.startswith(("http://", "https://")):
        text = _resolve_redirect(text)
    # ─────────────────────────────────────────────────────────
    cur = state
    if cur == 'ytdlp':
        if "youtube.com" in text or "youtu.be" in text:
            cur = 'youtube'
        elif text.startswith("magnet:?"):
            cur = 'torrent'
        elif text.startswith(("http://", "https://")):
            cur = 'social'
        else:
            bot.reply_to(message, t(cid, 'invalid_link'))
            return
    elif cur is None:
        if "youtube.com" in text or "youtu.be" in text:
            cur = 'youtube'
        elif text.startswith("magnet:?"):
            cur = 'torrent'
        elif text.startswith(("http://", "https://")):
            cur = 'social' if _is_ytdlp_url(text) else 'direct'
        else:
            bot.reply_to(message, t(cid, 'unknown_link'),
                         reply_markup=main_menu_markup(cid))
            return

    if cur == 'youtube':
        _handle_youtube_link(message, cid, text)
    elif cur == 'torrent':
        _handle_torrent_link(message, cid, text)
    elif cur == 'direct':
        _handle_direct_link(message, cid, text)
    elif cur == 'social':
        _handle_social_link(message, cid, text)


def _handle_youtube_link(message, cid, text):
    if "youtube.com" not in text and "youtu.be" not in text:
        bot.reply_to(message, t(cid, 'not_youtube'))
        return
    msg = bot.reply_to(message, t(cid, 'checking_link'))
    key = (cid, msg.message_id)
    with cache_lock:
        url_cache[key] = text
    opts = {'extract_flat': True, 'quiet': True, 'js_runtimes': {'deno': {}, 'node': {}}}
    cf   = active_cookies_file(text, cid)
    if cf:
        opts['cookiefile'] = cf
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(text, download=False)

        unknown = t(cid, 'unknown_title')

        if 'entries' in info:
            count  = len(list(info['entries']))
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton(
                    t(cid, 'yt_playlist_label', count=count),
                    callback_data=f"yt|pl|{msg.message_id}"),
                types.InlineKeyboardButton(
                    t(cid, 'yt_playlist_mp3'),
                    callback_data=f"yt|pl_audio|{msg.message_id}"),
            )
            bot.edit_message_text(
                t(cid, 'yt_playlist_info', title=info.get('title', unknown), count=count),
                cid, msg.message_id, reply_markup=markup)
        else:
            audio   = is_audio_mode(cid)
            quality = 'manual' if audio else get_quality(cid)
            title   = info.get('title', unknown)
            dur     = info.get('duration', 0)
            m, s    = divmod(dur, 60)
            s_str   = f"{s:02d}"

            if audio:
                fmt, audio_only = 'bestaudio/best', True
                dest = get_dest(cid)
                if should_ask_dest(cid):
                    dest_mk = types.InlineKeyboardMarkup()
                    dest_mk.row(
                        types.InlineKeyboardButton('🗄 S3', callback_data=f"ytd|audio|s3|{msg.message_id}"),
                        types.InlineKeyboardButton(t(cid, 'btn_gd'), callback_data=f"ytd|audio|gd|{msg.message_id}"),
                    )
                    bot.edit_message_text(
                        t(cid, 'yt_audio_dest_msg', title=title, m=m, s=s_str),
                        cid, msg.message_id, reply_markup=dest_mk)
                else:
                    enqueue({
                        'type': 'youtube', 'url': text, 'format': fmt,
                        'chat_id': cid, 'audio_only': True,
                        'dest': dest, 'title': title,
                        'audio_format':  get_audio_format(cid),
                        'audio_quality': get_audio_quality(cid),
                        'video_format':  get_video_format(cid),
                        'subtitle':      get_subtitle(cid),
                        'chapters':      get_chapters(cid),
                    })
                    pos = len(config.pending_queue)
                    bot.edit_message_text(
                        t(cid, 'yt_queued',
                          title=title, quality='🎵 MP3',
                          dest_icon='📱' if dest == 'tg' else '☁️',
                          pos=pos),
                        cid, msg.message_id)

            elif quality != 'manual':
                fmt, audio_only = YT_FMT_MAP[quality]
                dest = get_dest(cid)
                yt_label = YT_LABELS.get(quality, quality)
                if should_ask_dest(cid):
                    from menu import dest_pick_markup
                    dest_mk = dest_pick_markup(cid, prefix=f"ytd|{quality}|{msg.message_id}", back=f"ytd|{quality}|{msg.message_id}|back")
                    bot.edit_message_text(
                        t(cid, 'yt_quality_dest_msg', title=title, m=m, s=s_str, quality=yt_label),
                        cid, msg.message_id, reply_markup=dest_mk)
                else:
                    enqueue({
                        'type': 'youtube', 'url': text, 'format': fmt,
                        'chat_id': cid, 'audio_only': audio_only,
                        'dest': dest, 'title': title,
                        'audio_format':  get_audio_format(cid),
                        'audio_quality': get_audio_quality(cid),
                        'video_format':  get_video_format(cid),
                        'subtitle':      get_subtitle(cid),
                        'chapters':      get_chapters(cid),
                    })
                    pos = len(config.pending_queue)
                    bot.edit_message_text(
                        t(cid, 'yt_queued',
                          title=title, quality=yt_label,
                          dest_icon='📱' if dest == 'tg' else '☁️',
                          pos=pos),
                        cid, msg.message_id)

            else:
                bot.edit_message_text(t(cid, 'fetching_quality'), cid, msg.message_id)
                sizes = get_format_sizes(text, cid)

                def sz(k):
                    b = sizes.get(k, 0)
                    return f" ({fmt_size(b)})" if b else ""

                markup = types.InlineKeyboardMarkup()
                markup.row(
                    types.InlineKeyboardButton(f"1080p{sz(1080)}", callback_data=f"yt|1080|{msg.message_id}"),
                    types.InlineKeyboardButton(f"720p{sz(720)}",   callback_data=f"yt|720|{msg.message_id}"),
                    types.InlineKeyboardButton(f"480p{sz(480)}",   callback_data=f"yt|480|{msg.message_id}"),
                )
                markup.row(
                    types.InlineKeyboardButton(
                        f"{t(cid, 'best_quality')}{sz('best')}",
                        callback_data=f"yt|best|{msg.message_id}"),
                )
                bot.edit_message_text(
                    t(cid, 'select_quality', title=title, m=m, s=s_str),
                    cid, msg.message_id, reply_markup=markup)

    except Exception as e:
        bot.edit_message_text(f"❌ {friendly_error(str(e), cid=cid)}", cid, msg.message_id)


def _handle_torrent_link(message, cid, text):
    if not text.startswith("magnet:?"):
        bot.reply_to(message, t(cid, 'not_magnet'))
        return
    key = (cid, message.message_id)
    with cache_lock:
        url_cache[key] = text
    if not should_ask_dest(cid):
        enqueue({'type': 'torrent', 'url': text, 'chat_id': cid,
                 'dest': get_dest(cid)})
        dest_icon = '📱' if cid in config.tg_upload_mode else '☁️'
        bot.reply_to(message, t(cid, 'torrent_queued', dest_icon=dest_icon))
    else:
        from menu import dest_pick_markup
        markup = dest_pick_markup(cid, prefix=f"tr|{message.message_id}", back=f"tr|{message.message_id}|back")
        bot.reply_to(message, t(cid, 'select_dest'), reply_markup=markup)


def _handle_direct_link(message, cid, text):
    key = (cid, message.message_id)
    with cache_lock:
        url_cache[key] = text
    if not should_ask_dest(cid):
        enqueue({'type': 'direct', 'url': text, 'chat_id': cid,
                 'dest': get_dest(cid)})
        dest_icon = '📱' if cid in config.tg_upload_mode else '☁️'
        bot.reply_to(message, t(cid, 'direct_queued', dest_icon=dest_icon))
    else:
        from menu import dest_pick_markup
        markup = dest_pick_markup(cid, prefix=f"dl|{message.message_id}", back=f"dl|{message.message_id}|back")
        bot.reply_to(message, t(cid, 'select_dest'), reply_markup=markup)


# =============================================================
# Social-link helpers (Bug 4a & 4b)
# =============================================================

# Domains that serve audio content only — no video formats exist.
# Sending these through the video-quality probe wastes an API round-trip
# and produces a confusing "Best Quality" video button for audio tracks.
_AUDIO_ONLY_DOMAINS = {
    'soundcloud.com', 'on.soundcloud.com', 'm.soundcloud.com',
    'spotify.com', 'open.spotify.com',
    'bandcamp.com',
    'audiomack.com',
    'deezer.com',
    'tidal.com',
}


def _url_is_playlist(url: str) -> bool:
    """
    Return True when noplaylist=True is safe (i.e. the URL is a single item).
    Return False when the URL is a collection that should be downloaded as a
    playlist (noplaylist must be omitted / False).

    Currently handles SoundCloud /sets/ paths; extend the mapping as needed.
    """
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host   = parsed.netloc.replace('www.', '')
    path   = parsed.path
    # SoundCloud album / set URLs contain "/sets/" in the path.
    if host in ('soundcloud.com', 'on.soundcloud.com', 'm.soundcloud.com'):
        if '/sets/' in path:
            return False   # it IS a playlist → do NOT set noplaylist
    return True   # safe to treat as a single item


# =============================================================
# SoundCloud playlist detection & initial handler
# =============================================================
def _is_soundcloud_playlist(url: str) -> bool:
    """Return True only when the URL is a SoundCloud playlist/set.
    Single track URLs like soundcloud.com/artist/track-name return False.
    """
    parsed = urlparse(url)
    host   = parsed.netloc.replace('www.', '').lower()
    if host not in ('soundcloud.com', 'm.soundcloud.com', 'on.soundcloud.com'):
        return False
    return '/sets/' in parsed.path


def _handle_soundcloud_playlist(message, cid, text):
    """Fetch SoundCloud playlist metadata and show a download button."""
    msg = bot.reply_to(message, t(cid, 'sc_fetching_playlist'))

    cf = active_cookies_file(text, cid)
    opts = {'extract_flat': True, 'quiet': True}
    if cf:
        opts['cookiefile'] = cf

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(text, download=False)
    except Exception as e:
        try:
            bot.edit_message_text(
                t(cid, 'sc_playlist_fetch_error', error=friendly_error(str(e), cid=cid)),
                cid, msg.message_id)
        except Exception:
            pass
        return

    title   = info.get('title', 'SoundCloud Playlist')
    entries = list(info.get('entries', []))
    count   = len(entries)

    # Store the URL keyed by the status message's message_id
    with cache_lock:
        url_cache[msg.message_id] = text

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        t(cid, 'sc_playlist_audio_btn'),
        callback_data=f"scpl_info|{msg.message_id}",
    ))

    try:
        bot.edit_message_text(
            t(cid, 'sc_playlist_info', title=title, count=count),
            cid, msg.message_id, reply_markup=markup)
    except Exception:
        pass


def _handle_scpl_custom_count(cid, text, state):
    """Handle user typing a custom track count for SoundCloud playlist."""
    parts = state.split('|')
    mid   = int(parts[1])
    try:
        count = int(text.strip())
        if count < 1:
            raise ValueError()
    except Exception:
        bot.send_message(cid, t(cid, 'playlist_invalid_count'))
        return

    user_state[cid] = None

    with cache_lock:
        url = url_cache.get(mid)
    if not url:
        bot.send_message(cid, t(cid, 'playlist_link_expired'))
        return

    if not should_ask_dest(cid):
        dest = get_dest(cid)
        enqueue({
            'type': 'soundcloud_playlist',
            'chat_id': cid,
            'url': url,
            'count': count,
            'dest': dest,
            'audio_only': True,
            'format': 'bestaudio/best',
        })
        bot.send_message(
            cid,
            t(cid, 'sc_playlist_queued',
              count=count,
              dest_icon='📱' if dest == 'tg' else '☁️'))
    else:
        dest_mk = types.InlineKeyboardMarkup()
        dest_mk.row(
            types.InlineKeyboardButton('🗄 S3',
                callback_data=f"scpl_dest|{mid}|{count}|s3"),
            types.InlineKeyboardButton(t(cid, 'btn_gd'),
                callback_data=f"scpl_dest|{mid}|{count}|gd"),
        )
        bot.send_message(
            cid,
            t(cid, 'sc_playlist_dest_ask', count=count),
            reply_markup=dest_mk)


def _handle_social_link(message, cid, text):
    # ── SoundCloud playlist intercept ────────────────────────────
    if _is_soundcloud_playlist(text):
        _handle_soundcloud_playlist(message, cid, text)
        return

    domain = urlparse(text).netloc.replace('www.', '')
    msg    = bot.reply_to(message, t(cid, 'fetching_info', domain=domain))
    key    = (cid, msg.message_id)
    with cache_lock:
        url_cache[key] = text

    quality = get_quality(cid)
    audio   = is_audio_mode(cid)

    # ── Bug 4b: force audio-only path for known audio-centric domains ────────
    # Regardless of the user's video/audio mode setting, platforms like
    # SoundCloud and Spotify never provide video streams. Routing them through
    # the video format probe wastes a network round-trip and shows a confusing
    # "Best Quality" (video) button for what is purely audio content.
    base_domain = domain.split(':')[0]  # strip port if present
    is_audio_domain = base_domain in _AUDIO_ONLY_DOMAINS

    if audio or is_audio_domain:
        dest = get_dest(cid)
        if should_ask_dest(cid):
            dest_mk = types.InlineKeyboardMarkup()
            dest_mk.row(
                types.InlineKeyboardButton('🗄 S3',
                    callback_data=f"scd|a|bestaudio/best|s3|{msg.message_id}"),
                types.InlineKeyboardButton(t(cid, 'btn_gd'),
                    callback_data=f"scd|a|bestaudio/best|gd|{msg.message_id}"),
            )
            try:
                bot.edit_message_text(
                    t(cid, 'social_audio_dest_msg', domain=domain),
                    cid, msg.message_id, reply_markup=dest_mk)
            except Exception:
                pass
        else:
            enqueue({
                'type': 'social', 'chat_id': cid, 'url': text,
                'dest': dest, 'format': 'bestaudio/best',
                'audio_only':    True,
                'audio_format':  get_audio_format(cid),
                'audio_quality': get_audio_quality(cid),
                'video_format':  get_video_format(cid),
                'subtitle':      get_subtitle(cid),
                'chapters':      get_chapters(cid),
            })
            try:
                bot.edit_message_text(
                    t(cid, 'social_queued',
                      domain=domain,
                      dest_icon='📱' if dest == 'tg' else '☁️'),
                    cid, msg.message_id)
            except Exception:
                pass
        return

    if quality != 'manual':
        dest = get_dest(cid)
        fmt = 'bestvideo+bestaudio/best' if quality == 'best' else f'bestvideo[height<={quality}]+bestaudio/best'
        if should_ask_dest(cid):
            dest_mk = types.InlineKeyboardMarkup()
            dest_mk.row(
                types.InlineKeyboardButton('🗄 S3',
                    callback_data=f"scd|v|{fmt}|s3|{msg.message_id}"),
                types.InlineKeyboardButton(t(cid, 'btn_gd'),
                    callback_data=f"scd|v|{fmt}|gd|{msg.message_id}"),
            )
            try:
                bot.edit_message_text(
                    t(cid, 'social_quality_dest_msg', domain=domain, quality=quality),
                    cid, msg.message_id, reply_markup=dest_mk)
            except Exception:
                pass
        else:
            enqueue({
                'type': 'social', 'chat_id': cid, 'url': text,
                'dest': dest, 'format': fmt,
                'audio_format':  get_audio_format(cid),
                'audio_quality': get_audio_quality(cid),
                'video_format':  get_video_format(cid),
                'subtitle':      get_subtitle(cid),
                'chapters':      get_chapters(cid),
            })
            try:
                bot.edit_message_text(
                    t(cid, 'social_quality_queued',
                      domain=domain, quality=quality,
                      dest_icon='📱' if dest == 'tg' else '☁️'),
                    cid, msg.message_id)
            except Exception:
                pass
        return

    def fetch_social_formats():
        cf   = active_cookies_file(text, cid)
        # Bug 4a: dynamically decide noplaylist based on the URL structure.
        # SoundCloud /sets/ URLs are playlists and must not be truncated to 1 track.
        opts = {'quiet': True, 'skip_download': True, 'noplaylist': _url_is_playlist(text), 'js_runtimes': {'deno': {}, 'node': {}}}
        if cf:
            opts['cookiefile'] = cf
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(text, download=False)
            title   = info.get('title', domain)[:40]
            formats = info.get('formats', [])
            seen_h     = set()
            video_fmts = []
            for f in reversed(formats):
                h = f.get('height')
                if not h or h in seen_h:
                    continue
                is_merged = (f.get('acodec') not in ('none', None) and
                             f.get('vcodec') not in ('none', None))
                if is_merged:
                    seen_h.add(h)
                    size = f.get('filesize') or f.get('filesize_approx') or 0
                    video_fmts.append((h, f['format_id'], size))
            if not video_fmts:
                for f in reversed(formats):
                    h = f.get('height')
                    if h and f.get('vcodec') not in ('none', None) and h not in seen_h:
                        seen_h.add(h)
                        size = f.get('filesize') or f.get('filesize_approx') or 0
                        video_fmts.append((h, f['format_id'], size))
            video_fmts.sort(key=lambda x: x[0], reverse=True)
            mid      = msg.message_id
            ask_dest = should_ask_dest(cid)
            prefix   = "sca" if not ask_dest else "scq"
            markup   = types.InlineKeyboardMarkup(row_width=2)
            btns     = []
            for h, fid, size in video_fmts[:4]:
                sz_str = f" ({fmt_size(size)})" if size else ""
                btns.append(types.InlineKeyboardButton(
                    f"📹 {h}p{sz_str}", callback_data=f"{prefix}|v|{fid}|{mid}"))
            if btns:
                markup.add(*btns)
            if not video_fmts:
                markup.add(types.InlineKeyboardButton(
                    t(cid, 'best_quality_btn'),
                    callback_data=f"{prefix}|b|best|{mid}"))
            try:
                bot.edit_message_text(
                    t(cid, 'social_select_quality', title=title),
                    cid, msg.message_id, reply_markup=markup)
            except Exception:
                pass
        except Exception as e:
            try:
                bot.edit_message_text(f"❌ {friendly_error(str(e), cid=cid)}", cid, msg.message_id)
            except Exception:
                pass

    threading.Thread(target=fetch_social_formats, daemon=True).start()


# =============================================================
# Playlist custom count
# =============================================================
def _handle_playlist_count(cid, text, state):
    parts   = state.split('|')
    mid     = int(parts[1])
    audio   = parts[2] == '1'
    quality = parts[3] if len(parts) > 3 else 'best'
    key     = (cid, mid)
    with cache_lock:
        url = url_cache.get(key)
    if not url:
        bot.send_message(cid, t(cid, 'playlist_link_expired'))
        user_state[cid] = None
        return
    try:
        count = int(text.strip())
        if count < 1:
            raise ValueError()
    except Exception:
        bot.send_message(cid, t(cid, 'playlist_invalid_count'))
        return
    user_state[cid] = None
    PL_FMT_MAP = {
        "1080": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best",
        "720":  "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best",
        "480":  "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best",
        "best": "bestvideo+bestaudio/best",
        "audio": "bestaudio/best",
    }
    if not should_ask_dest(cid):
        dest = get_dest(cid)
        fmt  = PL_FMT_MAP.get(quality, "bestvideo+bestaudio/best")
        if audio:
            fmt = "bestaudio/best"
        enqueue({
            'type': 'youtube_playlist', 'url': url, 'chat_id': cid,
            'end': count, 'audio_only': audio, 'format': fmt, 'dest': dest,
        })
        bot.send_message(
            cid,
            t(cid, 'playlist_queued',
              count=count,
              dest_icon='📱' if dest == 'tg' else '☁️'))
    else:
        media = t(cid, 'playlist_media_audio') if audio else t(cid, 'playlist_media_video', quality=quality)
        dest_mk = types.InlineKeyboardMarkup()
        dest_mk.row(
            types.InlineKeyboardButton('🗄 S3',
                callback_data=f"pld|{count}|s3|{mid}|{'1' if audio else '0'}|{quality}"),
            types.InlineKeyboardButton(t(cid, 'btn_gd'),
                callback_data=f"pld|{count}|gd|{mid}|{'1' if audio else '0'}|{quality}"),
        )
        bot.send_message(
            cid,
            t(cid, 'playlist_dest_msg', media=media, count=count),
            reply_markup=dest_mk)


# =============================================================
# Profile stats helper
# =============================================================
def _send_profile_stats(cid: int) -> None:
    """Send the user their daily + monthly usage stats from the DB.
    Admin gets global system-wide stats instead of a personal quota view.
    """
    from config import MAX_DAILY_FILES, MAX_DAILY_BYTES, MAX_MONTHLY_FILES, MAX_MONTHLY_BYTES, ADMIN_ID

    # ── Admin: show global system stats ────────────────────────
    if cid == ADMIN_ID:
        stats = db.get_global_stats()
        total_gb = stats['total_bytes'] / (1024 ** 3)
        bot.send_message(
            cid,
            t(cid, 'admin_profile_stats',
              total_approved=stats['total_approved'],
              total_files=stats['total_files'],
              total_gb=total_gb),
        )
        return

    # ── Regular user: show personal daily + monthly quota ────────
    row = db.get_user(cid)
    if row is None:
        db.add_user(cid, approved=db.is_approved(cid))
        row = db.get_user(cid)

    files_used  = row['files_downloaded']  if row else 0
    bytes_used  = row['bytes_downloaded']   if row else 0
    max_files   = (row['custom_quota_files']
                   if row and row['custom_quota_files'] is not None
                   else MAX_DAILY_FILES)
    max_bytes   = (row['custom_quota_bytes']
                   if row and row['custom_quota_bytes'] is not None
                   else MAX_DAILY_BYTES)

    monthly_files_used = row['monthly_files_downloaded'] if row else 0
    monthly_bytes_used = row['monthly_bytes_downloaded'] if row else 0
    max_monthly_files  = (row['custom_quota_monthly_files']
                          if row and row['custom_quota_monthly_files'] is not None
                          else MAX_MONTHLY_FILES)
    max_monthly_bytes  = (row['custom_quota_monthly_bytes']
                          if row and row['custom_quota_monthly_bytes'] is not None
                          else MAX_MONTHLY_BYTES)

    used_gb          = bytes_used  / (1024 ** 3)
    max_gb           = max_bytes   / (1024 ** 3)
    monthly_used_gb  = monthly_bytes_used / (1024 ** 3)
    monthly_max_gb   = max_monthly_bytes  / (1024 ** 3)

    bot.send_message(
        cid,
        t(cid, 'profile_stats',
          files=files_used, max_files=max_files,
          used_gb=used_gb,  max_gb=max_gb,
          monthly_files=monthly_files_used, max_monthly_files=max_monthly_files,
          monthly_used_gb=monthly_used_gb, monthly_max_gb=monthly_max_gb),
    )
