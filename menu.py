from telebot import types
from config import tg_upload_mode, USER_CONFIGS_DIR
from cookies import list_cookies, is_cookie_enabled, cookie_exists
from dest_helpers import get_quality_label, get_audio_mode_label
from locales import t
from pathlib import Path


def _gdrive_button_label(cid) -> str:
    """Return the Drive connect/connected button label based on whether
    the user already has a personal rclone config on disk.
    Admin always shows 'System Default' (uses the global rclone.conf)."""
    from config import ADMIN_ID
    if cid == ADMIN_ID:
        return t(cid, 'btn_gdrive_connected_system')
    if cid and Path(USER_CONFIGS_DIR, f"rclone_{cid}.conf").exists():
        return t(cid, 'btn_gdrive_connected')
    return t(cid, 'btn_gdrive_connect') if cid else "☁️ اتصال گوگل درایو"


# =============================================================
# Main Reply Keyboard — only 5 buttons, settings moved to inline
# =============================================================
def main_menu_markup(cid=None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton(t(cid, 'btn_settings')    if cid else "تنظیمات ⚙️"),
        types.KeyboardButton(t(cid, 'btn_cancel')      if cid else "❌ لغو عملیات فعلی"),
        types.KeyboardButton(t(cid, 'btn_queue')       if cid else "📊 وضعیت صف"),
        types.KeyboardButton(t(cid, 'btn_profile')     if cid else "👤 پروفایل من"),
        types.KeyboardButton(t(cid, 'btn_change_lang') if cid else "تغییر زبان 🌐"),
        types.KeyboardButton(t(cid, 'btn_help')        if cid else "ℹ️ راهنما"),
    )
    return markup



# =============================================================
# Settings Inline Panel
#   Row 1: [Media mode] [Format]
#   Row 2: [Quality]    [Upload]
#   Row 3: [Subtitle]   [Chapters]
#   Row 4: [Cookie Manager — full width]
# =============================================================
def settings_inline_markup(cid=None):
    import config
    from dest_helpers import (
        get_quality_label, get_audio_mode_label,
        get_video_format_label, get_audio_format_label,
        get_audio_quality_label, get_subtitle_label,
        get_chapters_label, is_audio_mode,
    )

    # ── Section A: Download Mode (radio, 2×2) ─────────────────
    current_mode = config.user_download_mode.get(cid, 'auto') if cid else 'auto'

    def mode_label(key, locale_key):
        base = t(cid, locale_key) if cid else locale_key
        return f"✅ {base}" if current_mode == key else base

    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton(mode_label('ytdlp',   'btn_mode_ytdlp'),
                                   callback_data="set|mode|ytdlp"),
        types.InlineKeyboardButton(mode_label('torrent', 'btn_mode_torrent'),
                                   callback_data="set|mode|torrent"),
        types.InlineKeyboardButton(mode_label('direct',  'btn_mode_direct'),
                                   callback_data="set|mode|direct"),
        types.InlineKeyboardButton(mode_label('auto',    'btn_mode_auto'),
                                   callback_data="set|mode|auto"),
    )

    # ── Section B: Toggle / Cycle settings (2-column grid) ────
    audio_mode = is_audio_mode(cid) if cid else False

    media_label   = (get_audio_mode_label(cid)  if cid else "🎬 Media: Video")
    if cid:
        import db
        d = db.get_upload_dest(cid)
        if d == 'tg':
            upload_label = t(cid, 'btn_upload_tg')  # legacy value; treated as "ask"
        elif d == 'gd':
            upload_label = t(cid, 'btn_upload_gd')
        elif d == 's3':
            upload_label = '☁️ آپلود: Railway S3'
        elif d == 'github':
            upload_label = '🐙 آپلود: GitHub'
        else:
            upload_label = t(cid, 'btn_upload_ask')
    else:
        upload_label = "☁️ Upload: Drive"

    if cid:
        if audio_mode:
            quality_label = get_audio_quality_label(cid)
            format_label  = get_audio_format_label(cid)
        else:
            quality_label = get_quality_label(cid)
            format_label  = get_video_format_label(cid)
    else:
        quality_label = "🎯 Quality: Manual"
        format_label  = "📦 Format: MP4"

    subtitle_label = get_subtitle_label(cid) if cid else "💬 Subtitle: Off"
    chapters_label = get_chapters_label(cid) if cid else "📑 Chapters: Off"
    cookie_label   = t(cid, 'btn_cookie') if cid else "🍪 Cookie Manager"

    # Row 1: Media · Format
    mk.row(
        types.InlineKeyboardButton(media_label,   callback_data="set|media"),
        types.InlineKeyboardButton(format_label,  callback_data="set|fmt"),
    )
    # Row 2: Quality · Upload destination
    mk.row(
        types.InlineKeyboardButton(quality_label, callback_data="set|qual"),
        types.InlineKeyboardButton(upload_label,  callback_data="set|destmenu"),
    )
    # Row 3: Subtitle · Chapters
    mk.row(
        types.InlineKeyboardButton(subtitle_label, callback_data="set|sub"),
        types.InlineKeyboardButton(chapters_label, callback_data="set|chap"),
    )
    # Row 4: Cookie manager (full width)
    mk.add(types.InlineKeyboardButton(cookie_label, callback_data="set|cookie"))
    # Row 5: Google Drive connection (full width, status-aware)
    mk.add(types.InlineKeyboardButton(_gdrive_button_label(cid), callback_data="set|gdrive"))

    return mk


def dest_pick_markup(cid=None, prefix: str = "dest", back: str = "set|back"):
    """
    Per-download destination picker (links/youtube/torrent).
    Telegram removed — for chat files the file is already in Telegram;
    downloaded files go to a cloud destination or get asked per file.
    All callbacks become:  <prefix>|<key>   where key ∈ gd|s3|github
    """
    import db
    cur = db.get_upload_dest(cid) if cid else 'gd'
    mk = types.InlineKeyboardMarkup(row_width=2)

    def btn(key, label):
        mark = "✅ " if cur == key else ""
        return types.InlineKeyboardButton(mark + label, callback_data=f"{prefix}|{key}")

    mk.row(btn('gd', "☁️ Google Drive"), btn('s3', "🗄 Railway S3"))
    mk.add(btn('github', "🐙 GitHub"))
    mk.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data=back))
    return mk


def destination_pick_markup(cid=None):
    """Settings menu: default upload destination — Ask (per-file) + 3 cloud
    destinations. Telegram excluded: files sent in chat are already there."""
    import db
    cur = db.get_upload_dest(cid) if cid else None
    mk = types.InlineKeyboardMarkup(row_width=2)

    def btn(key, label):
        mark = "✅ " if cur == key else ""
        return types.InlineKeyboardButton(mark + label, callback_data=f"dest|{key}")

    ask_mark = "✅ " if cur not in ('gd', 's3', 'github') else ""
    mk.add(types.InlineKeyboardButton(ask_mark + "❓ پرسیده شود", callback_data="dest|ask"))
    mk.row(btn('gd', "☁️ Google Drive"), btn('s3', "🗄 Railway S3"))
    mk.add(btn('github', "🐙 GitHub"))
    mk.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="set|back"))
    return mk


def cancel_markup(cid=None):
    m = types.InlineKeyboardMarkup()
    label = t(cid, 'cancel_btn') if cid else "❌ لغو"
    m.add(types.InlineKeyboardButton(label, callback_data="cancel_task"))
    return m


def cookie_list_markup(cid=None):
    cookies = list_cookies(cid)
    markup  = types.InlineKeyboardMarkup(row_width=1)
    if not cookies:
        markup.add(types.InlineKeyboardButton(
            t(cid, 'cookie_none') if cid else "❌ هیچ کوکی‌ای ندارید",
            callback_data="ck|none"))
    else:
        for ck in cookies:
            icon = "✅" if ck['enabled'] else "⛔"
            markup.add(types.InlineKeyboardButton(
                f"{icon} {ck['name']}  ({ck['size'] // 1024}KB)",
                callback_data=f"ck|select|{ck['name']}"
            ))
    markup.add(types.InlineKeyboardButton(
        t(cid, 'cookie_add')      if cid else "➕ افزودن کوکی جدید",
        callback_data="ck|add"))
    markup.add(types.InlineKeyboardButton(
        t(cid, 'cookie_help_btn') if cid else "راهنما",
        callback_data="ck|help"))
    markup.add(types.InlineKeyboardButton(
        t(cid, 'cookie_back_btn') if cid else "بازگشت",
        callback_data="ck|back"))
    return markup


def cookie_item_markup(name: str, cid=None):
    enabled = is_cookie_enabled(name, cid)
    markup  = types.InlineKeyboardMarkup(row_width=2)
    if enabled:
        markup.add(types.InlineKeyboardButton(
            t(cid, 'cookie_disable_btn') if cid else "⛔ غیرفعال کردن",
            callback_data=f"ck|disable|{name}"))
    else:
        markup.add(types.InlineKeyboardButton(
            t(cid, 'cookie_enable_btn') if cid else "✅ فعال کردن",
            callback_data=f"ck|enable|{name}"))
    markup.add(types.InlineKeyboardButton(
        t(cid, 'cookie_rename_btn')    if cid else "✏️ تغییر نام",
        callback_data=f"ck|rename|{name}"))
    markup.add(types.InlineKeyboardButton(
        t(cid, 'cookie_delete_btn')    if cid else "🗑 حذف",
        callback_data=f"ck|delete|{name}"))
    markup.add(types.InlineKeyboardButton(
        t(cid, 'cookie_back_list_btn') if cid else "🔙 بازگشت به لیست",
        callback_data="ck|list"))
    return markup


def get_cookie_help(cid=None) -> str:
    """Return the localized cookie help text."""
    return t(cid, 'cookie_help') if cid else t(0, 'cookie_help')
