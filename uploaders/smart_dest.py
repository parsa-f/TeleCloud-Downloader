import os
from config import bot
from utils import get_file_size, fmt_size


def smart_dest(file_path: str, status_msg, dest: str = None, folder_name: str = None, task_info: dict = None):
    """
    Send the file to the correct destination.
    dest='tg'      → Telegram (auto-redirects to Drive if size > 2GB)
    dest='gd'      → Google Drive (per-user rclone config)
    dest='s3'      → Railway Bucket (S3-compatible), public link
    dest='github'  → user's own GitHub repo (per-user token), raw link
    dest=None      → reads from user's upload toggle (tg_upload_mode set,
                     otherwise per-user db.upload_dest, fallback to Drive)
    """
    from locales import t
    from config import tg_upload_mode
    from uploaders.telegram_upload import upload_file_to_telegram
    from uploaders.gdrive_upload import upload_to_gdrive_cancellable
    from uploaders.s3_upload import upload_to_s3
    from uploaders.github_upload import upload_to_github

    chat_id = status_msg.chat.id
    cid     = chat_id
    if task_info is None:
        task_info = {}

    if dest is None:
        import db
        try:
            d = db.get_upload_dest(cid)
            dest = d if d in ('s3', 'github', 'gd') else 'gd'
        except Exception:
            dest = 'tg'

    size = get_file_size(file_path)

    # Local Bot API allows up to 2GB; if a single file is larger, redirect to Drive.
    if size > 2000 * 1024 * 1024 and dest == 'tg':
        try:
            bot.edit_message_text(
                t(cid, 'smart_dest_large', size=fmt_size(size)),
                chat_id, status_msg.message_id
            )
        except Exception:
            pass
        dest = 'gd'

    if dest == 'tg':
        upload_file_to_telegram(file_path, status_msg, task_info)
    elif dest == 's3':
        url = upload_to_s3(file_path, chat_id, status_msg)
        _reply_link(status_msg, url, "S3/Railway", cid)
    elif dest == 'github':
        url = upload_to_github(file_path, chat_id, status_msg)
        _reply_link(status_msg, url, "GitHub", cid)
    else:
        # gdrive — if the user never connected Drive, say so clearly instead
        # of a raw rclone traceback.
        from pathlib import Path
        from config import USER_CONFIGS_DIR
        if not Path(USER_CONFIGS_DIR, f"rclone_{cid}.conf").exists():
            try:
                bot.edit_message_text(
                    "☁️ برای آپلود به Google Drive اول باید وصلش کنی:\n"
                    "تنظیمات → ☁️ اتصال گوگل درایو\n\n"
                    "یا مقصد دیگه‌ای (S3 / GitHub / تلگرام) انتخاب کن.",
                    cid, status_msg.message_id)
            except Exception:
                pass
            return
        upload_to_gdrive_cancellable(file_path, status_msg, folder_name, False, task_info)


def _reply_link(status_msg, url: str | None, label: str, cid: int):
    from locales import t
    if url:
        try:
            bot.edit_message_text(
                f"{label} link:\n{url}",
                cid, status_msg.message_id
            )
        except Exception:
            pass
    else:
        try:
            bot.edit_message_text(
                t(cid, 'upload_failed_toast'),
                cid, status_msg.message_id
            )
        except Exception:
            pass
