"""
Centralized localization strings for the bilingual bot (Persian / English).

Usage:
    from locales import t
    bot.send_message(cid, t(cid, 'welcome'))
    bot.send_message(cid, t(cid, 'queue_added', pos=3))
"""

from user_langs import get_lang

# ==============================================================
# All user-facing strings, keyed by a short label.
# 'fa' strings are identical to the original Persian messages.
# ==============================================================
STRINGS = {

    # ── Language selection ─────────────────────────────────────
    'lang_select': {
        'fa': "Please select your language / لطفاً زبان خود را انتخاب کنید",
        'en': "Please select your language / لطفاً زبان خود را انتخاب کنید",
    },
    'btn_english': {
        'fa': "English",
        'en': "English",
    },
    'btn_persian': {
        'fa': "فارسی",
        'en': "فارسی",
    },

    # ── Auth ───────────────────────────────────────────────────
    'ask_password': {
        'fa': "سلام! رمز عبور را وارد کنید:",
        'en': "Hello! Please enter the password:",
    },
    'ask_password_file': {
        'fa': "ابتدا رمز عبور را وارد کنید:",
        'en': "Please enter the password first:",
    },
    'wrong_password': {
        'fa': "❌ رمز اشتباه.",
        'en': "❌ Wrong password.",
    },
    'welcome': {
        'fa': "✅ خوش آمدید!",
        'en': "✅ Welcome!",
    },
    'bot_ready': {
        'fa': "✅ ربات آماده است.",
        'en': "✅ Bot is ready.",
    },

    # ── Cookie manager ─────────────────────────────────────────
    'cookie_received_ask_name': {
        'fa': "✅ فایل دریافت شد.\nنام این کوکی را بفرستید:\n(مثلاً: instagram، default)",
        'en': "✅ File received.\nSend a name for this cookie:\n(e.g.: instagram, default)",
    },
    'cookie_saved': {
        'fa': "✅ کوکی «{name}» ذخیره شد.",
        'en': "✅ Cookie '{name}' saved.",
    },
    'cookie_error': {
        'fa': "❌ خطا: {e}",
        'en': "❌ Error: {e}",
    },
    'cookie_need_txt': {
        'fa': "❌ لطفاً یک فایل .txt بفرستید.",
        'en': "❌ Please send a .txt file.",
    },
    'cookie_invalid_name': {
        'fa': "❌ نام معتبر نیست.",
        'en': "❌ Invalid name.",
    },
    'cookie_data_not_found': {
        'fa': "❌ داده کوکی پیدا نشد.",
        'en': "❌ Cookie data not found.",
    },
    'cookie_invalid_format': {
        'fa': "❌ فرمت کوکی صحیح نیست.",
        'en': "❌ Invalid cookie format.",
    },
    'cookie_text_received': {
        'fa': "✅ دریافت شد.\nنام این کوکی را بفرستید:",
        'en': "✅ Received.\nSend a name for this cookie:",
    },
    'cookie_rename_done': {
        'fa': "✅ نام به «{new_name}» تغییر یافت.",
        'en': "✅ Renamed to '{new_name}'.",
    },
    'cookie_rename_ask': {
        'fa': "نام جدید برای «{name}» را بفرستید:",
        'en': "Send the new name for '{name}':",
    },
    'cookie_manage': {
        'fa': "🍪 مدیریت کوکی‌ها:",
        'en': "🍪 Cookie Manager:",
    },
    'cookie_none': {
        'fa': "❌ هیچ کوکی‌ای ندارید",
        'en': "❌ No cookies found",
    },
    'cookie_add': {
        'fa': "➕ افزودن کوکی جدید",
        'en': "➕ Add New Cookie",
    },
    'cookie_help_btn': {
        'fa': "راهنما",
        'en': "Help",
    },
    'cookie_back_btn': {
        'fa': "بازگشت",
        'en': "Back",
    },
    'cookie_status': {
        'fa': "🍪 کوکی: {name}\nوضعیت: {status}",
        'en': "🍪 Cookie: {name}\nStatus: {status}",
    },
    'cookie_status_active': {
        'fa': "✅ فعال",
        'en': "✅ Active",
    },
    'cookie_status_inactive': {
        'fa': "⛔ غیرفعال",
        'en': "⛔ Disabled",
    },
    'cookie_enable_btn': {
        'fa': "✅ فعال کردن",
        'en': "✅ Enable",
    },
    'cookie_disable_btn': {
        'fa': "⛔ غیرفعال کردن",
        'en': "⛔ Disable",
    },
    'cookie_rename_btn': {
        'fa': "✏️ تغییر نام",
        'en': "✏️ Rename",
    },
    'cookie_delete_btn': {
        'fa': "🗑 حذف",
        'en': "🗑 Delete",
    },
    'cookie_back_list_btn': {
        'fa': "🔙 بازگشت به لیست",
        'en': "🔙 Back to List",
    },
    'cookie_enabled_toast': {
        'fa': "✅ {name} فعال شد.",
        'en': "✅ {name} enabled.",
    },
    'cookie_enabled_msg': {
        'fa': "🍪 {name}\n✅ فعال",
        'en': "🍪 {name}\n✅ Active",
    },
    'cookie_disabled_toast': {
        'fa': "⛔ {name} غیرفعال شد.",
        'en': "⛔ {name} disabled.",
    },
    'cookie_disabled_msg': {
        'fa': "🍪 {name}\n⛔ غیرفعال",
        'en': "🍪 {name}\n⛔ Disabled",
    },
    'cookie_deleted_toast': {
        'fa': "🗑 {name} حذف شد.",
        'en': "🗑 {name} deleted.",
    },
    'cookie_no_cookies_toast': {
        'fa': "هیچ کوکی‌ای ندارید.",
        'en': "No cookies found.",
    },
    'cookie_help': {
        'fa': (
            "🍪 راهنمای گرفتن کوکی:\n\n"
            "1 افزونه Get cookies.txt LOCALLY رو توی کروم نصب کن\n\n"
            "2 وارد سایت مورد نظر بشو\n\n"
            "3 روی آیکون افزونه کلیک کن و Export بزن\n\n"
            "4 فایل رو اینجا بفرست\n\n"
            "نام‌گذاری:\n"
            "• فایل رو با اسم سایت بفرست — مثلاً instagram.txt\n"
            "• یا بعد از ارسال ازت اسم میپرسم\n"
            "• اسم default برای همه سایت‌ها استفاده میشه\n\n"
            "فرمت باید Netscape باشه:\n"
            "خط اول: # Netscape HTTP Cookie File"
        ),
        'en': (
            "🍪 How to get cookies:\n\n"
            "1 Install the 'Get cookies.txt LOCALLY' extension in Chrome\n\n"
            "2 Log in to the target website\n\n"
            "3 Click the extension icon and press Export\n\n"
            "4 Send the file here\n\n"
            "Naming:\n"
            "• Send the file named after the site — e.g. instagram.txt\n"
            "• Or I'll ask you for a name after you send it\n"
            "• The name 'default' is used for all sites\n\n"
            "Format must be Netscape:\n"
            "First line: # Netscape HTTP Cookie File"
        ),
    },

    # ── File reception ─────────────────────────────────────────
    'receiving_file': {
        'fa': "📥 دریافت فایل...",
        'en': "📥 Receiving file...",
    },
    'unsupported_type': {
        'fa': "⚠️ نوع فایل پشتیبانی نمیشه.",
        'en': "⚠️ Unsupported file type.",
    },

    # ── Main menu buttons ──────────────────────────────────────
    'btn_ytdlp': {
        'fa': "🔽 دانلود با yt-dlp",
        'en': "🔽 Download with yt-dlp",
    },
    'btn_torrent': {
        'fa': "🧲 دانلود تورنت",
        'en': "🧲 Download Torrent",
    },
    'btn_direct': {
        'fa': "🌐 دانلود لینک مستقیم",
        'en': "🌐 Direct Link Download",
    },
    'btn_cookie': {
        'fa': "🍪 مدیریت کوکی",
        'en': "🍪 Cookie Manager",
    },
    'btn_queue': {
        'fa': "📊 وضعیت صف",
        'en': "📊 Queue Status",
    },
    'btn_cancel': {
        'fa': "❌ لغو عملیات فعلی",
        'en': "❌ Cancel Current Task",
    },
    'btn_upload_tg': {
        'fa': "📱 آپلود: تلگرام",
        'en': "📱 Upload: Telegram",
    },
    'btn_upload_gd': {
        'fa': "☁️ آپلود: درایو",
        'en': "☁️ Upload: Drive",
    },
    'btn_upload_ask': {
        'fa': "☁️/📱 آپلود: پرسیدن",
        'en': "☁️/📱 Upload: Ask",
    },
    'upload_ask_toast': {
        'fa': "❓ مقصد هر بار پرسیده می‌شود.",
        'en': "❓ Destination will be asked each time.",
    },
    'btn_help': {
        'fa': "ℹ️ راهنما",
        'en': "ℹ️ Help",
    },
    'btn_change_lang': {
        'fa': "تغییر زبان 🌐",
        'en': "Change Language 🌐",
    },
    'btn_settings': {
        'fa': "تنظیمات ⚙️",
        'en': "Settings ⚙️",
    },

    # ── Settings panel ─────────────────────────────────────────
    'settings_panel_title': {
        'fa': "⚙️ پنل تنظیمات",
        'en': "⚙️ Control Panel",
    },
    'btn_mode_ytdlp': {
        'fa': "yt-dlp",
        'en': "yt-dlp",
    },
    'btn_mode_torrent': {
        'fa': "Torrent",
        'en': "Torrent",
    },
    'btn_mode_direct': {
        'fa': "Direct Link",
        'en': "Direct Link",
    },
    'btn_mode_auto': {
        'fa': "Auto Detect",
        'en': "Auto Detect",
    },
    'changed_success_msg': {
        'fa': "✅ تنظیم شد.",
        'en': "✅ Setting applied.",
    },
    'mode_set_toast': {
        'fa': "✅ حالت دانلود تغییر کرد.",
        'en': "✅ Download mode changed.",
    },
    'upload_set_toast': {
        'fa': "✅ مقصد آپلود تغییر کرد.",
        'en': "✅ Upload destination changed.",
    },
    'quality_set_toast': {
        'fa': "✅ کیفیت: {label}",
        'en': "✅ Quality: {label}",
    },
    'media_set_toast': {
        'fa': "✅ مدیا: {label}",
        'en': "✅ Media: {label}",
    },

    'quality_2160': {
        'fa': "🎥 کیفیت: 2160p (4K)",
        'en': "🎥 Quality: 2160p (4K)",
    },
    'quality_1440': {
        'fa': "🖥️ کیفیت: 1440p (2K)",
        'en': "🖥️ Quality: 1440p (2K)",
    },
    'quality_manual': {
        'fa': "🎯 کیفیت: دستی",
        'en': "🎯 Quality: Manual",
    },
    'quality_best': {
        'fa': "⭐ کیفیت: بهترین",
        'en': "⭐ Quality: Best",
    },
    'quality_1080': {
        'fa': "📺 کیفیت: 1080p",
        'en': "📺 Quality: 1080p",
    },
    'quality_720': {
        'fa': "📺 کیفیت: 720p",
        'en': "📺 Quality: 720p",
    },
    'quality_480': {
        'fa': "📺 کیفیت: 480p",
        'en': "📺 Quality: 480p",
    },

    # ── Audio quality labels ────────────────────────────────────
    'audio_quality_320': {
        'fa': "🎵 کیفیت: 320kbps",
        'en': "🎵 Quality: 320kbps",
    },
    'audio_quality_128': {
        'fa': "🎵 کیفیت: 128kbps",
        'en': "🎵 Quality: 128kbps",
    },
    'audio_quality_default': {
        'fa': "🎵 کیفیت: پیش‌فرض",
        'en': "🎵 Quality: Default",
    },

    # ── Video format (container) labels ────────────────────────
    'format_mp4': {
        'fa': "📦 فرمت: MP4",
        'en': "📦 Format: MP4",
    },
    'format_mkv': {
        'fa': "📦 فرمت: MKV",
        'en': "📦 Format: MKV",
    },
    'format_default': {
        'fa': "📦 فرمت: پیش‌فرض",
        'en': "📦 Format: Default",
    },

    # ── Audio format (codec) labels ────────────────────────────
    'format_mp3': {
        'fa': "🎙️ فرمت: MP3",
        'en': "🎙️ Format: MP3",
    },
    'format_m4a': {
        'fa': "🎙️ فرمت: M4A",
        'en': "🎙️ Format: M4A",
    },
    'format_flac': {
        'fa': "🎙️ فرمت: FLAC",
        'en': "🎙️ Format: FLAC",
    },

    # ── Subtitle button labels ─────────────────────────────────
    'btn_subtitle_en': {
        'fa': "💬 زیرنویس: انگلیسی",
        'en': "💬 Subtitle: English",
    },
    'btn_subtitle_fa': {
        'fa': "💬 زیرنویس: فارسی",
        'en': "💬 Subtitle: Persian",
    },
    'btn_subtitle_off': {
        'fa': "💬 زیرنویس: خاموش",
        'en': "💬 Subtitle: Off",
    },

    # ── Chapters button labels ─────────────────────────────────
    'btn_chapters_on': {
        'fa': "📑 فصل‌ها: روشن",
        'en': "📑 Chapters: On",
    },
    'btn_chapters_off': {
        'fa': "📑 فصل‌ها: خاموش",
        'en': "📑 Chapters: Off",
    },

    # ── Settings toast messages ────────────────────────────────
    'format_set_toast': {
        'fa': "✅ فرمت: {label}",
        'en': "✅ Format: {label}",
    },
    'subtitle_set_toast': {
        'fa': "✅ زیرنویس: {label}",
        'en': "✅ Subtitle: {label}",
    },
    'chapters_set_toast': {
        'fa': "✅ فصل‌ها: {label}",
        'en': "✅ Chapters: {label}",
    },

    # ── Subtitle not found warning (appended to upload completion message) ──
    'subtitle_not_found_warn': {
        'fa': "\n⚠️ ویدیو دانلود شد، اما زیرنویس درخواستی پیدا نشد.",
        'en': "\n⚠️ The video was downloaded, but the requested subtitle was not found.",
    },

    'media_video': {
        'fa': "🎬 مدیا: ویدیو",
        'en': "🎬 Media: Video",
    },
    'media_audio': {
        'fa': "🎵 مدیا: موسیقی",
        'en': "🎵 Media: Music",
    },


    # ── Menu messages ──────────────────────────────────────────
    'ytdlp_activated': {
        'fa': (
            "🔽 موتور yt-dlp فعال شد.\n\n"
            "لینک بفرستید — یوتیوب، اینستاگرام، توییتر، ساوندکلاد و هر سایت پشتیبانی‌شده‌ای:"
        ),
        'en': (
            "🔽 yt-dlp engine activated.\n\n"
            "Send a link — YouTube, Instagram, Twitter, SoundCloud, and any supported site:"
        ),
    },
    'ask_magnet': {
        'fa': "لینک مگنت را بفرستید:",
        'en': "Send the magnet link:",
    },
    'ask_direct': {
        'fa': "لینک دانلود را بفرستید:",
        'en': "Send the download link:",
    },

    # ── Help ──────────────────────────────────────────────────────────
    'help_text': {
        'fa': (
            "📖 راهنما:\n\n"
            "🔽 yt-dlp: یوتیوب، اینستاگرام، توییتر، ساوندکلاد و هر سایت پشتیبانی‌شده\n"
            "🧲 تورنت: لینک magnet (با health check و timeout 20min)\n"
            "🌐 لینک مستقیم: GitHub، F-Droid، ...\n"
            "🍪 کوکی: چند کوکی مجزا (ذخیره جداگانه برای هر کاربر)\n"
            "📎 فایل: آپلود مستقیم به درایو\n\n"
            "☁️/📱 تاگل آپلود (۳ حالت):\n"
            "  📱 تلگرام ← ☁️ گوگل درایو ← ❓ پرسیدن هر بار\n"
            "🎯 کیفیت: کیفیت پیش‌فرض رو تنظیم کن (دستی = هر بار میپرسه)\n"
            "⚠️ تورنت بدون پیشرفت در 20 دقیقه لغو میشه"
        ),
        'en': (
            "📖 Help:\n\n"
            "🔽 yt-dlp: YouTube, Instagram, Twitter, SoundCloud, and any supported site\n"
            "🧲 Torrent: magnet link (with health check and 20min timeout)\n"
            "🌐 Direct link: GitHub, F-Droid, ...\n"
            "🍪 Cookie: multiple separate cookies (stored per-user for privacy)\n"
            "📎 File: upload directly to Drive\n\n"
            "☁️/📱 Upload toggle (3 modes):\n"
            "  📱 Telegram → ☁️ Google Drive → ❓ Ask Every Time\n"
            "🎯 Quality: set default quality (manual = asks every time)\n"
            "⚠️ Torrent with no progress in 20 minutes will be cancelled"
        ),
    },

    # ── Queue status ───────────────────────────────────────────
    'queue_running': {
        'fa': "▶️ در حال اجرا:\n{type} | {title}\n",
        'en': "▶️ Running:\n{type} | {title}\n",
    },
    'queue_nothing_running': {
        'fa': "▶️ در حال اجرا: ندارد\n",
        'en': "▶️ Running: none\n",
    },
    'queue_empty': {
        'fa': "مورد دیگری در صف نیست.",
        'en': "No other items in queue.",
    },
    'queue_waiting': {
        'fa': "🔢 منتظر در صف ({count} مورد):",
        'en': "🔢 Waiting in queue ({count} items):",
    },
    'queue_unknown': {
        'fa': "نامشخص",
        'en': "Unknown",
    },
    'queue_clear_btn': {
        'fa': "🗑 پاک کردن کل صف",
        'en': "🗑 Clear All Queue",
    },
    'queue_refresh_btn': {
        'fa': "🔄 رفرش",
        'en': "🔄 Refresh",
    },
    'queue_cleared_toast': {
        'fa': "✅ صف پاک شد.",
        'en': "✅ Queue cleared.",
    },
    'queue_removed_toast': {
        'fa': "✅ حذف شد",
        'en': "✅ Removed",
    },
    'queue_not_found_toast': {
        'fa': "❌ یافت نشد",
        'en': "❌ Not found",
    },
    'queue_refreshed_toast': {
        'fa': "🔄 بروزرسانی شد.",
        'en': "🔄 Refreshed.",
    },

    # ── Cancel ─────────────────────────────────────────────────
    'cancel_requested': {
        'fa': "🚫 درخواست لغو ارسال شد.",
        'en': "🚫 Cancel request sent.",
    },
    'cancel_nothing': {
        'fa': "هیچ عملیاتی در حال اجرا نیست.",
        'en': "No operation is currently running.",
    },
    'cancel_no_task_toast': {
        'fa': "عملیاتی نیست.",
        'en': "No operation running.",
    },
    'upload_cancelled_toast': {
        'fa': "🚫 آپلود لغو شد.",
        'en': "🚫 Upload cancelled.",
    },

    # ── Upload toggle ──────────────────────────────────────────
    'dest_gdrive': {
        'fa': "☁️ مقصد پیش‌فرض: گوگل درایو",
        'en': "☁️ Default destination: Google Drive",
    },
    'dest_tg': {
        'fa': "📱 مقصد پیش‌فرض: تلگرام",
        'en': "📱 Default destination: Telegram",
    },
    'dest_gdrive_toast': {
        'fa': "☁️ مقصد: گوگل درایو",
        'en': "☁️ Destination: Google Drive",
    },
    'dest_tg_toast': {
        'fa': "📱 مقصد: تلگرام",
        'en': "📱 Destination: Telegram",
    },

    # ── Quality / media mode ───────────────────────────────────
    'quality_set': {
        'fa': "✅ کیفیت پیش‌فرض: {label}",
        'en': "✅ Default quality: {label}",
    },
    'audio_on': {
        'fa': "🎵 حالت موسیقی فعال شد — دانلودها به MP3 تبدیل میشن.",
        'en': "🎵 Music mode activated — downloads will be converted to MP3.",
    },
    'audio_off': {
        'fa': "🎬 حالت ویدیو فعال شد.",
        'en': "🎬 Video mode activated.",
    },

    # ── Link handling ──────────────────────────────────────────
    'invalid_link': {
        'fa': "❓ لینک معتبر نیست.",
        'en': "❓ Invalid link.",
    },
    'unknown_link': {
        'fa': "❓ لینک شناخته‌شده‌ای نیست.",
        'en': "❓ Unrecognized link.",
    },
    'not_youtube': {
        'fa': "❌ لینک یوتیوب نیست.",
        'en': "❌ Not a YouTube link.",
    },
    'not_magnet': {
        'fa': "❌ لینک مگنت نیست.",
        'en': "❌ Not a magnet link.",
    },
    'checking_link': {
        'fa': "🔍 بررسی لینک...",
        'en': "🔍 Checking link...",
    },
    'fetching_info': {
        'fa': "🔍 دریافت اطلاعات از {domain}...",
        'en': "🔍 Fetching info from {domain}...",
    },
    'unknown_title': {
        'fa': "نامشخص",
        'en': "Unknown",
    },

    # ── YouTube ────────────────────────────────────────────────
    'yt_playlist_label': {
        'fa': "📺 پلی‌لیست ویدیو ({count})",
        'en': "📺 Video Playlist ({count})",
    },
    'yt_playlist_mp3': {
        'fa': "🎵 پلی‌لیست MP3",
        'en': "🎵 MP3 Playlist",
    },
    'yt_playlist_info': {
        'fa': "📋 {title}\n{count} ویدیو",
        'en': "📋 {title}\n{count} videos",
    },
    'ask_dest': {
        'fa': "مقصد:",
        'en': "Destination:",
    },
    'btn_tg': {
        'fa': "📱 تلگرام",
        'en': "📱 Telegram",
    },
    'btn_gd': {
        'fa': "☁️ گوگل درایو",
        'en': "☁️ Google Drive",
    },
    'yt_audio_dest_msg': {
        'fa': "🎬 {title}\n⏱ {m}:{s}\n🎵 MP3\nمقصد:",
        'en': "🎬 {title}\n⏱ {m}:{s}\n🎵 MP3\nDestination:",
    },
    'yt_quality_dest_msg': {
        'fa': "🎬 {title}\n⏱ {m}:{s}\nکیفیت: {quality}\nمقصد:",
        'en': "🎬 {title}\n⏱ {m}:{s}\nQuality: {quality}\nDestination:",
    },
    'yt_queued': {
        'fa': "✅ ثبت شد.\n🎬 {title}\n{quality} | {dest_icon}\n🔢 جایگاه: {pos}",
        'en': "✅ Queued.\n🎬 {title}\n{quality} | {dest_icon}\n🔢 Position: {pos}",
    },
    'fetching_quality': {
        'fa': "⏳ دریافت اطلاعات کیفیت‌ها...",
        'en': "⏳ Fetching quality info...",
    },
    'select_quality': {
        'fa': "🎬 {title}\n⏱ {m}:{s}\nکیفیت را انتخاب کنید:",
        'en': "🎬 {title}\n⏱ {m}:{s}\nSelect quality:",
    },
    'best_quality': {
        'fa': "⭐ بهترین",
        'en': "⭐ Best",
    },
    'yt_quality_dest_only': {
        'fa': "کیفیت: {quality}\nمقصد:",
        'en': "Quality: {quality}\nDestination:",
    },
    'yt_queued_cb': {
        'fa': "✅ ثبت شد.\n{quality} | {dest_icon}\n🔢 جایگاه: {pos}",
        'en': "✅ Queued.\n{quality} | {dest_icon}\n🔢 Position: {pos}",
    },
    'invalid_option_toast': {
        'fa': "گزینه نامعتبر.",
        'en': "Invalid option.",
    },
    'link_expired_toast': {
        'fa': "لینک منقضی شده.",
        'en': "Link has expired.",
    },

    # ── Torrent ────────────────────────────────────────────────
    'torrent_queued': {
        'fa': "🧲 به صف افزوده شد. {dest_icon}",
        'en': "🧲 Added to queue. {dest_icon}",
    },
    'torrent_queued_cb': {
        'fa': "🧲 به صف افزوده شد.\n{dest_icon}",
        'en': "🧲 Added to queue.\n{dest_icon}",
    },
    'torrent_cancelled': {
        'fa': "انصراف.",
        'en': "Cancelled.",
    },
    'torrent_cancel_msg': {
        'fa': "❌ لغو شد.",
        'en': "❌ Cancelled.",
    },

    # ── Direct link ────────────────────────────────────────────
    'direct_queued': {
        'fa': "✅ به صف افزوده شد. {dest_icon}",
        'en': "✅ Added to queue. {dest_icon}",
    },
    'direct_queued_cb': {
        'fa': "✅ به صف.\n{dest_icon}",
        'en': "✅ Queued.\n{dest_icon}",
    },

    # ── Social media ───────────────────────────────────────────
    'social_queued': {
        'fa': "✅ به صف.\n🌐 {domain}\n🎵 MP3 | {dest_icon}",
        'en': "✅ Queued.\n🌐 {domain}\n🎵 MP3 | {dest_icon}",
    },
    'social_audio_dest_msg': {
        'fa': "🌐 {domain}\n🎵 MP3\nمقصد:",
        'en': "🌐 {domain}\n🎵 MP3\nDestination:",
    },
    'social_quality_dest_msg': {
        'fa': "🌐 {domain}\nکیفیت: {quality}\nمقصد:",
        'en': "🌐 {domain}\nQuality: {quality}\nDestination:",
    },
    'social_quality_queued': {
        'fa': "✅ به صف.\n🌐 {domain}\nکیفیت: {quality} | {dest_icon}",
        'en': "✅ Queued.\n🌐 {domain}\nQuality: {quality} | {dest_icon}",
    },
    'social_select_quality': {
        'fa': "🌐 {title}\nکیفیت را انتخاب کنید:",
        'en': "🌐 {title}\nSelect quality:",
    },
    'best_quality_btn': {
        'fa': "⭐ بهترین کیفیت",
        'en': "⭐ Best Quality",
    },
    'social_added_to_queue': {
        'fa': "⬇️ به صف افزوده شد. {dest_icon}",
        'en': "⬇️ Added to queue. {dest_icon}",
    },
    'social_added_cb': {
        'fa': "⬇️ به صف افزوده شد...",
        'en': "⬇️ Added to queue...",
    },
    'select_dest': {
        'fa': "مقصد را انتخاب کنید:",
        'en': "Select destination:",
    },
    'select_dest_cancelled': {
        'fa': "انتخاب مقصد لغو شد.",
        'en': "Destination selection cancelled.",
    },

    # ── Playlist ───────────────────────────────────────────────
    'playlist_quality': {
        'fa': "کیفیت پلی‌لیست:",
        'en': "Playlist quality:",
    },
    'playlist_count_ask': {
        'fa': "{media}\nچند تا دانلود کنم?",
        'en': "{media}\nHow many to download?",
    },
    'playlist_all_btn': {
        'fa': "همه",
        'en': "All",
    },
    'playlist_custom_btn': {
        'fa': "✏️ تعداد دلخواه",
        'en': "✏️ Custom Count",
    },
    'playlist_ask_custom': {
        'fa': "تعداد مورد نظر را وارد کنید (عدد):",
        'en': "Enter the desired count (number):",
    },
    'playlist_invalid_count': {
        'fa': "❌ عدد معتبر وارد کنید.",
        'en': "❌ Please enter a valid number.",
    },
    'playlist_link_expired': {
        'fa': "❌ لینک منقضی شده.",
        'en': "❌ Link has expired.",
    },
    'playlist_queued': {
        'fa': "✅ به صف افزوده شد.\n{count} عدد | {dest_icon}",
        'en': "✅ Added to queue.\n{count} items | {dest_icon}",
    },
    'playlist_queued_cb': {
        'fa': "✅ به صف.\n{count} عدد | {dest_icon}",
        'en': "✅ Queued.\n{count} items | {dest_icon}",
    },
    'playlist_dest_msg': {
        'fa': "{media} — {count} عدد\nمقصد:",
        'en': "{media} — {count} items\nDestination:",
    },
    'playlist_media_video': {
        'fa': "📺 {quality}",
        'en': "📺 {quality}",
    },
    'playlist_media_audio': {
        'fa': "🎵 MP3",
        'en': "🎵 MP3",
    },

    # ── Downloader status messages ─────────────────────────────
    'disk_no_space': {
        'fa': "❌ فضای دیسک کافی نیست! {free} آزاد است.",
        'en': "❌ Not enough disk space! {free} free.",
    },
    'connecting_youtube': {
        'fa': "🔗 ارتباط با سرور یوتیوب...",
        'en': "🔗 Connecting to YouTube server...",
    },
    'cancel_btn': {
        'fa': "❌ لغو",
        'en': "❌ Cancel",
    },
    'download_cancelled': {
        'fa': "🚫 دانلود لغو شد.",
        'en': "🚫 Download cancelled.",
    },
    'processing_file': {
        'fa': "☁️ پردازش فایل و آماده‌سازی برای آپلود...",
        'en': "☁️ Processing file and preparing for upload...",
    },
    'fetching_playlist': {
        'fa': "📋 دریافت لیست پلی‌لیست...",
        'en': "📋 Fetching playlist...",
    },
    'uploading_item': {
        'fa': "⬆️ آپلود {idx}/{total}: {name}",
        'en': "⬆️ Uploading {idx}/{total}: {name}",
    },
    'playlist_done': {
        'fa': "✅ پلی‌لیست تموم شد!\n📁 {title}\nموفق: {ok} / {total}",
        'en': "✅ Playlist complete!\n📁 {title}\nSuccess: {ok} / {total}",
    },
    'torrent_checking': {
        'fa': "🔍 بررسی سلامت تورنت...",
        'en': "🔍 Checking torrent health...",
    },
    'torrent_size_unknown': {
        'fa': "نامشخص",
        'en': "Unknown",
    },
    'torrent_verdict_none': {
        'fa': "🔴 هیچ seeder ای نیست",
        'en': "🔴 No seeders",
    },
    'torrent_verdict_slow': {
        'fa': "🟡 {sd} seeder — کند",
        'en': "🟡 {sd} seeder(s) — slow",
    },
    'torrent_verdict_ok': {
        'fa': "🟢 {sd} seeder — سالم",
        'en': "🟢 {sd} seeder(s) — healthy",
    },
    'torrent_confirm_msg': {
        'fa': "📊 نتیجه بررسی:\nحجم: {size}\n🌱 Seeder: {sd} | 📥 Leecher: {lc}\n{verdict}\n\nادامه بدم؟",
        'en': "📊 Health check result:\nSize: {size}\n🌱 Seeders: {sd} | 📥 Leechers: {lc}\n{verdict}\n\nProceed?",
    },
    'torrent_btn_download': {
        'fa': "✅ دانلود کن",
        'en': "✅ Download",
    },
    'torrent_btn_cancel': {
        'fa': "❌ انصراف",
        'en': "❌ Cancel",
    },
    'torrent_cancel_cb': {
        'fa': "🚫 لغو شد.",
        'en': "🚫 Cancelled.",
    },
    'torrent_timeout': {
        'fa': "⏰ تورنت به دلیل عدم پیشرفت در ۲۰ دقیقه لغو شد.",
        'en': "⏰ Torrent cancelled due to no progress in 20 minutes.",
    },
    'torrent_file_not_found': {
        'fa': "هیچ فایلی پیدا نشد.",
        'en': "No file found.",
    },
    'torrent_preparing_upload': {
        'fa': "☁️ آماده‌سازی برای آپلود...",
        'en': "☁️ Preparing for upload...",
    },
    'torrent_downloading': {
        'fa': "در حال دانلود تورنت...",
        'en': "Downloading torrent...",
    },
    'torrent_no_progress_warn': {
        'fa': "\n⚠️ بدون پیشرفت: {m}m{s}s / 20m",
        'en': "\n⚠️ No progress: {m}m{s}s / 20m",
    },
    'direct_preparing': {
        'fa': "🔗 آماده‌سازی لینک...",
        'en': "🔗 Preparing link...",
    },
    'direct_upload_preparing': {
        'fa': "☁️ آماده‌سازی برای آپلود...",
        'en': "☁️ Preparing for upload...",
    },
    'social_preparing': {
        'fa': "🔗 دریافت از {domain}...",
        'en': "🔗 Fetching from {domain}...",
    },
    'social_upload_preparing': {
        'fa': "☁️ آماده‌سازی برای آپلود...",
        'en': "☁️ Preparing for upload...",
    },
    'social_cancelled': {
        'fa': "لغو",
        'en': "Cancelled",
    },
    'file_not_found_err': {
        'fa': "فایل پیدا نشد",
        'en': "File not found",
    },

    # ── Upload status messages ─────────────────────────────────
    'upload_cancelled': {
        'fa': "🚫 آپلود لغو شد.",
        'en': "🚫 Upload cancelled.",
    },
    'getting_gdrive_link': {
        'fa': "⌛ در حال دریافت لینک دانلود از گوگل درایو...",
        'en': "⌛ Getting download link from Google Drive...",
    },
    'gdrive_upload_done': {
        'fa': "✅ آپلود به گوگل درایو تموم شد!\n📄 {title}\n📦 {size} • {source} {quality}\n📂 {folder}\n",
        'en': "✅ Upload to Google Drive complete!\n📄 {title}\n📦 {size} • {source} {quality}\n📂 {folder}\n",
    },
    'gdrive_direct_link': {
        'fa': "⬇️ <a href='{link}'>دانلود مستقیم</a>",
        'en': "⬇️ <a href='{link}'>Direct Download</a>",
    },
    'gdrive_view_link': {
        'fa': "☁️ <a href='{link}'>مشاهده در درایو</a>",
        'en': "☁️ <a href='{link}'>View in Drive</a>",
    },
    'gdrive_link_error': {
        'fa': "⚠️ (خطا در دریافت لینک)",
        'en': "⚠️ (Error retrieving link)",
    },
    'gdrive_upload_fallback': {
        'fa': "✅ آپلود شد: {name}\n⚠️ خطا در لینک: {e}",
        'en': "✅ Uploaded: {name}\n⚠️ Link error: {e}",
    },
    'gdrive_upload_error': {
        'fa': "❌ خطا در آپلود به گوگل درایو.",
        'en': "❌ Error uploading to Google Drive.",
    },
    'tg_upload_large': {
        'fa': "⚠️ حجم {size}MB — بیش از 2GB.\nآپلود به گوگل درایو...",
        'en': "⚠️ Size {size}MB — over 2GB.\nUploading to Google Drive...",
    },
    'tg_uploading': {
        'fa': "⬆️ در حال ارسال به تلگرام...\n(به دلیل محدودیت تلگرام، درصد آپلود قابل نمایش نیست)",
        'en': "⬆️ Sending to Telegram...\n(Upload percentage cannot be displayed due to Telegram limitations)",
    },
    'tg_upload_done': {
        'fa': "✅ دانلود و آپلود تموم شد!\n📁 {title}\n📦 {size} • 🌐 {source} {quality}\n📱 آپلود شده در تلگرام",
        'en': "✅ Download and upload complete!\n📁 {title}\n📦 {size} • 🌐 {source} {quality}\n📱 Uploaded to Telegram",
    },
    'tg_folder_files': {
        'fa': "📂 {count} فایل یافت شد.",
        'en': "📂 {count} file(s) found.",
    },
    'smart_dest_large': {
        'fa': "⚠️ حجم {size} بیش از 2GB است.\n☁️ انتقال خودکار به گوگل درایو...",
        'en': "⚠️ Size {size} exceeds 2GB.\n☁️ Automatically transferring to Google Drive...",
    },

    # ── Retry / error (downloader_queue) ──────────────────────
    'retry_error': {
        'fa': "⚠️ خطا در دانلود (تلاش {attempt}/{max}):\n{error}\n\n⏳ {delay} ثانیه دیگر دوباره امتحان میکنم...",
        'en': "⚠️ Download error (attempt {attempt}/{max}):\n{error}\n\n⏳ Retrying in {delay} seconds...",
    },
    'max_retries_error': {
        'fa': "❌ بعد از {max} بار تلاش موفق نشدم:\n{error}",
        'en': "❌ Failed after {max} attempts:\n{error}",
    },
    'generic_error': {
        'fa': "❌ خطا:\n{error}",
        'en': "❌ Error:\n{error}",
    },

    # ── Friendly errors ────────────────────────────────────────
    'err_login': {
        'fa': "🔒 محتوا نیاز به لاگین دارد.\n➡️ از منوی 🍪 مدیریت کوکی، کوکی سایت را اضافه کنید.",
        'en': "🔒 Content requires login.\n➡️ Add the site cookie via the 🍪 Cookie Manager.",
    },
    'err_404': {
        'fa': "🔗 لینک پیدا نشد (404).\n➡️ لینک را بررسی کنید — ممکن است حذف شده یا private باشد.\n💡 اگه لینک share از اپ بود، لینک مستقیم مرورگر را امتحان کنید.",
        'en': "🔗 Link not found (404).\n➡️ Check the link — it may have been deleted or is private.\n💡 If the link was shared from an app, try the browser's direct link.",
    },
    'err_no_video': {
        'fa': "🎬 ویدیویی در این لینک پیدا نشد.\n➡️ مطمئن شوید لینک مستقیم ویدیو است.",
        'en': "🎬 No video found at this link.\n➡️ Make sure it is a direct video link.",
    },
    'err_network': {
        'fa': "🌐 خطای شبکه — اتصال برقرار نشد.\n➡️ چند ثانیه دیگر دوباره امتحان میکنم.",
        'en': "🌐 Network error — connection failed.\n➡️ I will retry in a few seconds.",
    },
    'err_disk': {
        'fa': "💾 فضای دیسک کافی نیست! آزاد: {free}\n➡️ لطفاً با ادمین تماس بگیرید.",
        'en': "💾 Not enough disk space! Free: {free}\n➡️ Please contact the admin.",
    },
    'err_yt_403': {
        'fa': "🚫 یوتیوب دانلود این ویدیو رو مسدود کرده (403).\n➡️ چند دقیقه بعد دوباره امتحان کن یا کیفیت دیگه‌ای انتخاب کن.\n💡 اگه تکرار شد، کوکی تازهٔ یوتیوب اضافه کن.",
        'en': "🚫 YouTube blocked this download (403).\n➡️ Try again in a few minutes or pick another quality.\n💡 If it repeats, add a fresh YouTube cookie.",
    },
    'err_login_fresh': {
        'fa': "🔒 یوتیوب میگه لاگین لازمه.\n➡️ کوکی تازه بگیر: از مرورگر لاگین کن، افزونهٔ «Get cookies.txt LOCALLY» رو نصب کن، خروجی بگیر و از منوی 🍪 بفرست.\n💡 کوکی قدیمی/منقضی هم همین خطا میده — پاکش کن و جدید بفرست.",
        'en': "🔒 YouTube says login is required.\n➡️ Get a fresh cookie: log in via browser, export cookies.txt with the \"Get cookies.txt LOCALLY\" extension, send it via the 🍪 menu.\n💡 An old/expired cookie gives this too — delete it and send a new one.",
    },
    'err_unsupported': {
        'fa': "🚫 این سایت پشتیبانی نمیشود.\n➡️ از گزینه 🌐 لینک مستقیم استفاده کنید.",
        'en': "🚫 This site is not supported.\n➡️ Use the 🌐 Direct Link option.",
    },
    'err_copyright': {
        'fa': "⛔ این محتوا به دلیل کپی‌رایت قابل دانلود نیست.",
        'en': "⛔ This content cannot be downloaded due to copyright.",
    },
    'err_format': {
        'fa': "📹 کیفیت انتخابی موجود نیست.\n➡️ کیفیت پایین‌تری انتخاب کنید.",
        'en': "📹 Selected quality is not available.\n➡️ Choose a lower quality.",
    },
    'err_torrent': {
        'fa': "🧲 خطا در دانلود تورنت.\n➡️ لینک مگنت را بررسی کنید یا تورنت دیگری امتحان کنید.",
        'en': "🧲 Torrent download error.\n➡️ Check the magnet link or try a different torrent.",
    },
    'err_rclone': {
        'fa': "☁️ خطا در آپلود به گوگل درایو.\n➡️ تنظیمات rclone را بررسی کنید.",
        'en': "☁️ Error uploading to Google Drive.\n➡️ Check rclone configuration.",
    },
    'err_technical': {
        'fa': "⚙️ خطای فنی:\n{err}",
        'en': "⚙️ Technical error:\n{err}",
    },

    # ── ETA label in progress card ─────────────────────────────
    'eta_seconds': {
        'fa': "~{eta} ثانیه",
        'en': "~{eta}s",
    },
    'eta_unknown': {
        'fa': "نامشخص",
        'en': "Unknown",
    },
    'progress_title_unknown': {
        'fa': "نامشخص",
        'en': "Unknown",
    },

    # ── downloader_queue internal ──────────────────────────────
    'cancelled_keyword': {
        'fa': "لغو",
        'en': "Cancelled",
    },
    'unknown_task_type': {
        'fa': "نوع task ناشناخته: {t}",
        'en': "Unknown task type: {t}",
    },

    # ── User profile dashboard ────────────────────────────────
    'btn_profile': {
        'fa': "👤 پروفایل من",
        'en': "👤 My Profile",
    },
    'profile_stats': {
        'fa': (
            "📊 آمار شما:\n\n"
            "📅 روزانه:\n"
            "📥 دانلودها: {files}/{max_files}\n"
            "💾 حجم: {used_gb:.2f}/{max_gb:.2f} GB\n\n"
            "📆 ماهانه:\n"
            "📥 دانلودها: {monthly_files}/{max_monthly_files}\n"
            "💾 حجم: {monthly_used_gb:.2f}/{monthly_max_gb:.2f} GB"
        ),
        'en': (
            "📊 Your stats:\n\n"
            "📅 Daily:\n"
            "📥 Downloads: {files}/{max_files}\n"
            "💾 Data used: {used_gb:.2f}/{max_gb:.2f} GB\n\n"
            "📆 Monthly:\n"
            "📥 Downloads: {monthly_files}/{max_monthly_files}\n"
            "💾 Data used: {monthly_used_gb:.2f}/{monthly_max_gb:.2f} GB"
        ),
    },

    # ── Join-request flow ─────────────────────────────────────
    'registration_closed': {
        'fa': "🔒 ثبت‌نام در حال حاضر بسته است.",
        'en': "🔒 Registration is currently closed.",
    },
    'btn_request_access': {
        'fa': "🙋\u200d♂️ درخواست دسترسی",
        'en': "🙋\u200d♂️ Request Access",
    },
    'join_request_sent': {
        'fa': "✅ درخواست شما به ادمین ارسال شد. لطفاً منتظر بمانید.",
        'en': "✅ Your request has been sent to the admin. Please wait.",
    },
    'join_request_already_sent': {
        'fa': "⏳ درخواست شما قبلاً ارسال شده. لطفاً منتظر تأیید باشید.",
        'en': "⏳ Your request was already sent. Please wait for approval.",
    },
    'join_request_admin_msg': {
        'fa': "🙋 درخواست دسترسی جدید:\nUser ID: <code>{user_id}</code>\nنام: {full_name}\nUsername: @{username}",
        'en': "🙋 New access request:\nUser ID: <code>{user_id}</code>\nName: {full_name}\nUsername: @{username}",
    },
    'btn_approve': {
        'fa': "✅ تایید",
        'en': "✅ Approve",
    },
    'btn_reject': {
        'fa': "❌ رد",
        'en': "❌ Reject",
    },
    'join_approved_user_notify': {
        'fa': "✅ درخواست دسترسی شما تأیید شد! اکنون می‌توانید از ربات استفاده کنید.",
        'en': "✅ Your access request was approved! You can now use the bot.",
    },
    'join_rejected_user_notify': {
        'fa': "❌ متأسفانه درخواست دسترسی شما رد شد.",
        'en': "❌ Unfortunately your access request was rejected.",
    },
    'join_approved_admin_toast': {
        'fa': "✅ کاربر تأیید شد.",
        'en': "✅ User approved.",
    },
    'join_rejected_admin_toast': {
        'fa': "❌ کاربر رد شد.",
        'en': "❌ User rejected.",
    },
    'not_approved': {
        'fa': "❌ شما هنوز تأیید نشده‌اید. لطفاً ابتدا درخواست دسترسی ارسال کنید.",
        'en': "❌ You are not yet approved. Please send an access request first.",
    },

    # ── Admin commands ────────────────────────────────────────
    'admin_only': {
        'fa': "⛔ این دستور فقط برای ادمین است.",
        'en': "⛔ This command is for admins only.",
    },
    'admin_adduser_usage': {
        'fa': "❌ استفاده: /adduser <user_id>",
        'en': "❌ Usage: /adduser <user_id>",
    },
    'admin_adduser_done': {
        'fa': "✅ کاربر {user_id} اضافه و تأیید شد.",
        'en': "✅ User {user_id} added and approved.",
    },
    'admin_deluser_usage': {
        'fa': "❌ استفاده: /deluser <user_id>",
        'en': "❌ Usage: /deluser <user_id>",
    },
    'admin_deluser_done': {
        'fa': "✅ کاربر {user_id} غیرفعال شد.",
        'en': "✅ User {user_id} disabled.",
    },
    'admin_setquota_usage': {
        'fa': "❌ استفاده:\n/setquota <user_id> <files> <GB>\n/setquota <user_id> <files> <GB> <monthly_files> <monthly_GB>",
        'en': "❌ Usage:\n/setquota <user_id> <files> <GB>\n/setquota <user_id> <files> <GB> <monthly_files> <monthly_GB>",
    },
    'admin_setquota_done': {
        'fa': "✅ سهمیه روزانه کاربر {user_id} به‌روز شد:\n📥 فایل: {files}\n💾 حجم: {gb} GB",
        'en': "✅ Daily quota for user {user_id} updated:\n📥 Files: {files}\n💾 Size: {gb} GB",
    },
    'admin_setquota_done_full': {
        'fa': (
            "✅ سهمیه کاربر {user_id} به‌روز شد:\n"
            "📅 روزانه: {files} فایل / {gb} GB\n"
            "📆 ماهانه: {m_files} فایل / {m_gb} GB"
        ),
        'en': (
            "✅ Quota for user {user_id} updated:\n"
            "📅 Daily: {files} files / {gb} GB\n"
            "📆 Monthly: {m_files} files / {m_gb} GB"
        ),
    },
    'admin_togglereg_done': {
        'fa': "✅ وضعیت ثبت‌نام عمومی: {status}",
        'en': "✅ Public registration is now: {status}",
    },
    'admin_togglereg_open': {
        'fa': "باز",
        'en': "Open",
    },
    'admin_togglereg_closed': {
        'fa': "بسته",
        'en': "Closed",
    },
    'admin_broadcast_usage': {
        'fa': "❌ استفاده: /broadcast <پیام>",
        'en': "❌ Usage: /broadcast <message>",
    },
    'admin_broadcast_done': {
        'fa': "✅ پیام به {count} کاربر ارسال شد.",
        'en': "✅ Message sent to {count} users.",
    },
    'admin_user_self_blocked': {
        'fa': "⛔ این عمل برای ادمین اصلی مجاز نیست.",
        'en': "⛔ This action is not allowed for the main admin.",
    },
    'admin_users_title': {
        'fa': "👥 لیست کاربران ثبت‌شده\nصفحه {page}/{pages} • کل: {total}",
        'en': "👥 Signed-Up Users\nPage {page}/{pages} • Total: {total}",
    },
    'admin_users_title_search': {
        'fa': "🔎 نتایج جستجو: {query}\nصفحه {page}/{pages} • کل: {total}",
        'en': "🔎 Search results: {query}\nPage {page}/{pages} • Total: {total}",
    },
    'admin_users_empty': {
        'fa': "موردی پیدا نشد.",
        'en': "No users found.",
    },
    'admin_users_row': {
        'fa': "ID: {user_id} | {status}\nUsername: {username}\nName: {display_name}",
        'en': "ID: {user_id} | {status}\nUsername: {username}\nName: {display_name}",
    },
    'admin_users_open_btn': {
        'fa': "🔍 مدیریت کاربر {user_id}",
        'en': "🔍 Manage user {user_id}",
    },
    'admin_users_prev_btn': {
        'fa': "⬅️ قبلی",
        'en': "⬅️ Prev",
    },
    'admin_users_next_btn': {
        'fa': "بعدی ➡️",
        'en': "Next ➡️",
    },
    'admin_users_search_btn': {
        'fa': "🔎 جستجو",
        'en': "🔎 Search",
    },
    'admin_users_clear_search_btn': {
        'fa': "🧹 پاک‌کردن جستجو",
        'en': "🧹 Clear Search",
    },
    'admin_users_search_prompt': {
        'fa': "عبارت جستجو را بفرستید: ID عددی، @username یا نام نمایشی.",
        'en': "Send search text: numeric ID, @username, or display name.",
    },
    'admin_users_search_cleared_toast': {
        'fa': "✅ جستجو پاک شد.",
        'en': "✅ Search cleared.",
    },
    'admin_users_bad_action': {
        'fa': "❌ عملیات نامعتبر.",
        'en': "❌ Invalid action.",
    },
    'admin_user_not_found': {
        'fa': "❌ کاربر {user_id} پیدا نشد.",
        'en': "❌ User {user_id} not found.",
    },
    'admin_user_status_enabled': {
        'fa': "✅ فعال",
        'en': "✅ Enabled",
    },
    'admin_user_status_disabled': {
        'fa': "⛔ غیرفعال",
        'en': "⛔ Disabled",
    },
    'admin_user_status_admin': {
        'fa': "👑 ادمین",
        'en': "👑 Admin",
    },
    'admin_user_detail': {
        'fa': (
            "🛡 مدیریت کاربر\n"
            "ID: {user_id}\n"
            "وضعیت: {status}\n"
            "Username: {username}\n"
            "Name: {display_name}\n\n"
            "📅 مصرف روزانه:\n"
            "📥 {files_today} فایل | 💾 {used_gb:.2f} / {quota_gb:.2f} GB\n\n"
            "📆 مصرف ماهانه:\n"
            "📥 {monthly_files_used}/{monthly_quota_files} فایل | 💾 {monthly_gb_used:.2f} / {monthly_quota_gb:.2f} GB\n\n"
            "📊 آمار دانلود فایل:\n"
            "امروز: {files_today_stats} | این هفته: {files_week} | این ماه: {files_month} | همه‌زمان: {files_all}\n"
            "📊 آمار حجم (GB):\n"
            "امروز: {bytes_today_stats_gb:.2f} | این هفته: {bytes_week_gb:.2f} | این ماه: {bytes_month_gb:.2f} | همه‌زمان: {bytes_all_gb:.2f}"
        ),
        'en': (
            "🛡 User Management\n"
            "ID: {user_id}\n"
            "Status: {status}\n"
            "Username: {username}\n"
            "Name: {display_name}\n\n"
            "📅 Daily usage:\n"
            "📥 {files_today} files | 💾 {used_gb:.2f} / {quota_gb:.2f} GB\n\n"
            "📆 Monthly usage:\n"
            "📥 {monthly_files_used}/{monthly_quota_files} files | 💾 {monthly_gb_used:.2f} / {monthly_quota_gb:.2f} GB\n\n"
            "📊 File download stats:\n"
            "Today: {files_today_stats} | This week: {files_week} | This month: {files_month} | All time: {files_all}\n"
            "📊 Volume stats (GB):\n"
            "Today: {bytes_today_stats_gb:.2f} | This week: {bytes_week_gb:.2f} | This month: {bytes_month_gb:.2f} | All time: {bytes_all_gb:.2f}"
        ),
    },
    'admin_user_disable_confirm': {
        'fa': "⚠️ آیا از غیرفعال‌کردن این کاربر مطمئن هستید؟ دانلود فعال او قطع می‌شود.",
        'en': "⚠️ Confirm disabling this user? Any active download will be stopped.",
    },
    'admin_user_usage_minus_btn': {
        'fa': "➖ مصرف فایل",
        'en': "➖ File Usage",
    },
    'admin_user_usage_plus_btn': {
        'fa': "➕ مصرف فایل",
        'en': "➕ File Usage",
    },
    'admin_user_quota_minus_btn': {
        'fa': "➖ 0.5GB سقف",
        'en': "➖ 0.5GB Quota",
    },
    'admin_user_quota_plus_btn': {
        'fa': "➕ 0.5GB سقف",
        'en': "➕ 0.5GB Quota",
    },
    'admin_user_enable_btn': {
        'fa': "✅ فعال‌سازی",
        'en': "✅ Enable",
    },
    'admin_user_disable_btn': {
        'fa': "⛔ غیرفعال‌سازی",
        'en': "⛔ Disable",
    },
    'admin_user_disable_yes_btn': {
        'fa': "✅ بله، غیرفعال شود",
        'en': "✅ Yes, Disable",
    },
    'admin_user_disable_no_btn': {
        'fa': "↩️ انصراف",
        'en': "↩️ Cancel",
    },
    'admin_user_back_btn': {
        'fa': "🔙 بازگشت به لیست",
        'en': "🔙 Back to List",
    },
    'admin_user_usage_updated_toast': {
        'fa': "✅ مصرف فایل به‌روزرسانی شد.",
        'en': "✅ File usage updated.",
    },
    'admin_user_quota_updated_toast': {
        'fa': "✅ سقف حجم روزانه به‌روزرسانی شد.",
        'en': "✅ Daily quota updated.",
    },
    'admin_user_monthly_quota_minus_btn': {
        'fa': "➖ 1GB سقف ماهانه",
        'en': "➖ 1GB Monthly",
    },
    'admin_user_monthly_quota_plus_btn': {
        'fa': "➕ 1GB سقف ماهانه",
        'en': "➕ 1GB Monthly",
    },
    'admin_user_monthly_quota_updated_toast': {
        'fa': "✅ سقف حجم ماهانه به‌روزرسانی شد.",
        'en': "✅ Monthly quota updated.",
    },
    'admin_user_enabled_toast': {
        'fa': "✅ کاربر فعال شد.",
        'en': "✅ User enabled.",
    },
    'admin_user_disabled_toast': {
        'fa': "⛔ کاربر غیرفعال شد.",
        'en': "⛔ User disabled.",
    },

    # ── Quota limit messages ──────────────────────────────────
    'quota_files_exceeded': {
        'fa': "❌ سقف روزانه فایل شما پر شده است.\n📥 دانلودها: {used}/{max}\nفردا دوباره امتحان کنید.",
        'en': "❌ Your daily file limit has been reached.\n📥 Downloads: {used}/{max}\nTry again tomorrow.",
    },
    'quota_bytes_exceeded': {
        'fa': "❌ حجم دانلود روزانه شما تمام شده است.\n💾 مصرف: {used}/{max}\nفردا دوباره امتحان کنید.",
        'en': "❌ Your daily data limit has been reached.\n💾 Used: {used}/{max}\nTry again tomorrow.",
    },
    'quota_monthly_files_exceeded': {
        'fa': "❌ سقف ماهانه فایل شما پر شده است.\n📥 دانلودها این ماه: {used}/{max}\nماه آینده دوباره امتحان کنید.",
        'en': "❌ Your monthly file limit has been reached.\n📥 Downloads this month: {used}/{max}\nTry again next month.",
    },
    'quota_monthly_bytes_exceeded': {
        'fa': "❌ حجم دانلود ماهانه شما تمام شده است.\n💾 مصرف این ماه: {used}/{max}\nماه آینده دوباره امتحان کنید.",
        'en': "❌ Your monthly data limit has been reached.\n💾 Used this month: {used}/{max}\nTry again next month.",
    },

    # ── Corrected Colab instructions ──────────────────────────
    'gdrive_colab_instructions': {
        'fa': (
            "برای اتصال درایو خود، نیازی به کامپیوتر ندارید!\n\n"
            "۱. روی لینک زیر کلیک کنید.\n"
            "۲. دکمه Play را بزنید و با اکانت گوگل خود لاگین کنید.\n"
            "۳. یک فایل به نام `rclone.conf` به شما داده میشود، آن را دانلود کنید.\n"
            "۴. فایل را همینجا برای من بفرستید.\n\n"
            "🔗 لینک اتصال: {colab_url}"
        ),
        'en': (
            "To connect your Drive, no computer is needed!\n\n"
            "1. Click the link below.\n"
            "2. Press Play and log in with your Google account.\n"
            "3. A file named `rclone.conf` will be given to you — download it.\n"
            "4. Send the file here.\n\n"
            "🔗 Connection link: {colab_url}"
        ),
    },

    # ── Google Drive multi-tenant ──────────────────────────────
    'btn_gdrive_connect': {
        'fa': "☁️ اتصال گوگل درایو",
        'en': "☁️ Connect Google Drive",
    },
    'btn_gdrive_connected': {
        'fa': "✅ درایو متصل است",
        'en': "✅ Drive Connected",
    },
    'gdrive_connect_title': {
        'fa': "☁️ اتصال گوگل درایو شخصی",
        'en': "☁️ Connect Your Google Drive",
    },
    'gdrive_connect_msg': {
        'fa': (
            "☁️ <b>اتصال گوگل درایو شخصی</b>\n\n"
            "با این قابلیت، تمام فایل‌های دانلودشده مستقیماً در <b>گوگل درایو خودتان</b> ذخیره می‌شوند."
            " نیازی به کامپیوتر ندارید — همه کارها از گوشی قابل انجام است.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📋 <b>مراحل اتصال:</b>\n\n"
            "0️⃣ (ضروری) یک بار در گوگل کلود یک OAuth Client ID شخصی بسازید:\n"
            "👉 https://console.cloud.google.com/apis/credentials\n"
            "• «Create OAuth client ID» → نوع: «Desktop app»\n"
            "• Client ID و Client Secret را کپی کنید و در اسکریپت Colab (بالای فایل) جای‌گذاری کنید.\n"
            "⚠️ بدون این کار، گوگل اتصال را بلاک می‌کند (client_id اشتراکی rclone از ۲۰۲۶ غیرفعال شد).\n\n"
            "1️⃣ لینک زیر را در مرورگر خود باز کنید:\n"
            "👉 <code>{colab_url}</code>\n\n"
            "2️⃣ روی ▶️ <b>Run</b> کلیک کنید و با حساب گوگل خود وارد شوید.\n\n"
            "3️⃣ اسکریپت به‌طور خودکار پوشه <b>TeleCloud-Downloads</b> را در درایو شما ایجاد می‌کند "
            "و فایل <code>rclone.conf</code> را برای دانلود آماده می‌کند.\n\n"
            "4️⃣ فایل <code>rclone.conf</code> دانلودشده را <b>همین‌جا به من بفرستید</b>.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🔒 <b>امنیت:</b> فایل config فقط روی سرور شما ذخیره می‌شود و به اشتراک گذاشته نمی‌شود.\n"
            "♻️ <b>توکن:</b> اعتبار اتصال نامحدود است و به‌صورت خودکار تمدید می‌شود."
        ),
        'en': (
            "☁️ <b>Connect Your Personal Google Drive</b>\n\n"
            "With this feature, all downloaded files are saved directly to <b>your own Google Drive</b>."
            " No computer needed — everything works from your phone.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📋 <b>Setup Steps:</b>\n\n"
            "0️⃣ (Required) Create your own OAuth Client ID in Google Cloud once:\n"
            "👉 https://console.cloud.google.com/apis/credentials\n"
            "• 'Create OAuth client ID' → Application type: 'Desktop app'\n"
            "• Copy the Client ID and Client Secret into the Colab script (top of file).\n"
            "⚠️ Without this, Google will block the connection (shared rclone client_id retired in 2026).\n\n"
            "1️⃣ Open the link below in your browser:\n"
            "👉 <code>{colab_url}</code>\n\n"
            "2️⃣ Click ▶️ <b>Run</b> and sign in with your Google account.\n\n"
            "3️⃣ The script will automatically create a <b>TeleCloud-Downloads</b> folder in your Drive "
            "and prepare the <code>rclone.conf</code> file for download.\n\n"
            "4️⃣ Send the downloaded <code>rclone.conf</code> file <b>back here</b>.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🔒 <b>Security:</b> The config file is stored only on your server and is never shared.\n"
            "♻️ <b>Token:</b> The connection credential is permanent and refreshes automatically."
        ),
    },
    'gdrive_status_connected': {
        'fa': (
            "✅ <b>گوگل درایو متصل است</b>\n\n"
            "📂 فایل‌های شما در پوشه <b>TeleCloud-Downloads</b> در درایو شما ذخیره می‌شوند.\n\n"
            "برای قطع اتصال و حذف کانفیگ، دکمه زیر را بزنید:"
        ),
        'en': (
            "✅ <b>Google Drive is connected</b>\n\n"
            "📂 Your files are saved to the <b>TeleCloud-Downloads</b> folder in your Drive.\n\n"
            "To disconnect and remove your config, press the button below:"
        ),
    },
    'btn_gdrive_disconnect': {
        'fa': "🔌 قطع اتصال درایو",
        'en': "🔌 Disconnect Drive",
    },
    'gdrive_disconnect_confirm': {
        'fa': (
            "⚠️ <b>آیا مطمئنید؟</b>\n\n"
            "با قطع اتصال، کانفیگ شخصی شما از سرور حذف می‌شود.\n"
            "فایل‌های قبلاً آپلودشده در درایو شما باقی می‌مانند.\n\n"
            "برای اتصال مجدد باید دوباره اسکریپت Colab را اجرا کنید."
        ),
        'en': (
            "⚠️ <b>Are you sure?</b>\n\n"
            "Disconnecting will remove your personal config from the server.\n"
            "Previously uploaded files in your Drive will remain intact.\n\n"
            "To reconnect, you will need to run the Colab script again."
        ),
    },
    'btn_gdrive_disconnect_confirm': {
        'fa': "✅ بله، قطع کن",
        'en': "✅ Yes, Disconnect",
    },
    'btn_gdrive_disconnect_cancel': {
        'fa': "❌ انصراف",
        'en': "❌ Cancel",
    },
    'gdrive_disconnected_toast': {
        'fa': "🔌 اتصال درایو قطع شد.",
        'en': "🔌 Drive disconnected.",
    },
    'gdrive_disconnected_msg': {
        'fa': "🔌 اتصال گوگل درایو قطع شد.\n\nبرای اتصال مجدد از منوی تنظیمات استفاده کنید.",
        'en': "🔌 Google Drive disconnected.\n\nUse the Settings menu to reconnect.",
    },

    # ── User profile dashboard ────────────────────────────────
    'btn_profile': {
        'fa': "👤 پروفایل من",
        'en': "👤 My Profile",
    },
    'profile_stats': {
        'fa': (
            "📊 آمار شما:\n\n"
            "📅 روزانه:\n"
            "📥 دانلودها: {files}/{max_files}\n"
            "💾 حجم: {used_gb:.2f}/{max_gb:.2f} GB\n\n"
            "📆 ماهانه:\n"
            "📥 دانلودها: {monthly_files}/{max_monthly_files}\n"
            "💾 حجم: {monthly_used_gb:.2f}/{monthly_max_gb:.2f} GB"
        ),
        'en': (
            "📊 Your stats:\n\n"
            "📅 Daily:\n"
            "📥 Downloads: {files}/{max_files}\n"
            "💾 Data used: {used_gb:.2f}/{max_gb:.2f} GB\n\n"
            "📆 Monthly:\n"
            "📥 Downloads: {monthly_files}/{max_monthly_files}\n"
            "💾 Data used: {monthly_used_gb:.2f}/{monthly_max_gb:.2f} GB"
        ),
    },
    'admin_profile_stats': {
        'fa': (
            "📊 آمار سیستم (ادمین)\n\n"
            "👥 کاربران تأیید‌شده: {total_approved}\n"
            "📥 کل دانلودها: {total_files}\n"
            "💾 کل حجم دانلود: {total_gb:.2f} GB"
        ),
        'en': (
            "📊 System Stats (Admin)\n\n"
            "👥 Approved users: {total_approved}\n"
            "📥 Total downloads: {total_files}\n"
            "💾 Total data downloaded: {total_gb:.2f} GB"
        ),
    },
    'btn_gdrive_connected_system': {
        'fa': "✅ درایو: پیش‌فرض سیستم",
        'en': "✅ Drive: System Default",
    },

    # ── SoundCloud Playlist ────────────────────────────────────
    'sc_fetching_playlist': {
        'fa': "⏳ در حال دریافت پلیلیست SoundCloud...",
        'en': "⏳ Fetching SoundCloud playlist...",
    },
    'sc_playlist_info': {
        'fa': "🎵 {title}\n📀 {count} آهنگ",
        'en': "🎵 {title}\n📀 {count} tracks",
    },
    'sc_playlist_audio_btn': {
        'fa': "🎵 دانلود آهنگها",
        'en': "🎵 Download Audio",
    },
    'sc_playlist_done': {
        'fa': "✅ تمام شد — {done}/{total} آهنگ دانلود شد",
        'en': "✅ Done — {done}/{total} tracks downloaded",
    },
    'sc_playlist_track_error': {
        'fa': "⚠️ آهنگ {n} با خطا مواجه شد: {error}",
        'en': "⚠️ Track {n} failed: {error}",
    },
    'sc_playlist_count_ask': {
        'fa': "🎵 {title}\nچند آهنگ دانلود کنم?",
        'en': "🎵 {title}\nHow many tracks to download?",
    },
    'sc_playlist_custom_ask': {
        'fa': "تعداد آهنگ‌های مورد نظر را وارد کنید (عدد):",
        'en': "Enter the number of tracks to download:",
    },
    'sc_playlist_queued': {
        'fa': "✅ به صف افزوده شد.\n🎵 {count} آهنگ | {dest_icon}",
        'en': "✅ Queued.\n🎵 {count} tracks | {dest_icon}",
    },
    'sc_playlist_dest_ask': {
        'fa': "🎵 {count} آهنگ\nمقصد:",
        'en': "🎵 {count} tracks\nDestination:",
    },
    'sc_playlist_fetch_error': {
        'fa': "❌ خطا در دریافت اطلاعات پلیلیست: {error}",
        'en': "❌ Failed to fetch playlist info: {error}",
    },
}




def t(cid, key: str, **kwargs) -> str:
    """
    Return the localized string for `key` in the user's language.
    Falls back to 'fa' if the key or language is not found.
    Extra kwargs are used for .format() substitutions.
    """
    lang = get_lang(cid)
    entry = STRINGS.get(key, {})
    text = entry.get(lang) or entry.get('fa') or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
