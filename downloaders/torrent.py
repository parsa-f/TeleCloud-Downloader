import os
import re
import time
import subprocess

from config import bot, cache_lock, url_cache, DOWNLOAD_DIR
from config import ADMIN_ID
import db
from utils import fmt_size, build_rich_progress_card, cleanup_path, friendly_error, safe_tg_call
from uploaders.smart_dest import smart_dest


def _cancel_markup(cid=None):
    from telebot import types
    from locales import t
    m = types.InlineKeyboardMarkup()
    label = t(cid, 'cancel_btn') if cid else "❌ لغو"
    m.add(types.InlineKeyboardButton(label, callback_data="cancel_task"))
    return m


def check_torrent_health(magnet_url: str) -> dict:
    result = {"seeders": -1, "leechers": -1, "size": 0}
    try:
        cmd  = ["aria2c", "--bt-metadata-only=true", "--bt-save-metadata=false",
                "--seed-time=0", "--console-log-level=notice",
                "--summary-interval=3", "--bt-max-peers=80",
                "--enable-dht=true", "--disable-ipv6=true",
                "--timeout=20", "--max-tries=1", magnet_url]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1)
        deadline = time.time() + 20
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                break
            m_sd = re.search(r'Seeder:(\d+)',  line, re.I)
            m_lc = re.search(r'Leecher:(\d+)', line, re.I)
            m_sz = re.search(r'Total Length[:\s]+([\d.]+)\s*(GiB|MiB|KiB|B)', line)
            if m_sd:
                result["seeders"]  = int(m_sd.group(1))
            if m_lc:
                result["leechers"] = int(m_lc.group(1))
            if m_sz:
                val, unit = float(m_sz.group(1)), m_sz.group(2)
                result["size"] = int(val * {"GiB": 1024**3, "MiB": 1024**2, "KiB": 1024, "B": 1}[unit])
            if result["seeders"] >= 0:
                break
        proc.terminate()
    except Exception:
        pass
    return result


def process_torrent_download(task):
    from locales import t
    chat_id = task['chat_id']
    cid     = chat_id
    from utils import check_disk_space, get_free_space
    if not check_disk_space():
        bot.send_message(chat_id, t(cid, 'disk_no_space', free=get_free_space()))
        return

    msg    = bot.send_message(chat_id, t(cid, 'torrent_checking'), reply_markup=_cancel_markup(cid))
    task['_msg_id'] = msg.message_id  # lets cancel_task find this task by its progress message
    health = check_torrent_health(task['url'])
    sd, lc = health["seeders"], health["leechers"]
    sz_str = fmt_size(health["size"]) if health["size"] else t(cid, 'torrent_size_unknown')

    if sd >= 0:
        if sd == 0:
            verdict = t(cid, 'torrent_verdict_none')
        elif sd < 5:
            verdict = t(cid, 'torrent_verdict_slow', sd=sd)
        else:
            verdict = t(cid, 'torrent_verdict_ok', sd=sd)
        from telebot import types
        confirm_mk = types.InlineKeyboardMarkup()
        confirm_mk.row(
            types.InlineKeyboardButton(t(cid, 'torrent_btn_download'), callback_data=f"trc|yes|{msg.message_id}"),
            types.InlineKeyboardButton(t(cid, 'torrent_btn_cancel'),   callback_data=f"trc|no|{msg.message_id}")
        )
        try:
            safe_tg_call(
                bot.edit_message_text,
                t(cid, 'torrent_confirm_msg', size=sz_str, sd=sd, lc=lc, verdict=verdict),
                chat_id, msg.message_id, reply_markup=confirm_mk)
        except Exception:
            pass
        with cache_lock:
            url_cache[('torrent_confirm', msg.message_id)] = task
        return

    _do_torrent_download(task, msg)


def _do_torrent_download(task, msg):
    from locales import t
    from config import tg_upload_mode
    chat_id = task['chat_id']
    cid     = chat_id
    dest    = task.get('dest') or 'tg'
    TIMEOUT = 20 * 60
    task['_active_path'] = None
    session_dir = os.path.join(DOWNLOAD_DIR, f".torrent_{chat_id}_{int(time.time())}_{os.getpid()}")
    os.makedirs(session_dir, exist_ok=True)
    task['_active_path'] = session_dir

    cmd = [
        "aria2c", "--dir", session_dir, "--seed-time=0",
        "--console-log-level=notice", "--summary-interval=5",
        "--bt-enable-lpd=true", "--enable-dht=true",
        "--enable-dht6=false", "--disable-ipv6=true",
        "--dht-listen-port=6881", "--listen-port=6881-6885",
        "--bt-tracker-connect-timeout=30", "--bt-tracker-timeout=60",
        "--max-connection-per-server=4", "--bt-max-peers=100",
        "--allow-overwrite=true", "--auto-file-renaming=false",
        "--follow-torrent=mem", "--timeout=60",
        "--retry-wait=5", "--max-tries=5", task['url']
    ]

    try:
        process            = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT, text=True, bufsize=1)
        last_update        = time.time()
        last_progress_time = time.time()
        last_percent       = -1
        output_lines       = []
        pi                 = {"percent": 0.0, "speed": 0.0, "peers": 0, "eta": 0,
                              "dl_bytes": 0, "total_bytes": 0}

        while True:
            if task['_stop'].is_set():
                process.terminate()
                try:
                    safe_tg_call(bot.edit_message_text, t(cid, 'torrent_cancel_cb'), chat_id, msg.message_id)
                except Exception:
                    pass
                return

            if time.time() - last_progress_time > TIMEOUT:
                process.terminate()
                try:
                    safe_tg_call(bot.edit_message_text, t(cid, 'torrent_timeout'), chat_id, msg.message_id)
                except Exception:
                    pass
                return

            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.strip()
                output_lines.append(line)
                m_pct  = re.search(r'\((\d+)%\)',     line)
                m_spd  = re.search(r'DL:([^\s\]]+)',  line)
                m_eta  = re.search(r'ETA:([^\]]+)',   line)
                m_peer = re.search(r'CN:(\d+)',        line)
                m_size = re.search(r'SIZE:([^\s/]+)/([^\s\]]+)', line)
                if m_pct:
                    new_pct = float(m_pct.group(1))
                    if new_pct > last_percent:
                        last_percent       = new_pct
                        last_progress_time = time.time()
                    pi["percent"] = new_pct
                if m_spd:
                    raw = m_spd.group(1).upper()
                    mul = 1024 * 1024 if 'M' in raw else 1024 if 'K' in raw else 1
                    spd = float(re.sub(r'[^\d.]', '', raw) or 0) * mul
                    if spd > 0:
                        last_progress_time = time.time()
                    pi["speed"] = spd
                if m_eta:
                    e  = m_eta.group(1).strip()
                    mm = re.search(r'(\d+)m', e)
                    ss = re.search(r'(\d+)s', e)
                    pi["eta"] = int(mm.group(1) if mm else 0) * 60 + int(ss.group(1) if ss else 0)
                if m_peer:
                    pi["peers"] = int(m_peer.group(1))
                if m_size:
                    def parse_sz(s):
                        s   = s.upper()
                        mul = 1024**3 if 'G' in s else 1024**2 if 'M' in s else 1024 if 'K' in s else 1
                        return float(re.sub(r'[^\d.]', '', s) or 0) * mul
                    pi["dl_bytes"]    = int(parse_sz(m_size.group(1)))
                    pi["total_bytes"] = int(parse_sz(m_size.group(2)))

                if time.time() - last_update > 4:
                    no_prog_sec  = int(time.time() - last_progress_time)
                    timeout_warn = (
                        t(cid, 'torrent_no_progress_warn',
                          m=no_prog_sec // 60, s=no_prog_sec % 60)
                        if no_prog_sec > 60 else ""
                    )
                    source_label = f"Torrent ({pi['peers']} Peers)"
                    card = build_rich_progress_card(
                        "🧲", t(cid, 'torrent_downloading'),
                        pi["percent"], pi["dl_bytes"], pi["total_bytes"],
                        pi["speed"], pi["eta"], source_label, "", cid=cid)
                    if timeout_warn:
                        card += timeout_warn
                    try:
                        safe_tg_call(
                            bot.edit_message_text, card, chat_id, msg.message_id,
                            reply_markup=_cancel_markup(cid))
                    except Exception:
                        pass
                    last_update = time.time()

        if process.wait() != 0:
            relevant = [l for l in output_lines if any(
                k in l for k in ['ERROR', 'error', 'Cannot', 'failed', 'timeout'])]
            raise Exception("aria2c error:\n" + "\n".join((relevant or output_lines)[-8:]))

        entries = sorted(
            [os.path.join(session_dir, e) for e in os.listdir(session_dir)
             if not e.endswith('.aria2')],
            key=os.path.getmtime, reverse=True)
        if not entries:
            raise Exception(t(cid, 'torrent_file_not_found'))

        newest = entries[0] if len(entries) == 1 else session_dir
        task['_active_path'] = newest
        display_name = os.path.basename(newest.rstrip(os.sep)) or 'Torrent'
        if newest == session_dir and len(entries) > 1:
            display_name = 'Torrent'
        base_name = os.path.splitext(display_name)[0][:40]
        is_folder = os.path.isdir(newest)

        if is_folder:
            real_size = 0
            for root, _, files in os.walk(newest):
                for name in files:
                    fpath = os.path.join(root, name)
                    if os.path.isfile(fpath):
                        real_size += os.path.getsize(fpath)
        else:
            real_size = os.path.getsize(newest) if os.path.isfile(newest) else 0
        db.record_download_bytes(cid, real_size)

        try:
            safe_tg_call(bot.edit_message_text, t(cid, 'torrent_preparing_upload'), chat_id, msg.message_id)
        except Exception:
            pass

        task_info = {
            'title':   os.path.basename(newest),
            'source':  'Torrent',
            'quality': '',
            'user_id': chat_id,
            '_stop': task.get('_stop'),
        }

        if is_folder:
            from uploaders.gdrive_upload import upload_to_gdrive_cancellable
            upload_to_gdrive_cancellable(
                newest, msg,
                folder_name=base_name,
                is_folder=True,
                task_info=task_info,
                user_id=chat_id,
            )
        else:
            smart_dest(newest, msg, dest, folder_name=base_name, task_info=task_info)

        try:
            if os.path.isdir(session_dir) and not os.listdir(session_dir):
                cleanup_path(session_dir)
        except Exception:
            pass

    except Exception as e:
        err = str(e)
        cancel_kw = t(cid, 'cancelled_keyword')
        if cancel_kw not in err and "timeout" not in err:
            text = f"❌ {friendly_error(err, cid=cid)}"
            try:
                safe_tg_call(bot.edit_message_text, text, chat_id, msg.message_id)
            except Exception:
                safe_tg_call(bot.send_message, chat_id, text)
