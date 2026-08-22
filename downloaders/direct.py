import os
import re
import time
import requests
from urllib.parse import urlparse

import db
from config import bot, DOWNLOAD_DIR, ADMIN_ID
from utils import (check_disk_space, get_free_space, cleanup_path,
                   build_rich_progress_card, friendly_error, safe_tg_call)
from uploaders.smart_dest import smart_dest


def _cancel_markup(cid=None):
    from telebot import types
    from locales import t
    m = types.InlineKeyboardMarkup()
    label = t(cid, 'cancel_btn') if cid else "❌ لغو"
    m.add(types.InlineKeyboardButton(label, callback_data="cancel_task"))
    return m


def resolve_direct_url(url: str) -> tuple:
    """Resolve the URL — supports GitHub and F-Droid."""
    gh = re.match(r'https?://github\.com/([^/]+)/([^/]+)/releases(?:/tag/([^/]+))?/?$', url)
    if gh:
        owner, repo, tag = gh.group(1), gh.group(2), gh.group(3)
        api = f"https://api.github.com/repos/{owner}/{repo}/releases/{'tags/'+tag if tag else 'latest'}"
        try:
            data   = requests.get(api, timeout=15).json()
            assets = data.get('assets', [])
            if assets:
                return assets[0]['browser_download_url'], assets[0]['name']
        except Exception:
            pass

    fd = re.match(r'https?://f-droid\.org/(?:en/)?packages/([^/]+)/?', url)
    if fd:
        pkg = fd.group(1)
        try:
            data    = requests.get(f"https://f-droid.org/api/v1/packages/{pkg}", timeout=15).json()
            version = data['suggestedVersionCode']
            return f"https://f-droid.org/repo/{pkg}_{version}.apk", f"{pkg}_{version}.apk"
        except Exception:
            pass

    filename = os.path.basename(urlparse(url).path) or "downloaded_file"
    return url, filename


def process_direct_download(task):
    from locales import t
    from config import tg_upload_mode
    chat_id = task['chat_id']
    cid     = chat_id
    dest    = task.get('dest') or 'tg'

    if not check_disk_space():
        bot.send_message(chat_id, t(cid, 'disk_no_space', free=get_free_space()))
        return

    url = task['url']
    msg = bot.send_message(chat_id, t(cid, 'direct_preparing'), reply_markup=_cancel_markup(cid))
    task['_msg_id'] = msg.message_id  # lets cancel_task find this task by its progress message
    fp  = None

    try:
        real_url, filename = resolve_direct_url(url)
        fp         = os.path.join(DOWNLOAD_DIR, filename)
        task['_active_path'] = fp
        start_time = time.time()

        with requests.get(real_url, stream=True, timeout=60,
                          headers={'User-Agent': 'Mozilla/5.0'}) as r:
            r.raise_for_status()
            total      = int(r.headers.get('content-length', 0))
            downloaded = 0
            last_upd   = time.time()
            with open(fp, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if task['_stop'].is_set():
                        raise Exception(t(cid, 'cancelled_keyword'))
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        if now - last_upd > 3 and total > 0:
                            elapsed = now - start_time
                            speed   = downloaded / elapsed if elapsed > 0 else 0
                            eta     = int((total - downloaded) / speed) if speed > 0 else 0
                            pct     = downloaded / total * 100
                            card = build_rich_progress_card(
                                "⬇️", filename, pct, downloaded, total, speed, eta,
                                "Direct Link", "", cid=cid)
                            try:
                                safe_tg_call(bot.edit_message_text, card, chat_id, msg.message_id, reply_markup=_cancel_markup(cid))
                            except Exception:
                                pass
                            last_upd = now

        folder_name = os.path.splitext(filename)[0][:40]

        try:
            safe_tg_call(bot.edit_message_text, t(cid, 'direct_upload_preparing'), chat_id, msg.message_id)
        except Exception:
            pass

        # ── Byte quota accounting ──────────────────────────────
        real_size = os.path.getsize(fp) if os.path.isfile(fp) else 0
        db.record_download_bytes(cid, real_size)

        task_info = {
            'title': filename,
            'source': 'Direct Link',
            'quality': '',
            '_stop': task.get('_stop'),
            'user_id': cid,
        }
        smart_dest(fp, msg, dest, folder_name=folder_name, task_info=task_info)

    except Exception as e:
        if fp:
            cleanup_path(fp)
        err = str(e)
        cancel_kw = t(cid, 'cancelled_keyword') if cid else "لغو"
        if cancel_kw in err:
            try:
                safe_tg_call(bot.edit_message_text, t(cid, 'download_cancelled'), chat_id, msg.message_id)
            except Exception:
                pass
        else:
            text = f"❌ {friendly_error(err, cid=cid)}"
            try:
                safe_tg_call(bot.edit_message_text, text, chat_id, msg.message_id)
            except Exception:
                safe_tg_call(bot.send_message, chat_id, text)
