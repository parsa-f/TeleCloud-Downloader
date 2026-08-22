import os
from downloader_queue import enqueue
import logging
import re
import threading
import time
from telebot import types

import config
from config import (bot, stop_event,
                    cache_lock, url_cache, user_state, ADMIN_ID)
from cookies import (cookie_exists, is_cookie_enabled,
                     set_cookie_enabled, delete_cookie)
from menu import (main_menu_markup, cookie_list_markup,
                  cookie_item_markup, get_cookie_help)
from dest_helpers import get_dest, should_ask_dest
from playlist_menu import _show_playlist_menu, _show_playlist_count_menu
from downloaders.torrent import _do_torrent_download
from locales import t
from user_langs import set_lang
import db

logger = logging.getLogger(__name__)


PL_FMT_MAP = {
    "1080": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best",
    "720":  "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best",
    "480":  "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best",
    "best": "bestvideo+bestaudio/best",
    "audio":"bestaudio/best",
}

YT_FMT_MAP = {
    "1080": ("bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best", False),
    "720":  ("bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best",  False),
    "480":  ("bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best",  False),
    "best": ("bestvideo+bestaudio/best", False),
    "audio":("bestaudio/best", True),
}

YT_LABELS = {
    "1080": "1080p", "720": "720p", "480": "480p",
    "best": "⭐ بهترین", "audio": "🎵 MP3",
}


# =============================================================
# Main callback handler
# =============================================================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    import db
    cid  = call.message.chat.id
    data = call.data

    # ── Join-request flow (non-approved users) ───────────────────
    if data.startswith("joinreq|"):
        action = data.split('|')[1]
        if action == "request":
            from handlers import _pending_join_requests
            if cid in _pending_join_requests:
                bot.answer_callback_query(
                    call.id, t(cid, 'join_request_already_sent'), show_alert=True)
                return
            _pending_join_requests.add(cid)
            user  = call.from_user
            uname = user.username or "N/A"
            fname = ((user.first_name or '') + ' ' + (user.last_name or '')).strip() or 'N/A'
            admin_text = t(ADMIN_ID, 'join_request_admin_msg',
                           user_id=cid,
                           full_name=fname,
                           username=uname)
            mk = types.InlineKeyboardMarkup()
            mk.row(
                types.InlineKeyboardButton(
                    t(ADMIN_ID, 'btn_approve'),
                    callback_data=f"joinreq|approve|{cid}"),
                types.InlineKeyboardButton(
                    t(ADMIN_ID, 'btn_reject'),
                    callback_data=f"joinreq|reject|{cid}"),
            )
            try:
                bot.send_message(ADMIN_ID, admin_text,
                                 parse_mode='HTML', reply_markup=mk)
            except Exception:
                pass
            bot.answer_callback_query(call.id, t(cid, 'join_request_sent'), show_alert=True)
            return

        # Admin-side approval / rejection
        if action in ('approve', 'reject') and cid == ADMIN_ID:
            target_id = int(data.split('|')[2])
            from handlers import _pending_join_requests
            _pending_join_requests.discard(target_id)
            if action == 'approve':
                db.approve_user(target_id)
                bot.answer_callback_query(call.id, t(cid, 'join_approved_admin_toast'))
                try:
                    bot.send_message(target_id,
                                     t(target_id, 'join_approved_user_notify'),
                                     reply_markup=main_menu_markup(target_id))
                except Exception:
                    pass
            else:
                db.reject_user(target_id)
                bot.answer_callback_query(call.id, t(cid, 'join_rejected_admin_toast'))
                try:
                    bot.send_message(target_id, t(target_id, 'join_rejected_user_notify'))
                except Exception:
                    pass
            # Edit the admin's message to remove the buttons
            try:
                bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
            except Exception:
                pass
            return

        bot.answer_callback_query(call.id)
        return

    # ── Language selection ────────────────────────────────────
    if data.startswith("lang|"):
        lang = data.split("|")[1]
        set_lang(cid, lang)
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(cid, call.message.message_id)
        except Exception:
            pass
        # After language is set, continue the /start flow via DB check
        if cid == ADMIN_ID or db.is_approved(cid):
            user_state[cid] = None
            bot.send_message(cid, t(cid, 'bot_ready'), reply_markup=main_menu_markup(cid))
        else:
            # Show join-request button for unapproved users
            from config import REGISTRATION_OPEN
            if REGISTRATION_OPEN:
                db.approve_user(cid)
                user_state[cid] = None
                bot.send_message(cid, t(cid, 'bot_ready'), reply_markup=main_menu_markup(cid))
            else:
                mk = types.InlineKeyboardMarkup()
                mk.add(types.InlineKeyboardButton(
                    t(cid, 'btn_request_access'),
                    callback_data="joinreq|request",
                ))
                bot.send_message(cid, t(cid, 'registration_closed'), reply_markup=mk)
        return

    if data.startswith("aum|"):
        _handle_admin_user_panel(call, cid, data)
        return

    # ── Destination picker (dest|tg / dest|gd / dest|s3 / dest|github) ──────
    # The per-file picker builds callback_data "dest|<key>" (no prefix), which
    # used to fall through every branch below and silently dead-end the button.
    if data.startswith("dest|"):
        _handle_dest_pick(call, cid, data)
        return

    if data.startswith("set|"):
        parts  = data.split('|')
        action = parts[1]
        from menu import settings_inline_markup
        from dest_helpers import (
            cycle_quality, toggle_audio_mode,
            get_quality_label, get_audio_mode_label,
            cycle_audio_quality, get_audio_quality_label,
            cycle_video_format, get_video_format_label,
            cycle_audio_format, get_audio_format_label,
            cycle_subtitle, get_subtitle_label,
            toggle_chapters, get_chapters_label,
            is_audio_mode,
        )

        if action == "mode" and len(parts) >= 3:
            new_mode = parts[2]  # ytdlp | torrent | direct | auto
            config.user_download_mode[cid] = new_mode
            toast = t(cid, 'mode_set_toast')

        elif action == "destmenu":
            # Open explicit destination picker as a new message
            bot.answer_callback_query(call.id)
            from menu import destination_pick_markup
            bot.send_message(cid, "مقصد آپلود رو انتخاب کن:",
                             reply_markup=destination_pick_markup(cid))
            return

        elif action == "back":
            # Return to the main settings panel (from destination picker)
            bot.answer_callback_query(call.id)
            from menu import settings_inline_markup
            try:
                bot.edit_message_reply_markup(
                    cid, call.message.message_id,
                    reply_markup=settings_inline_markup(cid))
            except Exception:
                pass
            return

        elif action == "upload":
            current = db.get_upload_dest(cid)
            # cycle: tg → gd → s3 → github → tg
            if current == 'tg':
                db.set_upload_dest(cid, 'gd')
                toast = 'مقصد آپلود: Google Drive'
            elif current == 'gd':
                db.set_upload_dest(cid, 's3')
                toast = 'مقصد آپلود: Railway S3'
            elif current == 's3':
                db.set_upload_dest(cid, 'github')
                toast = 'مقصد آپلود: GitHub شخصی'
            else:
                db.set_upload_dest(cid, 'tg')
                toast = 'مقصد آپلود: تلگرام'

        elif action == "qual":
            # Context-aware: audio mode → audio quality, video mode → video quality
            # Each mode remembers its own last setting independently
            if is_audio_mode(cid):
                cycle_audio_quality(cid)
                label = get_audio_quality_label(cid)
            else:
                cycle_quality(cid)
                label = get_quality_label(cid)
            toast = t(cid, 'quality_set_toast', label=label)

        elif action == "media":
            # Toggle mode; each mode retains its own quality/format state (no reset)
            toggle_audio_mode(cid)
            label = get_audio_mode_label(cid)
            toast = t(cid, 'media_set_toast', label=label)

        elif action == "fmt":
            # Context-aware format cycle: audio codec vs video container
            if is_audio_mode(cid):
                cycle_audio_format(cid)
                label = get_audio_format_label(cid)
            else:
                cycle_video_format(cid)
                label = get_video_format_label(cid)
            toast = t(cid, 'format_set_toast', label=label)

        elif action == "sub":
            cycle_subtitle(cid)
            label = get_subtitle_label(cid)
            toast = t(cid, 'subtitle_set_toast', label=label)

        elif action == "chap":
            toggle_chapters(cid)
            label = get_chapters_label(cid)
            toast = t(cid, 'chapters_set_toast', label=label)

        elif action == "cookie":
            # Open cookie manager as a new message (can't replace inline kbd with different content)
            bot.answer_callback_query(call.id)
            bot.send_message(cid, t(cid, 'cookie_manage'),
                             reply_markup=cookie_list_markup(cid))
            return

        elif action == "gdrive":
            # Open the Drive setup / status panel as a new message
            bot.answer_callback_query(call.id)
            _handle_gdrive_settings(call, cid)
            return

        elif action == "profile":
            # Show the user's daily quota stats (helper lives in handlers.py)
            bot.answer_callback_query(call.id)
            from handlers import _send_profile_stats
            _send_profile_stats(cid)
            return

        elif action.startswith("dest|"):
            # Explicit destination pick: dest|tg / dest|gd / dest|s3 / dest|github
            from config import pending_uploads
            choice = action.split("|", 1)[1]
            if choice not in ("tg", "gd", "s3", "github"):
                bot.answer_callback_query(call.id)
                return

            # Case A: a file is pending — upload it to the chosen destination NOW
            pend = pending_uploads.pop(cid, None)
            if pend:
                fp = pend['fp']
                status_msg_id = pend['status_msg_id']
                bot.answer_callback_query(call.id, f"آپلود به: {choice}")
                try:
                    bot.delete_message(cid, call.message.message_id)
                except Exception:
                    pass
                try:
                    status_msg = bot.send_message(cid, "⏳ آپلود...")
                    # route through smart_dest with explicit dest
                    from uploaders.smart_dest import smart_dest
                    smart_dest(fp, status_msg, dest=choice, folder_name="FilesFromTel",
                               task_info={'chat_id': cid, 'user_id': cid})
                except Exception as e:
                    bot.send_message(cid, f"❌ خطا: {e}")
                return

            # Case B: no pending file — just set default destination
            db.set_upload_dest(cid, choice)
            bot.answer_callback_query(call.id, f"مقصد پیش‌فرض تنظیم شد: {choice}")
            from menu import destination_pick_markup
            try:
                bot.edit_message_reply_markup(
                    cid, call.message.message_id,
                    reply_markup=destination_pick_markup(cid))
            except Exception:
                pass
            return

        else:
            bot.answer_callback_query(call.id)
            return

        # Silent in-place update
        try:
            bot.edit_message_reply_markup(cid, call.message.message_id,
                                          reply_markup=settings_inline_markup(cid))
        except Exception:
            pass
        bot.answer_callback_query(call.id, toast, show_alert=False)
        return

    # ── Legacy cfg| handler (kept for any stale inline keyboards in chat) ──────
    if data.startswith("cfg|"):
        action = data.split("|")[1]
        from menu import settings_inline_markup
        from dest_helpers import cycle_quality, toggle_audio_mode
        if action == "upload":
            if cid in config.tg_upload_mode:
                config.tg_upload_mode.discard(cid)
                config.gd_upload_mode.add(cid)
                toast = t(cid, 'dest_gdrive_toast')
            else:
                config.gd_upload_mode.discard(cid)
                config.tg_upload_mode.add(cid)
                toast = t(cid, 'dest_tg_toast')
        elif action == "quality":
            cycle_quality(cid)
            from dest_helpers import get_quality_label
            toast = get_quality_label(cid)
        elif action == "media":
            toggle_audio_mode(cid)
            from dest_helpers import get_audio_mode_label
            toast = get_audio_mode_label(cid)
        else:
            bot.answer_callback_query(call.id)
            return
        try:
            bot.edit_message_reply_markup(cid, call.message.message_id,
                                          reply_markup=settings_inline_markup(cid))
        except Exception:
            pass
        bot.answer_callback_query(call.id, toast, show_alert=False)
        return


    # ── Google Drive connect / disconnect ─────────────────────
    if data.startswith("gdrive|"):
        _handle_gdrive_callback(call, cid, data)
        return

    # ── Cancel ────────────────────────────────────────────
    if data == "cancel_task":
        # call.message.message_id is the progress message the cancel button lives on.
        # Each downloader stamps task['_msg_id'] after sending that message, so this
        # O(n) scan (n ≤ MAX_CONCURRENT_DOWNLOADS) resolves to exactly the right task.
        _target_mid = call.message.message_id
        with config.current_tasks_lock:
            my_task = next(
                (t for t in config.current_tasks.values()
                 if t.get('_msg_id') == _target_mid),
                None,
            )
        if my_task:
            my_task['_stop'].set()
            bot.answer_callback_query(call.id, t(cid, 'cancel_requested'))
        else:
            bot.answer_callback_query(call.id, t(cid, 'cancel_no_task_toast'), show_alert=True)
        return

    if data == "cancel_upload":
        stop_event.set()
        if config.rclone_process:
            try:
                config.rclone_process.terminate()
            except Exception:
                pass
        bot.answer_callback_query(call.id, t(cid, 'upload_cancelled_toast'))
        return

    # ── Queue management ──────────────────────────────────────
    if data.startswith("qrm|"):
        from downloader_queue import remove_from_queue
        idx = int(data.split('|')[1])
        removed = remove_from_queue(idx)
        bot.answer_callback_query(
            call.id,
            t(cid, 'queue_removed_toast') if removed else t(cid, 'queue_not_found_toast'))
        _refresh_queue_msg(cid, call.message.message_id)
        return

    if data == "qclear":
        from downloader_queue import clear_queue
        clear_queue()
        bot.answer_callback_query(call.id, t(cid, 'queue_cleared_toast'))
        _refresh_queue_msg(cid, call.message.message_id)
        return

    if data == "qrefresh":
        bot.answer_callback_query(call.id, t(cid, 'queue_refreshed_toast'))
        _refresh_queue_msg(cid, call.message.message_id)
        return

    # ── Torrent confirmation ──────────────────────────────────
    if data.startswith("trc|"):
        _, answer, mid = data.split('|')
        with cache_lock:
            task = url_cache.get(('torrent_confirm', int(mid)))
        if answer == 'no' or not task:
            bot.answer_callback_query(call.id, t(cid, 'torrent_cancelled'))
            try:
                bot.edit_message_text(t(cid, 'torrent_cancel_msg'), cid, call.message.message_id)
            except Exception:
                pass
            return
        bot.answer_callback_query(call.id)
        _do_torrent_download(task, call.message)
        return

    # ── Social media with auto destination ───────────────────
    if data.startswith("sca|"):
        _, kind, fid, mid_s = data.split('|', 3)
        mid = int(mid_s)
        with cache_lock:
            url = url_cache.get((cid, mid))
        if not url:
            bot.answer_callback_query(call.id, t(cid, 'link_expired_toast'), show_alert=True)
            return
        dest = get_dest(cid) or 'tg'
        fmt  = "bestaudio/best" if kind == 'a' else "bestvideo+bestaudio/best"
        from dest_helpers import (get_audio_format, get_audio_quality,
                                  get_video_format, get_subtitle, get_chapters)
        enqueue({
            'type': 'social', 'chat_id': cid, 'url': url, 'dest': dest, 'format': fmt,
            'audio_only':    kind == 'a',
            'audio_format':  get_audio_format(cid),
            'audio_quality': get_audio_quality(cid),
            'video_format':  get_video_format(cid),
            'subtitle':      get_subtitle(cid),
            'chapters':      get_chapters(cid),
        })
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                t(cid, 'social_added_to_queue', dest_icon='📱' if dest == 'tg' else '☁️'),
                cid, call.message.message_id)
        except Exception:
            pass
        return

    # ── Playlist quality menu ─────────────────────────────────
    if data.startswith("plmenu|"):
        _, mid_s, audio_s = data.split('|')
        mid   = int(mid_s)
        audio = audio_s == '1'
        with cache_lock:
            url = url_cache.get((cid, mid))
        if not url:
            bot.answer_callback_query(call.id, t(cid, 'link_expired_toast'), show_alert=True)
            return
        if not audio:
            mk = types.InlineKeyboardMarkup(row_width=3)
            mk.add(
                types.InlineKeyboardButton("1080p",     callback_data=f"plq|1080|{mid}|0"),
                types.InlineKeyboardButton("720p",      callback_data=f"plq|720|{mid}|0"),
                types.InlineKeyboardButton("480p",      callback_data=f"plq|480|{mid}|0"),
                types.InlineKeyboardButton(t(cid, 'best_quality'), callback_data=f"plq|best|{mid}|0"),
            )
            try:
                bot.edit_message_text(t(cid, 'playlist_quality'), cid, call.message.message_id, reply_markup=mk)
            except Exception:
                pass
        else:
            _show_playlist_count_menu(cid, call.message.message_id, mid, audio=True, quality='audio')
        bot.answer_callback_query(call.id)
        return

    if data.startswith("plq|"):
        _, quality, mid_s, audio_s = data.split('|')
        mid = int(mid_s)
        _show_playlist_count_menu(cid, call.message.message_id, mid,
                                  audio=audio_s == '1', quality=quality)
        bot.answer_callback_query(call.id)
        return

    if data.startswith("plcount|"):
        parts   = data.split('|')
        end_idx = int(parts[1])
        mid     = int(parts[2])
        audio   = parts[3] == '1'
        quality = parts[4] if len(parts) > 4 else 'best'
        with cache_lock:
            url = url_cache.get((cid, mid))
        if not url:
            bot.answer_callback_query(call.id, t(cid, 'link_expired_toast'), show_alert=True)
            return
        _enqueue_playlist(call, cid, url, mid, end_idx, audio, quality)
        return

    if data.startswith("pld|"):
        parts = data.split('|')
        end_s, dest, mid_s, audio_s = parts[1], parts[2], parts[3], parts[4]
        quality = parts[5] if len(parts) > 5 else 'best'
        mid     = int(mid_s)
        with cache_lock:
            url = url_cache.get((cid, mid))
        if not url:
            bot.answer_callback_query(call.id, t(cid, 'link_expired_toast'), show_alert=True)
            return
        audio   = audio_s == '1'
        end_idx = int(end_s)
        fmt     = PL_FMT_MAP.get(quality, "bestvideo+bestaudio/best")
        if audio:
            fmt = "bestaudio/best"
        enqueue({
            'type': 'youtube_playlist', 'url': url, 'chat_id': cid,
            'end': end_idx if end_idx < 9999 else 99999,
            'audio_only': audio, 'format': fmt, 'dest': dest,
        })
        bot.answer_callback_query(call.id)
        count_str = end_s if end_idx < 9999 else t(cid, 'playlist_all_btn')
        try:
            bot.edit_message_text(
                t(cid, 'playlist_queued_cb',
                  count=count_str,
                  dest_icon='📱' if dest == 'tg' else '☁️'),
                cid, call.message.message_id)
        except Exception:
            pass
        return

    # ── SoundCloud playlist callbacks ────────────────────────────
    if data.startswith("scpl_info|"):
        _handle_scpl_info(call, cid, data)
        return

    if data.startswith("scpl_count|"):
        _handle_scpl_count(call, cid, data)
        return

    if data.startswith("scpl_custom|"):
        _handle_scpl_custom(call, cid, data)
        return

    if data.startswith("scpl_dest|"):
        _handle_scpl_dest(call, cid, data)
        return

    # ── Cookie management ─────────────────────────────────────
    if data.startswith("ck|"):
        _handle_cookie_callback(call, cid, data)
        return

    # ── Torrent destination ───────────────────────────────────
    if data.startswith("tr|"):
        _, dest, mid = data.split('|', 2)
        with cache_lock:
            url = url_cache.get((cid, int(mid)))
        if not url:
            bot.answer_callback_query(call.id, t(cid, 'link_expired_toast'), show_alert=True)
            return
        enqueue({'type': 'torrent', 'url': url, 'chat_id': cid,
                 'dest': dest, 'msg_id': int(mid)})
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                t(cid, 'torrent_queued_cb', dest_icon='📱' if dest == 'tg' else '☁️'),
                cid, call.message.message_id)
        except Exception:
            pass
        return

    # ── Direct link destination ───────────────────────────────
    if data.startswith("dl|"):
        _, dest, mid = data.split('|', 2)
        with cache_lock:
            url = url_cache.get((cid, int(mid)))
        if not url:
            bot.answer_callback_query(call.id, t(cid, 'link_expired_toast'), show_alert=True)
            return
        enqueue({'type': 'direct', 'url': url, 'chat_id': cid, 'dest': dest})
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                t(cid, 'direct_queued_cb', dest_icon='📱' if dest == 'tg' else '☁️'),
                cid, call.message.message_id)
        except Exception:
            pass
        return

    # ── Social media quality (with destination prompt) ────────
    if data.startswith("scq|"):
        _, kind, fid, mid_s = data.split('|', 3)
        mid = int(mid_s)
        with cache_lock:
            url = url_cache.get((cid, mid))
        if not url:
            bot.answer_callback_query(call.id, t(cid, 'link_expired_toast'), show_alert=True)
            return
        from menu import dest_pick_markup
        dest_mk = dest_pick_markup(cid, prefix=f"scd|{kind}|{fid}|{mid}", back=f"scd|{kind}|{fid}|{mid}|back")
        try:
            bot.edit_message_text(t(cid, 'select_dest'), cid, call.message.message_id,
                                  reply_markup=dest_mk)
        except Exception:
            pass
        bot.answer_callback_query(call.id)
        return

    if data.startswith("scd|"):
        # Format: scd|kind|fid|mid|dest
        parts = data.split('|', 4)
        if len(parts) < 5:
            bot.answer_callback_query(call.id, t(cid, 'invalid_option_toast'), show_alert=True)
            return
        _, kind, fid, mid_s, dest = parts
        mid = int(mid_s)
        with cache_lock:
            url = url_cache.get((cid, mid))
        if not url:
            bot.answer_callback_query(call.id, t(cid, 'link_expired_toast'), show_alert=True)
            return
        # If fid contains '+' or '/' it is a full fmt string; otherwise it is a yt-dlp format_id
        if '+' in fid or '/' in fid:
            fmt = fid
        else:
            fmt = "bestaudio/best" if kind == 'a' else "bestvideo+bestaudio/best"
        from dest_helpers import (get_audio_format, get_audio_quality,
                                  get_video_format, get_subtitle, get_chapters)
        task = {
            'type': 'social', 'chat_id': cid, 'url': url, 'dest': dest, 'format': fmt,
            'audio_only':    kind == 'a',
            'audio_format':  get_audio_format(cid),
            'audio_quality': get_audio_quality(cid),
            'video_format':  get_video_format(cid),
            'subtitle':      get_subtitle(cid),
            'chapters':      get_chapters(cid),
        }
        enqueue(task)
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(t(cid, 'social_added_cb'), cid, call.message.message_id)
        except Exception:
            pass
        return

    # ── YouTube quality ───────────────────────────────────────
    if data.startswith("yt|"):
        _handle_yt_quality(call, cid, data)
        return

    # Generic back button for the per-source destination pickers
    # (formats: ytd|<q>|<mid>|back, tr|<mid>|back, dl|<mid>|back, scd|<k>|<f>|<mid>|back)
    if data.endswith("|back"):
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(t(cid, 'select_dest_cancelled'), cid, call.message.message_id,
                                  reply_markup=None)
        except Exception:
            pass
        return

    if data.startswith("ytd|"):
        _handle_yt_dest(call, cid, data)
        return


# =============================================================
# Destination picker: dest|tg / dest|gd / dest|s3 / dest|github
# =============================================================
def _handle_dest_pick(call, cid, data):
    import db as _db
    from config import pending_uploads
    choice = data.split("|", 1)[1]
    if choice not in ("tg", "gd", "s3", "github"):
        bot.answer_callback_query(call.id)
        return

    # Case A: a file is pending — upload it to the chosen destination NOW
    pend = pending_uploads.pop(cid, None)
    if pend:
        fp = pend['fp']
        bot.answer_callback_query(call.id, f"آپلود به: {choice}")
        try:
            bot.delete_message(cid, call.message.message_id)
        except Exception:
            pass
        try:
            status_msg = bot.send_message(cid, "⏳ آپلود...")
            from uploaders.smart_dest import smart_dest
            smart_dest(fp, status_msg, dest=choice, folder_name="FilesFromTel",
                       task_info={'chat_id': cid, 'user_id': cid})
        except Exception as e:
            bot.send_message(cid, f"❌ خطا: {e}")
        return

    # Case B: no pending file — set default destination
    _db.set_upload_dest(cid, choice)
    bot.answer_callback_query(call.id, f"مقصد پیش‌فرض تنظیم شد: {choice}")
    from menu import destination_pick_markup
    try:
        bot.edit_message_reply_markup(
            cid, call.message.message_id,
            reply_markup=destination_pick_markup(cid))
    except Exception:
        pass


# =============================================================
# Helper: refresh queue message
# =============================================================
def _refresh_queue_msg(cid, mid):
    from downloader_queue import get_queue_items
    from telebot import types
    from utils import get_free_space
    q_items = get_queue_items()
    with config.current_tasks_lock:
        active_tasks = list(config.current_tasks.values())
    unknown = t(cid, 'queue_unknown')

    lines = []
    if active_tasks:
        for act in active_tasks:
            a_title = act.get('title') or act.get('url', unknown)
            lines.append(t(cid, 'queue_running', type=act['type'], title=a_title))
    else:
        lines.append(t(cid, 'queue_nothing_running'))

    if not q_items:
        lines.append(t(cid, 'queue_empty'))
        try:
            bot.edit_message_text("\n".join(lines) + f"\n\n💾 {get_free_space()}", cid, mid)
        except Exception:
            logger.exception("Could not refresh queue message for chat %s message %s", cid, mid)
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

        try:
            bot.edit_message_text(
                "\n".join(lines) + f"\n\n💾 {get_free_space()}", cid, mid, reply_markup=markup)
        except Exception:
            logger.exception("Could not refresh queue message for chat %s message %s", cid, mid)


# =============================================================
# Helper: enqueue playlist
# =============================================================
def _enqueue_playlist(call, cid, url, mid, end_idx, audio, quality):
    if not should_ask_dest(cid):
        dest = get_dest(cid)
        fmt  = PL_FMT_MAP.get(quality, "bestvideo+bestaudio/best")
        if audio:
            fmt = "bestaudio/best"
        enqueue({
            'type': 'youtube_playlist', 'url': url, 'chat_id': cid,
            'end': end_idx if end_idx < 9999 else 99999,
            'audio_only': audio, 'format': fmt, 'dest': dest,
        })
        bot.answer_callback_query(call.id)
        count_str = str(end_idx) if end_idx < 9999 else t(cid, 'playlist_all_btn')
        try:
            bot.edit_message_text(
                t(cid, 'playlist_queued_cb',
                  count=count_str,
                  dest_icon='📱' if dest == 'tg' else '☁️'),
                cid, call.message.message_id)
        except Exception:
            pass
    else:
        dest_mk = types.InlineKeyboardMarkup()
        dest_mk.row(
            types.InlineKeyboardButton(t(cid, 'btn_tg'),
                callback_data=f"pld|{end_idx}|tg|{mid}|{'1' if audio else '0'}|{quality}"),
            types.InlineKeyboardButton(t(cid, 'btn_gd'),
                callback_data=f"pld|{end_idx}|gd|{mid}|{'1' if audio else '0'}|{quality}"),
        )
        count_str = str(end_idx) if end_idx < 9999 else t(cid, 'playlist_all_btn')
        if audio:
            media_label = t(cid, 'playlist_media_audio')
        else:
            media_label = t(cid, 'playlist_media_video', quality=quality)
        try:
            bot.edit_message_text(
                t(cid, 'playlist_dest_msg', media=media_label, count=count_str),
                cid, call.message.message_id, reply_markup=dest_mk)
        except Exception:
            pass
        bot.answer_callback_query(call.id)


# =============================================================
# Helper: YouTube quality callback
# =============================================================
def _handle_yt_quality(call, cid, data):
    import yt_dlp
    parts   = data.split('|')
    quality = parts[1]
    msg_id  = int(parts[2])
    with cache_lock:
        url = url_cache.get((cid, msg_id))
    if not url:
        bot.answer_callback_query(call.id, t(cid, 'link_expired_toast'), show_alert=True)
        return
    if quality in ('pl', 'pl_audio'):
        _show_playlist_menu(cid, call.message.message_id, msg_id, audio=(quality == 'pl_audio'))
        bot.answer_callback_query(call.id)
        return
    if not should_ask_dest(cid):
        dest = get_dest(cid)
        if quality not in YT_FMT_MAP:
            bot.answer_callback_query(call.id, t(cid, 'invalid_option_toast'), show_alert=True)
            return
        fmt, audio_only = YT_FMT_MAP[quality]
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
                info  = ydl.extract_info(url, download=False)
                title = info.get('title', 'video')
        except Exception:
            title = 'video'
        from dest_helpers import (get_audio_format, get_audio_quality,
                                  get_video_format, get_subtitle, get_chapters)
        enqueue({
            'type': 'youtube', 'url': url, 'format': fmt,
            'chat_id': cid, 'audio_only': audio_only,
            'dest': dest, 'title': title,
            'audio_format':  get_audio_format(cid),
            'audio_quality': get_audio_quality(cid),
            'video_format':  get_video_format(cid),
            'subtitle':      get_subtitle(cid),
            'chapters':      get_chapters(cid),
        })
        pos = len(config.pending_queue)
        try:
            bot.edit_message_text(
                t(cid, 'yt_queued_cb',
                  quality=YT_LABELS.get(quality, quality),
                  dest_icon='📱' if dest == 'tg' else '☁️',
                  pos=pos),
                cid, call.message.message_id)
        except Exception:
            pass
        bot.answer_callback_query(call.id)
    else:
        from menu import dest_pick_markup
        dest_mk = dest_pick_markup(cid, prefix=f"ytd|{quality}|{msg_id}", back=f"ytd|{quality}|{msg_id}|back")
        try:
            bot.edit_message_text(
                t(cid, 'yt_quality_dest_only', quality=YT_LABELS.get(quality, quality)),
                cid, call.message.message_id, reply_markup=dest_mk)
        except Exception:
            pass
        bot.answer_callback_query(call.id)


def _handle_yt_dest(call, cid, data):
    import yt_dlp
    # data format: ytd|{quality}|{mid}|{dest}
    parts = data.split('|', 3)
    if len(parts) < 4:
        bot.answer_callback_query(call.id, t(cid, 'invalid_option_toast'), show_alert=True)
        return
    _, quality, mid, dest = parts
    msg_id = int(mid)
    with cache_lock:
        url = url_cache.get((cid, msg_id))
    if not url:
        bot.answer_callback_query(call.id, t(cid, 'link_expired_toast'), show_alert=True)
        return
    if quality not in YT_FMT_MAP:
        bot.answer_callback_query(call.id, t(cid, 'invalid_option_toast'), show_alert=True)
        return
    fmt, audio_only = YT_FMT_MAP[quality]
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
            info  = ydl.extract_info(url, download=False)
            title = info.get('title', 'video')
    except Exception:
        title = 'video'
    from dest_helpers import (get_audio_format, get_audio_quality,
                              get_video_format, get_subtitle, get_chapters)
    enqueue({
        'type': 'youtube', 'url': url, 'format': fmt,
        'chat_id': cid, 'audio_only': audio_only,
        'dest': dest, 'title': title,
        'audio_format':  get_audio_format(cid),
        'audio_quality': get_audio_quality(cid),
        'video_format':  get_video_format(cid),
        'subtitle':      get_subtitle(cid),
        'chapters':      get_chapters(cid),
    })
    pos = len(config.pending_queue)
    try:
        bot.edit_message_text(
            t(cid, 'yt_queued_cb',
              quality=YT_LABELS.get(quality, quality),
              dest_icon='📱' if dest == 'tg' else '☁️',
              pos=pos),
            cid, call.message.message_id)
    except Exception:
        pass
    bot.answer_callback_query(call.id)


# =============================================================
# SoundCloud playlist callback handlers
# =============================================================
def _handle_scpl_info(call, cid, data):
    """User tapped '🎵 Download Audio' — show count selection menu."""
    _, mid_s = data.split('|', 1)
    mid = int(mid_s)
    with cache_lock:
        url = url_cache.get(mid)
    if not url:
        bot.answer_callback_query(call.id, t(cid, 'link_expired_toast'), show_alert=True)
        return

    # Re-fetch the title for display in the count menu
    title = 'SoundCloud Playlist'
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({'extract_flat': True, 'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', title)
    except Exception:
        pass

    mk = types.InlineKeyboardMarkup(row_width=3)
    mk.add(
        types.InlineKeyboardButton(t(cid, 'playlist_all_btn'),
            callback_data=f"scpl_count|{mid}|all"),
        types.InlineKeyboardButton("5",
            callback_data=f"scpl_count|{mid}|5"),
        types.InlineKeyboardButton("10",
            callback_data=f"scpl_count|{mid}|10"),
        types.InlineKeyboardButton("20",
            callback_data=f"scpl_count|{mid}|20"),
    )
    mk.add(types.InlineKeyboardButton(
        t(cid, 'playlist_custom_btn'),
        callback_data=f"scpl_custom|{mid}"))

    try:
        bot.edit_message_text(
            t(cid, 'sc_playlist_count_ask', title=title),
            cid, call.message.message_id, reply_markup=mk)
    except Exception:
        pass
    bot.answer_callback_query(call.id)


def _handle_scpl_custom(call, cid, data):
    """Ask user to type a custom number of tracks."""
    _, mid_s = data.split('|', 1)
    mid = int(mid_s)
    user_state[cid] = f'await_scpl_count|{mid}'
    bot.answer_callback_query(call.id)
    bot.send_message(cid, t(cid, 'sc_playlist_custom_ask'))


def _handle_scpl_count(call, cid, data):
    """User selected track count — show destination selection."""
    parts = data.split('|')
    mid   = int(parts[1])
    count = parts[2]  # 'all' or a number string

    with cache_lock:
        url = url_cache.get(mid)
    if not url:
        bot.answer_callback_query(call.id, t(cid, 'link_expired_toast'), show_alert=True)
        return

    from dest_helpers import should_ask_dest, get_dest
    if not should_ask_dest(cid):
        dest = get_dest(cid)
        enqueue({
            'type': 'soundcloud_playlist',
            'chat_id': cid,
            'url': url,
            'count': int(count) if count != 'all' else 'all',
            'dest': dest,
            'audio_only': True,
            'format': 'bestaudio/best',
        })
        bot.answer_callback_query(call.id)
        count_display = t(cid, 'playlist_all_btn') if count == 'all' else count
        try:
            bot.edit_message_text(
                t(cid, 'sc_playlist_queued',
                  count=count_display,
                  dest_icon='📱' if dest == 'tg' else '☁️'),
                cid, call.message.message_id)
        except Exception:
            pass
    else:
        dest_mk = types.InlineKeyboardMarkup()
        dest_mk.row(
            types.InlineKeyboardButton(t(cid, 'btn_tg'),
                callback_data=f"scpl_dest|{mid}|{count}|tg"),
            types.InlineKeyboardButton(t(cid, 'btn_gd'),
                callback_data=f"scpl_dest|{mid}|{count}|gd"),
        )
        count_display = t(cid, 'playlist_all_btn') if count == 'all' else count
        try:
            bot.edit_message_text(
                t(cid, 'sc_playlist_dest_ask', count=count_display),
                cid, call.message.message_id, reply_markup=dest_mk)
        except Exception:
            pass
        bot.answer_callback_query(call.id)


def _handle_scpl_dest(call, cid, data):
    """User selected destination — enqueue the SoundCloud playlist task."""
    parts = data.split('|')
    mid   = int(parts[1])
    count = parts[2]  # 'all' or a number string
    dest  = parts[3]

    with cache_lock:
        url = url_cache.get(mid)
    if not url:
        bot.answer_callback_query(call.id, t(cid, 'link_expired_toast'), show_alert=True)
        return

    enqueue({
        'type': 'soundcloud_playlist',
        'chat_id': cid,
        'url': url,
        'count': int(count) if count != 'all' else 'all',
        'dest': dest,
        'audio_only': True,
        'format': 'bestaudio/best',
    })
    bot.answer_callback_query(call.id)
    count_display = t(cid, 'playlist_all_btn') if count == 'all' else count
    try:
        bot.edit_message_text(
            t(cid, 'sc_playlist_queued',
              count=count_display,
              dest_icon='📱' if dest == 'tg' else '☁️'),
            cid, call.message.message_id)
    except Exception:
        pass


# =============================================================
# Admin user management panel
# =============================================================
def _aum_make_ctx(cid: int, page: int, query: str | None) -> str:
    token = f"{int(time.time() * 1000) % 10_000_000_000}"
    with cache_lock:
        url_cache[("aum_ctx", cid, token)] = {
            "page": int(page),
            "query": query,
        }
    return token


def _aum_get_ctx(cid: int, token: str) -> dict:
    with cache_lock:
        ctx = url_cache.get(("aum_ctx", cid, token))
    if isinstance(ctx, dict):
        return ctx
    return {"page": 1, "query": None}


def _chat_display_name(chat_obj) -> str:
    first = getattr(chat_obj, "first_name", "") or ""
    last = getattr(chat_obj, "last_name", "") or ""
    name = (first + " " + last).strip()
    if name:
        return name
    return getattr(chat_obj, "title", "") or ""


def _backfill_identity_if_missing(user_row) -> None:
    """
    Best-effort identity backfill for legacy rows that predate username/display_name fields.
    This is intentionally silent on failure.
    """
    if not user_row:
        return
    if user_row["username"] and user_row["display_name"]:
        return
    uid = user_row["user_id"]
    try:
        chat = bot.get_chat(uid)
        db.touch_user_identity(
            uid,
            getattr(chat, "username", None),
            _chat_display_name(chat),
        )
    except Exception:
        pass


def _fmt_quota_gb(bytes_value: int | None) -> str:
    if bytes_value is None:
        return "-"
    return f"{(int(bytes_value) / (1024 ** 3)):.2f}"


def render_admin_users_list(chat_id: int, page: int = 1, query: str | None = None, message_id: int | None = None) -> None:
    per_page = 10
    total = db.count_all_signed_users(query=query)
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, pages))
    rows = db.list_all_signed_users(page=page, per_page=per_page, query=query)
    token = _aum_make_ctx(chat_id, page, query)

    if query:
        title = t(chat_id, 'admin_users_title_search', query=query, page=page, pages=pages, total=total)
    else:
        title = t(chat_id, 'admin_users_title', page=page, pages=pages, total=total)

    lines = [title, ""]
    if not rows:
        lines.append(t(chat_id, 'admin_users_empty'))
    else:
        for row in rows:
            _backfill_identity_if_missing(row)
            fresh_row = db.get_user(row["user_id"]) or row
            uid = fresh_row["user_id"]
            if uid == ADMIN_ID and not fresh_row["is_approved"]:
                db.approve_user(uid)
                fresh_row = db.get_user(uid) or fresh_row
            if uid == ADMIN_ID:
                approved = t(chat_id, 'admin_user_status_admin')
            else:
                approved = (
                    t(chat_id, 'admin_user_status_enabled')
                    if fresh_row["is_approved"] else
                    t(chat_id, 'admin_user_status_disabled')
                )
            uname = f"@{fresh_row['username']}" if fresh_row["username"] else "-"
            dname = fresh_row["display_name"] or "-"
            lines.append(
                t(
                    chat_id,
                    'admin_users_row',
                    user_id=uid,
                    status=approved,
                    username=uname,
                    display_name=dname,
                )
            )

    markup = types.InlineKeyboardMarkup(row_width=1)
    for row in rows:
        uid = row["user_id"]
        markup.add(
            types.InlineKeyboardButton(
                t(chat_id, 'admin_users_open_btn', user_id=uid),
                callback_data=f"aum|u|{uid}|{token}",
            )
        )

    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton(t(chat_id, 'admin_users_prev_btn'), callback_data=f"aum|p|{page-1}|{token}"))
    if page < pages:
        nav.append(types.InlineKeyboardButton(t(chat_id, 'admin_users_next_btn'), callback_data=f"aum|p|{page+1}|{token}"))
    if nav:
        markup.row(*nav)

    markup.row(
        types.InlineKeyboardButton(t(chat_id, 'admin_users_search_btn'), callback_data=f"aum|s|{token}"),
        types.InlineKeyboardButton(t(chat_id, 'admin_users_clear_search_btn'), callback_data="aum|c"),
    )

    text = "\n".join(lines)
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)


def render_admin_user_detail(
    chat_id: int,
    user_id: int,
    ctx_token: str,
    message_id: int | None = None,
    confirm_disable: bool = False,
) -> None:
    row = db.get_user(user_id)
    if user_id == ADMIN_ID and row is not None and not row["is_approved"]:
        db.approve_user(user_id)
        row = db.get_user(user_id) or row
    _backfill_identity_if_missing(row)
    row = db.get_user(user_id) or row
    if row is None:
        bot.send_message(chat_id, t(chat_id, 'admin_user_not_found', user_id=user_id))
        return
    stats = db.get_user_download_stats(user_id)
    approved = t(chat_id, 'admin_user_status_enabled') if row["is_approved"] else t(chat_id, 'admin_user_status_disabled')
    uname = f"@{row['username']}" if row["username"] else "-"
    dname = row["display_name"] or "-"
    files_today = int(row["files_downloaded"] or 0)
    bytes_today = int(row["bytes_downloaded"] or 0)
    quota_bytes = db.get_effective_quota_bytes(user_id)
    gb_today = bytes_today / (1024 ** 3)
    quota_gb = quota_bytes / (1024 ** 3)

    monthly_files_used = int(row["monthly_files_downloaded"] or 0)
    monthly_bytes_used = int(row["monthly_bytes_downloaded"] or 0)
    monthly_quota_bytes = db.get_effective_monthly_quota_bytes(user_id)
    monthly_quota_files = db.get_effective_monthly_quota_files(user_id)
    monthly_gb_used = monthly_bytes_used / (1024 ** 3)
    monthly_quota_gb = monthly_quota_bytes / (1024 ** 3)

    text = t(
        chat_id,
        'admin_user_detail',
        user_id=user_id,
        status=approved,
        username=uname,
        display_name=dname,
        files_today=files_today,
        used_gb=gb_today,
        quota_gb=quota_gb,
        monthly_files_used=monthly_files_used,
        monthly_quota_files=monthly_quota_files,
        monthly_gb_used=monthly_gb_used,
        monthly_quota_gb=monthly_quota_gb,
        files_today_stats=stats["files_today"],
        files_week=stats["files_week"],
        files_month=stats["files_month"],
        files_all=stats["files_all"],
        bytes_today_stats_gb=stats["bytes_today"] / (1024 ** 3),
        bytes_week_gb=stats["bytes_week"] / (1024 ** 3),
        bytes_month_gb=stats["bytes_month"] / (1024 ** 3),
        bytes_all_gb=stats["bytes_all"] / (1024 ** 3),
    )
    if confirm_disable:
        text += "\n\n" + t(chat_id, 'admin_user_disable_confirm')

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton(t(chat_id, 'admin_user_usage_minus_btn'), callback_data=f"aum|us|{user_id}|-1|{ctx_token}"),
        types.InlineKeyboardButton(t(chat_id, 'admin_user_usage_plus_btn'), callback_data=f"aum|us|{user_id}|1|{ctx_token}"),
    )
    markup.row(
        types.InlineKeyboardButton(t(chat_id, 'admin_user_quota_minus_btn'), callback_data=f"aum|qb|{user_id}|-1|{ctx_token}"),
        types.InlineKeyboardButton(t(chat_id, 'admin_user_quota_plus_btn'), callback_data=f"aum|qb|{user_id}|1|{ctx_token}"),
    )
    markup.row(
        types.InlineKeyboardButton(t(chat_id, 'admin_user_monthly_quota_minus_btn'), callback_data=f"aum|qm|{user_id}|-1|{ctx_token}"),
        types.InlineKeyboardButton(t(chat_id, 'admin_user_monthly_quota_plus_btn'), callback_data=f"aum|qm|{user_id}|1|{ctx_token}"),
    )
    if confirm_disable:
        markup.row(
            types.InlineKeyboardButton(t(chat_id, 'admin_user_disable_yes_btn'), callback_data=f"aum|dc|{user_id}|{ctx_token}"),
            types.InlineKeyboardButton(t(chat_id, 'admin_user_disable_no_btn'), callback_data=f"aum|u|{user_id}|{ctx_token}"),
        )
    else:
        markup.row(
            types.InlineKeyboardButton(t(chat_id, 'admin_user_enable_btn'), callback_data=f"aum|en|{user_id}|{ctx_token}"),
            types.InlineKeyboardButton(t(chat_id, 'admin_user_disable_btn'), callback_data=f"aum|da|{user_id}|{ctx_token}"),
        )
    markup.add(types.InlineKeyboardButton(t(chat_id, 'admin_user_back_btn'), callback_data=f"aum|b|{ctx_token}"))

    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)


def _handle_admin_user_panel(call, cid: int, data: str) -> None:
    if cid != ADMIN_ID:
        bot.answer_callback_query(call.id, t(cid, 'admin_only'), show_alert=True)
        return
    parts = data.split('|')
    if len(parts) < 2:
        bot.answer_callback_query(call.id)
        return
    action = parts[1]

    try:
        if action == "p" and len(parts) >= 4:
            page = int(parts[2])
            token = parts[3]
            ctx = _aum_get_ctx(cid, token)
            render_admin_users_list(
                chat_id=cid,
                page=page,
                query=ctx.get("query"),
                message_id=call.message.message_id,
            )
            bot.answer_callback_query(call.id)
            return

        if action == "b" and len(parts) >= 3:
            token = parts[2]
            ctx = _aum_get_ctx(cid, token)
            render_admin_users_list(
                chat_id=cid,
                page=int(ctx.get("page") or 1),
                query=ctx.get("query"),
                message_id=call.message.message_id,
            )
            bot.answer_callback_query(call.id)
            return

        if action == "u" and len(parts) >= 4:
            user_id = int(parts[2])
            token = parts[3]
            render_admin_user_detail(
                chat_id=cid,
                user_id=user_id,
                ctx_token=token,
                message_id=call.message.message_id,
            )
            bot.answer_callback_query(call.id)
            return

        if action == "us" and len(parts) >= 5:
            user_id = int(parts[2])
            delta = int(parts[3])
            token = parts[4]
            if user_id == ADMIN_ID:
                bot.answer_callback_query(call.id, t(cid, 'admin_user_self_blocked'), show_alert=True)
                return
            db.adjust_user_usage_count(user_id, delta)
            render_admin_user_detail(
                chat_id=cid,
                user_id=user_id,
                ctx_token=token,
                message_id=call.message.message_id,
            )
            bot.answer_callback_query(call.id, t(cid, 'admin_user_usage_updated_toast'))
            return

        if action == "qb" and len(parts) >= 5:
            user_id = int(parts[2])
            step = int(parts[3])
            token = parts[4]
            if user_id == ADMIN_ID:
                bot.answer_callback_query(call.id, t(cid, 'admin_user_self_blocked'), show_alert=True)
                return
            delta_bytes = step * int(0.5 * (1024 ** 3))
            db.adjust_user_quota_bytes(user_id, delta_bytes)
            render_admin_user_detail(
                chat_id=cid,
                user_id=user_id,
                ctx_token=token,
                message_id=call.message.message_id,
            )
            bot.answer_callback_query(call.id, t(cid, 'admin_user_quota_updated_toast'))
            return

        if action == "qm" and len(parts) >= 5:
            user_id = int(parts[2])
            step = int(parts[3])
            token = parts[4]
            if user_id == ADMIN_ID:
                bot.answer_callback_query(call.id, t(cid, 'admin_user_self_blocked'), show_alert=True)
                return
            delta_bytes = step * int(1 * (1024 ** 3))  # 1 GB per click for monthly
            db.adjust_user_monthly_quota_bytes(user_id, delta_bytes)
            render_admin_user_detail(
                chat_id=cid,
                user_id=user_id,
                ctx_token=token,
                message_id=call.message.message_id,
            )
            bot.answer_callback_query(call.id, t(cid, 'admin_user_monthly_quota_updated_toast'))
            return

        if action == "en" and len(parts) >= 4:
            user_id = int(parts[2])
            token = parts[3]
            if user_id == ADMIN_ID:
                bot.answer_callback_query(call.id, t(cid, 'admin_user_self_blocked'), show_alert=True)
                return
            db.approve_user(user_id)
            render_admin_user_detail(
                chat_id=cid,
                user_id=user_id,
                ctx_token=token,
                message_id=call.message.message_id,
            )
            bot.answer_callback_query(call.id, t(cid, 'admin_user_enabled_toast'))
            return

        if action == "da" and len(parts) >= 4:
            user_id = int(parts[2])
            token = parts[3]
            render_admin_user_detail(
                chat_id=cid,
                user_id=user_id,
                ctx_token=token,
                message_id=call.message.message_id,
                confirm_disable=True,
            )
            bot.answer_callback_query(call.id)
            return

        if action == "dc" and len(parts) >= 4:
            user_id = int(parts[2])
            token = parts[3]
            if user_id == ADMIN_ID:
                bot.answer_callback_query(call.id, t(cid, 'admin_user_self_blocked'), show_alert=True)
                return
            from handlers import disable_user_and_stop_tasks
            disable_user_and_stop_tasks(user_id)
            render_admin_user_detail(
                chat_id=cid,
                user_id=user_id,
                ctx_token=token,
                message_id=call.message.message_id,
            )
            bot.answer_callback_query(call.id, t(cid, 'admin_user_disabled_toast'))
            return

        if action == "s":
            user_state[cid] = 'await_admin_user_search'
            bot.answer_callback_query(call.id)
            bot.send_message(cid, t(cid, 'admin_users_search_prompt'))
            return

        if action == "c":
            render_admin_users_list(
                chat_id=cid,
                page=1,
                query=None,
                message_id=call.message.message_id,
            )
            bot.answer_callback_query(call.id, t(cid, 'admin_users_search_cleared_toast'))
            return

    except Exception:
        bot.answer_callback_query(call.id, t(cid, 'admin_users_bad_action'), show_alert=True)
        return

    bot.answer_callback_query(call.id)


# =============================================================
# Helper: cookie callbacks
# =============================================================
def _handle_cookie_callback(call, cid, data):
    parts  = data.split('|')
    action = parts[1]

    if action == "none":
        bot.answer_callback_query(call.id, t(cid, 'cookie_no_cookies_toast'), show_alert=True)
    elif action == "list":
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(t(cid, 'cookie_manage'), cid, call.message.message_id,
                                  reply_markup=cookie_list_markup(cid))
        except Exception:
            pass
    elif action == "select":
        name   = parts[2]
        status = (t(cid, 'cookie_status_active')
                  if (is_cookie_enabled(name, cid) and cookie_exists(name, cid))
                  else t(cid, 'cookie_status_inactive'))
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                t(cid, 'cookie_status', name=name, status=status),
                cid, call.message.message_id,
                reply_markup=cookie_item_markup(name, cid))
        except Exception:
            pass
    elif action == "enable":
        name = parts[2]
        set_cookie_enabled(name, True, cid)
        bot.answer_callback_query(call.id, t(cid, 'cookie_enabled_toast', name=name))
        try:
            bot.edit_message_text(
                t(cid, 'cookie_enabled_msg', name=name),
                cid, call.message.message_id,
                reply_markup=cookie_item_markup(name, cid))
        except Exception:
            pass
    elif action == "disable":
        name = parts[2]
        set_cookie_enabled(name, False, cid)
        bot.answer_callback_query(call.id, t(cid, 'cookie_disabled_toast', name=name))
        try:
            bot.edit_message_text(
                t(cid, 'cookie_disabled_msg', name=name),
                cid, call.message.message_id,
                reply_markup=cookie_item_markup(name, cid))
        except Exception:
            pass
    elif action == "delete":
        name = parts[2]
        delete_cookie(name, cid)
        bot.answer_callback_query(call.id, t(cid, 'cookie_deleted_toast', name=name))
        try:
            bot.edit_message_text(t(cid, 'cookie_manage'), cid, call.message.message_id,
                                  reply_markup=cookie_list_markup(cid))
        except Exception:
            pass
    elif action == "rename":
        name = parts[2]
        user_state[cid] = f'await_cookie_rename|{name}'
        bot.answer_callback_query(call.id)
        bot.send_message(cid, t(cid, 'cookie_rename_ask', name=name))
    elif action == "add":
        user_state[cid] = 'await_cookie_file'
        bot.answer_callback_query(call.id)
        bot.send_message(cid, get_cookie_help(cid))
    elif action == "help":
        bot.answer_callback_query(call.id)
        bot.send_message(cid, get_cookie_help(cid))
    elif action == "back":
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except Exception:
            pass


# =============================================================
# Playlist — custom count
# =============================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("plcustom|"))
def playlist_custom_count(call):
    cid     = call.message.chat.id
    parts   = call.data.split('|')
    mid     = int(parts[1])
    audio   = parts[2] == '1'
    quality = parts[3] if len(parts) > 3 else 'best'
    user_state[cid] = f'await_playlist_count|{mid}|{"1" if audio else "0"}|{quality}'
    bot.answer_callback_query(call.id)
    bot.send_message(cid, t(cid, 'playlist_ask_custom'))


# =============================================================
# Google Drive multi-tenant helpers
# =============================================================
def _handle_gdrive_settings(call, cid: int) -> None:
    """
    Show either:
      • The step-by-step Colab setup instructions (if no config yet), or
      • A "connected" status panel with a Disconnect button.
    Always sent as a new message so it can't clash with the settings markup.
    For the Admin, always show "System Default (connected)" — they use the
    global rclone.conf and should never be prompted to reconnect.
    """
    from pathlib import Path
    from config import USER_CONFIGS_DIR, COLAB_URL

    # Admin uses the same per-user rclone config flow as regular users,
    # so they can connect their OWN Drive too.
    conf_path = Path(USER_CONFIGS_DIR) / f"rclone_{cid}.conf"

    if conf_path.exists():
        # ── Already connected: show status + disconnect option ────────────
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton(
            t(cid, 'btn_gdrive_disconnect'),
            callback_data="gdrive|disconnect_ask",
        ))
        bot.send_message(
            cid,
            t(cid, 'gdrive_status_connected'),
            parse_mode='HTML',
            reply_markup=mk,
        )
    else:
        # ── Not connected: send exact corrected Colab instructions ────────
        bot.send_message(
            cid,
            t(cid, 'gdrive_colab_instructions', colab_url=COLAB_URL),
            disable_web_page_preview=True,
        )


def _handle_gdrive_callback(call, cid: int, data: str) -> None:
    """
    Handle all gdrive|* callback actions:
      gdrive|disconnect_ask  → show confirmation dialog
      gdrive|disconnect_yes  → delete config, refresh settings button
      gdrive|disconnect_no   → silent dismiss
    """
    from pathlib import Path
    from config import USER_CONFIGS_DIR
    from menu import settings_inline_markup

    action = data.split('|', 1)[1]  # everything after "gdrive|"

    if action == "disconnect_ask":
        mk = types.InlineKeyboardMarkup()
        mk.row(
            types.InlineKeyboardButton(
                t(cid, 'btn_gdrive_disconnect_confirm'),
                callback_data="gdrive|disconnect_yes",
            ),
            types.InlineKeyboardButton(
                t(cid, 'btn_gdrive_disconnect_cancel'),
                callback_data="gdrive|disconnect_no",
            ),
        )
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                t(cid, 'gdrive_disconnect_confirm'),
                cid, call.message.message_id,
                parse_mode='HTML',
                reply_markup=mk,
            )
        except Exception:
            bot.send_message(
                cid,
                t(cid, 'gdrive_disconnect_confirm'),
                parse_mode='HTML',
                reply_markup=mk,
            )

    elif action == "disconnect_yes":
        conf_path = Path(USER_CONFIGS_DIR) / f"rclone_{cid}.conf"
        try:
            conf_path.unlink(missing_ok=True)
        except Exception:
            pass
        bot.answer_callback_query(call.id, t(cid, 'gdrive_disconnected_toast'))
        # Edit the confirmation message to a plain success notice
        try:
            bot.edit_message_text(
                t(cid, 'gdrive_disconnected_msg'),
                cid, call.message.message_id,
                parse_mode='HTML',
            )
        except Exception:
            pass
        # Proactively refresh any open settings panel so the button label updates
        # (best-effort; the user will see the updated label next time they open settings)

    elif action == "disconnect_no":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(cid, call.message.message_id)
        except Exception:
            pass

# (Profile stats helper lives in handlers.py to avoid circular imports;
#  callbacks.py imports it lazily inside the set|profile branch above.)
