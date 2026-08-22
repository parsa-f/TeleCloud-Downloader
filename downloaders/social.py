import os
import glob
import time
from urllib.parse import urlparse
import yt_dlp

import db
from config import bot, DOWNLOAD_DIR, ADMIN_ID
from cookies import active_cookies_file
from utils import check_disk_space, get_free_space, cleanup_path, build_rich_progress_card, friendly_error, safe_tg_call
from uploaders.smart_dest import smart_dest
# _url_is_playlist is defined in handlers alongside the other social-link helpers.
# Import lazily inside the function to avoid a circular-import at module load time.

def _cancel_markup(cid=None):
    from telebot import types
    from locales import t
    m = types.InlineKeyboardMarkup()
    label = t(cid, 'cancel_btn') if cid else "❌ لغو"
    m.add(types.InlineKeyboardButton(label, callback_data="cancel_task"))
    return m

def _is_ytdlp_url(url: str) -> bool:
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'js_runtimes': {'node': {}}}) as ydl:
            for ie_cls in ydl._ies.values():
                try:
                    if ie_cls.suitable(url) and ie_cls.IE_NAME not in ('generic', 'Generic'):
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False

def ytdlp_universal(task):
    from locales import t
    from config import tg_upload_mode
    chat_id = task['chat_id']
    cid     = chat_id
    dest    = task.get('dest') or 'tg'
    url     = task['url']

    if not check_disk_space():
        bot.send_message(chat_id, t(cid, 'disk_no_space', free=get_free_space()))
        return

    audio_only    = task.get('audio_only', False) or task.get('format', '') == 'bestaudio/best'
    audio_codec   = task.get('audio_format', 'mp3')      # mp3 | m4a | flac | default
    audio_quality = task.get('audio_quality', 'default')  # 320 | 128 | default
    video_fmt     = task.get('video_format', 'mp4')       # mp4 | mkv | default
    embed_chapters = task.get('chapters', False)

    domain        = urlparse(url).netloc.replace('www.', '').split('.')[0].capitalize()
    quality_label = f"🎵 {audio_codec.upper() if audio_codec != 'default' else 'MP3'}" if audio_only else 'video'

    msg      = bot.send_message(chat_id, t(cid, 'social_preparing', domain=domain), reply_markup=_cancel_markup(cid))
    task['_msg_id'] = msg.message_id  # lets cancel_task find this task by its progress message
    last_upd = [time.time()]

    def hook(d):
        if task['_stop'].is_set(): raise Exception(t(cid, 'social_cancelled'))
        if d['status'] == 'downloading' and time.time() - last_upd[0] > 3:
            pct   = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            speed = d.get('speed', 0) or 0
            eta   = d.get('eta', 0) or 0
            pct_f = pct / total * 100 if total else 0
            actual_title = d.get('info_dict', {}).get('title', f"{domain} Media")
            task['actual_title'] = actual_title
            card = build_rich_progress_card("⬇️", actual_title, pct_f, pct, total, speed, eta, domain, quality_label, cid=cid)
            try: safe_tg_call(bot.edit_message_text, card, chat_id, msg.message_id, reply_markup=_cancel_markup(cid))
            except Exception: pass
            last_upd[0] = time.time()

    folder = os.path.join(DOWNLOAD_DIR, domain)
    os.makedirs(folder, exist_ok=True)
    task['_active_path'] = folder
    cf = active_cookies_file(url, cid)

    # ── Build postprocessors dynamically ──────────────────────
    postprocessors = []
    if audio_only:
        # Task 3: Always extract audio via FFmpeg (never raw stream)
        pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': audio_codec if audio_codec != 'default' else 'mp3'}
        if audio_quality != 'default':
            pp['preferredquality'] = audio_quality
        postprocessors.append(pp)
        # Embed thumbnail as album art in the audio file
        postprocessors.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})

    if embed_chapters and not audio_only:
        postprocessors.append({'key': 'FFmpegMetadata', 'add_chapters': True})

    merge_fmt = video_fmt if video_fmt != 'default' else 'mp4'

    # Bug 4a fix: import lazily to avoid a circular-import at module load time
    # (social.py is imported by handlers.py, so a top-level import would create a cycle).
    from handlers import _url_is_playlist
    _noplaylist = _url_is_playlist(url)

    ydl_opts = {
        'format':              task.get('format', 'bestvideo+bestaudio/best'),
        'outtmpl':             os.path.join(folder, '%(title)s.%(ext)s'),
        'merge_output_format': merge_fmt,
        'progress_hooks':      [hook],
        'quiet':               True,
        'no_warnings':         True,
        'js_runtimes':         {'node': {}},
        'windowsfilenames':    True,
        # Bug 4a: False for SoundCloud /sets/ so the whole album downloads,
        # True for single-item URLs (the safe default for all other platforms).
        'noplaylist':          _noplaylist,
        'nocheckcertificate':  True,
        'format_sort':         ['res', 'ext:mp4:m4a'],
        'postprocessors':      postprocessors,
        'writethumbnail':      audio_only,  # download thumbnail for audio cover art
        'http_headers': {
            'User-Agent':      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept':          'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },
        'extractor_args': {
            'twitter': {'api': ['graphql']},
        },
    }
    if embed_chapters and not audio_only:
        ydl_opts['embedchapters'] = True
    if cf: ydl_opts['cookiefile'] = cf


    fp = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info      = ydl.extract_info(url, download=True)
            expected  = ydl.prepare_filename(info)
            base      = os.path.splitext(expected)[0]
            candidates = glob.glob(base + '.*')
            fp        = max(candidates, key=os.path.getmtime) if candidates else None
            if not fp:
                files = sorted(glob.glob(os.path.join(folder, '*')), key=os.path.getmtime)
                fp    = files[-1] if files else None
            if not fp: raise Exception(t(cid, 'file_not_found_err'))

        try: safe_tg_call(bot.edit_message_text, t(cid, 'social_upload_preparing'), chat_id, msg.message_id)
        except Exception: pass

        # ── Byte quota accounting ──────────────────────────────
        real_size = os.path.getsize(fp) if os.path.isfile(fp) else 0
        db.record_download_bytes(cid, real_size)

        # ── ID3 metadata fix for audio downloads ──────────────
        if audio_only and fp and fp.endswith('.mp3'):
            raw_title = info.get('title', '')

            # Try yt-dlp's dedicated fields first (YouTube Music provides these)
            track_title  = (info.get('track')
                            or info.get('alt_title')
                            or '')
            track_artist = (info.get('artist')
                            or info.get('creator')
                            or '')

            # Fallback: parse "Artist - Title" from the raw title string
            if not track_title and ' - ' in raw_title:
                parts        = raw_title.split(' - ', 1)
                track_artist = track_artist or parts[0].strip()
                track_title  = parts[1].strip()
            elif not track_title:
                track_title = raw_title

            # Final fallback for artist
            if not track_artist:
                track_artist = (info.get('uploader')
                                or info.get('channel')
                                or 'Unknown')

            album = info.get('album', '') or ''
            year  = str(info.get('release_year') or info.get('upload_date', '')[:4] or '')

            try:
                from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, APIC, ID3NoHeaderError
                try:
                    tags = ID3(fp)
                except ID3NoHeaderError:
                    tags = ID3()
                tags['TIT2'] = TIT2(encoding=3, text=track_title)
                tags['TPE1'] = TPE1(encoding=3, text=track_artist)
                if album:
                    tags['TALB'] = TALB(encoding=3, text=album)
                if year and year.isdigit() and year != '0':
                    tags['TDRC'] = TDRC(encoding=3, text=year)

                # Embed cover art - search for thumbnail file yt-dlp downloaded
                thumb_base = os.path.splitext(fp)[0]
                for ext in ('.jpg', '.jpeg', '.png', '.webp'):
                    thumb_path = thumb_base + ext
                    if os.path.isfile(thumb_path):
                        mime = 'image/jpeg' if ext in ('.jpg', '.jpeg') else f'image/{ext[1:]}'
                        with open(thumb_path, 'rb') as img:
                            tags['APIC'] = APIC(
                                encoding=3, mime=mime, type=3,
                                desc='Cover', data=img.read())
                        break

                tags.save(fp)
            except Exception:
                pass

            final_title = track_title
            final_artist = track_artist
        else:
            final_title = task.get('actual_title', f"{domain} Media")
            final_artist = None

        task_info = {
            'title': final_title,
            'artist': final_artist,
            'source': domain,
            'quality': quality_label,
            '_stop': task.get('_stop'),
            'user_id': cid,
        }

        smart_dest(fp, msg, dest, folder_name=None, task_info=task_info)
        cleanup_path(folder)

    except Exception as e:
        if fp: cleanup_path(fp)
        cleanup_path(folder)
        err = str(e)
        cancel_kw = t(cid, 'social_cancelled')
        if cancel_kw in err or t(cid, 'cancelled_keyword') in err:
            try: safe_tg_call(bot.edit_message_text, t(cid, 'download_cancelled'), chat_id, msg.message_id)
            except Exception: pass
        else:
            text = f"❌ {friendly_error(err, cid=cid)}"
            try: safe_tg_call(bot.edit_message_text, text, chat_id, msg.message_id)
            except Exception: safe_tg_call(bot.send_message, chat_id, text)


def process_soundcloud_playlist(task):
    """Download a SoundCloud playlist one track at a time.

    Each track is downloaded, uploaded, and cleaned up before the next one
    begins, so disk usage stays bounded to a single track at any moment.
    """
    from locales import t
    import re
    import logging

    logger = logging.getLogger(__name__)

    chat_id = task['chat_id']
    cid     = chat_id
    url     = task['url']
    count   = task.get('count', 'all')
    dest    = task.get('dest', 'tg')
    audio_codec   = task.get('audio_format', 'mp3')
    audio_quality = task.get('audio_quality', 'default')

    # ── 1. Fetch playlist entries with extract_flat ───────────
    cf = active_cookies_file(url, cid)
    fetch_opts = {'extract_flat': True, 'quiet': True}
    if cf:
        fetch_opts['cookiefile'] = cf

    msg = bot.send_message(chat_id, t(cid, 'sc_fetching_playlist'),
                           reply_markup=_cancel_markup(cid))
    task['_msg_id'] = msg.message_id

    try:
        with yt_dlp.YoutubeDL(fetch_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        entries  = list(info.get('entries', []))
        pl_title = info.get('title', 'SoundCloud Playlist')
    except Exception as e:
        logger.error("SoundCloud playlist fetch failed: %s", e, exc_info=True)
        try:
            safe_tg_call(bot.edit_message_text,
                f"❌ {friendly_error(str(e), cid=cid)}", chat_id, msg.message_id)
        except Exception:
            pass
        return

    # ── 2. Slice to 'count' entries ──────────────────────────
    if count != 'all':
        entries = entries[:int(count)]
    total = len(entries)

    safe_title = re.sub(r'[\\/*?:"<>|]', '_', pl_title)[:40]
    done   = 0
    errors = 0

    # ── 3. Download each track one at a time ─────────────────
    for idx, entry in enumerate(entries, 1):
        # Check cancellation before starting each track
        if task['_stop'].is_set():
            break

        if not check_disk_space():
            bot.send_message(chat_id, t(cid, 'disk_no_space', free=get_free_space()))
            break

        entry_url = entry.get('url') or entry.get('webpage_url', '')
        if not entry_url:
            errors += 1
            done   += 1
            continue

        folder = os.path.join(DOWNLOAD_DIR, f"sc_{safe_title}_{idx}")
        os.makedirs(folder, exist_ok=True)
        task['_active_path'] = folder

        # Build per-track yt-dlp options (audio only)
        postprocessors = []
        pp = {'key': 'FFmpegExtractAudio',
              'preferredcodec': audio_codec if audio_codec != 'default' else 'mp3'}
        if audio_quality != 'default':
            pp['preferredquality'] = audio_quality
        postprocessors.append(pp)
        # Bug 2 fix: add FFmpegMetadata to write correct ID3 artist/title tags
        postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})
        postprocessors.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})

        ydl_opts = {
            'format':              'bestaudio/best',
            'outtmpl':             os.path.join(folder, '%(title)s.%(ext)s'),
            'quiet':               True,
            'no_warnings':         True,
            'windowsfilenames':    True,
            'noplaylist':          True,
            'addmetadata':         True,
            'postprocessors':      postprocessors,
            'writethumbnail':      True,
        }
        if cf:
            ydl_opts['cookiefile'] = cf

        fp = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                dl_info    = ydl.extract_info(entry_url, download=True)
                expected   = ydl.prepare_filename(dl_info)
                base       = os.path.splitext(expected)[0]
                candidates = glob.glob(base + '.*')
                fp         = max(candidates, key=os.path.getmtime) if candidates else None

            if fp and not task['_stop'].is_set():
                # Byte quota accounting
                real_size = os.path.getsize(fp) if os.path.isfile(fp) else 0
                db.record_download_bytes(cid, real_size)

                # Parse artist/title from the raw title string.
                # SoundCloud doesn't provide a separate 'artist' field —
                # the title contains the full "Artist - Title" string.
                raw_title = dl_info.get('title', '')
                uploader  = dl_info.get('uploader', '') or dl_info.get('creator', '')

                if ' - ' in raw_title:
                    parts = raw_title.split(' - ', 1)
                    track_artist = parts[0].strip()
                    track_title  = parts[1].strip()
                else:
                    track_artist = uploader or 'Unknown'
                    track_title  = raw_title or os.path.basename(fp)

                # Write correct ID3 tags using mutagen (already in requirements)
                try:
                    from mutagen.id3 import ID3, TIT2, TPE1, ID3NoHeaderError
                    try:
                        audio = ID3(fp)
                    except ID3NoHeaderError:
                        audio = ID3()
                    audio['TIT2'] = TIT2(encoding=3, text=track_title)
                    audio['TPE1'] = TPE1(encoding=3, text=track_artist)
                    audio.save(fp)
                except Exception as meta_err:
                    logger.warning("Could not write ID3 tags to %s: %s", fp, meta_err)

                # Send a NEW per-track message (like YouTube playlist)
                display_name = f"{track_artist} - {track_title}" if track_artist not in ('Unknown', '') else track_title
                sub = bot.send_message(
                    chat_id,
                    t(cid, 'uploading_item',
                      idx=idx, total=total,
                      name=display_name))

                task_info = {
                    'title':   track_title,
                    'artist':  track_artist,
                    'source':  'SoundCloud',
                    'quality': '🎵 Audio',
                    '_stop':   task.get('_stop'),
                    'user_id': cid,
                }
                # Pass the per-track sub message (not the shared progress msg)
                smart_dest(fp, sub, dest, folder_name=safe_title, task_info=task_info)
                done += 1
            else:
                done += 1

        except Exception as e:
            logger.error(
                "SoundCloud track %d/%d failed (url=%s): %s",
                idx, total, entry_url, e, exc_info=True,
            )
            if fp:
                cleanup_path(fp)
            errors += 1
            done   += 1
            try:
                safe_tg_call(bot.send_message, chat_id,
                    t(cid, 'sc_playlist_track_error', n=idx, error=friendly_error(str(e), cid=cid)))
            except Exception:
                pass

        # Always clean up the per-track folder
        cleanup_path(folder)

        # Update the progress message (throttled to only on the last track
        # or when meaningful progress is made)
        if done == total or done % 3 == 0:
            try:
                from utils import make_progress_bar
                bar = make_progress_bar(done / total * 100)
                safe_tg_call(
                    bot.edit_message_text,
                    f"📋 {pl_title}\n{bar} {done}/{total}\n"
                    f"✅ {done - errors}  ❌ {errors}",
                    chat_id, msg.message_id, reply_markup=_cancel_markup(cid))
            except Exception:
                pass

    # ── 4. Final summary message ─────────────────────────────
    try:
        safe_tg_call(
            bot.edit_message_text,
            t(cid, 'sc_playlist_done', done=done - errors, total=total),
            chat_id, msg.message_id)
    except Exception:
        pass
