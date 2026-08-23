import config
from locales import t

# =============================================================
# Video quality cycle (expanded with 4K / 2K)
# =============================================================
VIDEO_QUALITY_CYCLE = ['manual', 'best', '2160', '1440', '1080', '720', '480']

_VIDEO_QUALITY_LOCALE = {
    'manual': 'quality_manual',
    'best':   'quality_best',
    '2160':   'quality_2160',
    '1440':   'quality_1440',
    '1080':   'quality_1080',
    '720':    'quality_720',
    '480':    'quality_480',
}

# yt-dlp format strings for each video quality key
VIDEO_FMT_MAP = {
    '2160': 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best',
    '1440': 'bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1440]+bestaudio/best',
    '1080': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best',
    '720':  'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best',
    '480':  'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best',
    'best': 'bestvideo+bestaudio/best',
}

# =============================================================
# Audio quality cycle
# =============================================================
AUDIO_QUALITY_CYCLE = ['320', '128', 'default']

_AUDIO_QUALITY_LOCALE = {
    '320':     'audio_quality_320',
    '128':     'audio_quality_128',
    'default': 'audio_quality_default',
}

# =============================================================
# Video format (container) cycle
# =============================================================
VIDEO_FORMAT_CYCLE = ['mp4', 'mkv', 'default']

_VIDEO_FORMAT_LOCALE = {
    'mp4':     'format_mp4',
    'mkv':     'format_mkv',
    'default': 'format_default',
}

# =============================================================
# Audio format (codec) cycle
# =============================================================
AUDIO_FORMAT_CYCLE = ['mp3', 'm4a', 'flac', 'default']

_AUDIO_FORMAT_LOCALE = {
    'mp3':     'format_mp3',
    'm4a':     'format_m4a',
    'flac':    'format_flac',
    'default': 'format_default',
}

# =============================================================
# Subtitle cycle
# =============================================================
SUBTITLE_CYCLE = ['en', 'fa', 'off']

_SUBTITLE_LOCALE = {
    'en':  'btn_subtitle_en',
    'fa':  'btn_subtitle_fa',
    'off': 'btn_subtitle_off',
}

# =============================================================
# Destination helpers
# =============================================================

def get_dest(cid) -> str:
    """Return the user's default upload destination (persisted in Postgres)."""
    import db
    try:
        d = db.get_upload_dest(cid)
        return d
    except Exception:
        # fallback: admin defaults to tg, others to gd (original behaviour)
        from config import ADMIN_ID
        return 'tg' if cid == ADMIN_ID else 'gd'


def should_ask_dest(cid) -> bool:
    """Return True if the user has never explicitly chosen a destination."""
    import db
    try:
        row = db.get_user(cid)
        return not (row and row["upload_dest"])  # NULL/absent = ask per file
    except Exception:
        return True


# =============================================================
# Video quality helpers
# =============================================================

def get_quality(cid) -> str:
    """Return the user's current video quality key. Default: 'manual'."""
    return config.user_quality.get(cid, 'manual')


def cycle_quality(cid) -> str:
    """Advance video quality to the next step and return the new value."""
    current = get_quality(cid)
    idx     = VIDEO_QUALITY_CYCLE.index(current) if current in VIDEO_QUALITY_CYCLE else 0
    next_q  = VIDEO_QUALITY_CYCLE[(idx + 1) % len(VIDEO_QUALITY_CYCLE)]
    config.user_quality[cid] = next_q
    return next_q


def get_quality_label(cid) -> str:
    """Return the localized display label for the user's current video quality."""
    q   = get_quality(cid)
    key = _VIDEO_QUALITY_LOCALE.get(q, 'quality_manual')
    return t(cid, key)


# =============================================================
# Audio quality helpers
# =============================================================

def get_audio_quality(cid) -> str:
    """Return the user's current audio quality/bitrate key. Default: 'default'."""
    return config.user_audio_quality.get(cid, 'default')


def cycle_audio_quality(cid) -> str:
    """Advance audio quality to the next step and return the new value."""
    current = get_audio_quality(cid)
    idx     = AUDIO_QUALITY_CYCLE.index(current) if current in AUDIO_QUALITY_CYCLE else 0
    next_q  = AUDIO_QUALITY_CYCLE[(idx + 1) % len(AUDIO_QUALITY_CYCLE)]
    config.user_audio_quality[cid] = next_q
    return next_q


def get_audio_quality_label(cid) -> str:
    """Return the localized display label for the user's current audio quality."""
    q   = get_audio_quality(cid)
    key = _AUDIO_QUALITY_LOCALE.get(q, 'audio_quality_default')
    return t(cid, key)


# =============================================================
# Video format (container) helpers
# =============================================================

def get_video_format(cid) -> str:
    """Return the user's current video container format. Default: 'mp4'."""
    return config.user_video_format.get(cid, 'mp4')


def cycle_video_format(cid) -> str:
    """Advance video container format to the next step and return the new value."""
    current = get_video_format(cid)
    idx     = VIDEO_FORMAT_CYCLE.index(current) if current in VIDEO_FORMAT_CYCLE else 0
    next_f  = VIDEO_FORMAT_CYCLE[(idx + 1) % len(VIDEO_FORMAT_CYCLE)]
    config.user_video_format[cid] = next_f
    return next_f


def get_video_format_label(cid) -> str:
    """Return the localized display label for the user's current video format."""
    f   = get_video_format(cid)
    key = _VIDEO_FORMAT_LOCALE.get(f, 'format_mp4')
    return t(cid, key)


# =============================================================
# Audio format (codec) helpers
# =============================================================

def get_audio_format(cid) -> str:
    """Return the user's current audio codec format. Default: 'mp3'."""
    return config.user_audio_format.get(cid, 'mp3')


def cycle_audio_format(cid) -> str:
    """Advance audio codec format to the next step and return the new value."""
    current = get_audio_format(cid)
    idx     = AUDIO_FORMAT_CYCLE.index(current) if current in AUDIO_FORMAT_CYCLE else 0
    next_f  = AUDIO_FORMAT_CYCLE[(idx + 1) % len(AUDIO_FORMAT_CYCLE)]
    config.user_audio_format[cid] = next_f
    return next_f


def get_audio_format_label(cid) -> str:
    """Return the localized display label for the user's current audio format."""
    f   = get_audio_format(cid)
    key = _AUDIO_FORMAT_LOCALE.get(f, 'format_mp3')
    return t(cid, key)


# =============================================================
# Subtitle helpers
# =============================================================

def get_subtitle(cid) -> str:
    """Return the user's current subtitle language preference. Default: 'off'."""
    return config.user_subtitle.get(cid, 'off')


def cycle_subtitle(cid) -> str:
    """Advance subtitle setting to the next step and return the new value."""
    current = get_subtitle(cid)
    idx     = SUBTITLE_CYCLE.index(current) if current in SUBTITLE_CYCLE else 2
    next_s  = SUBTITLE_CYCLE[(idx + 1) % len(SUBTITLE_CYCLE)]
    config.user_subtitle[cid] = next_s
    return next_s


def get_subtitle_label(cid) -> str:
    """Return the localized display label for the user's current subtitle setting."""
    s   = get_subtitle(cid)
    key = _SUBTITLE_LOCALE.get(s, 'btn_subtitle_off')
    return t(cid, key)


# =============================================================
# Chapters helpers
# =============================================================

def get_chapters(cid) -> bool:
    """Return whether chapter embedding is enabled. Default: False."""
    return config.user_chapters.get(cid, False)


def toggle_chapters(cid) -> bool:
    """Toggle chapter embedding and return the new value."""
    new_val = not config.user_chapters.get(cid, False)
    config.user_chapters[cid] = new_val
    return new_val


def get_chapters_label(cid) -> str:
    """Return the localized display label for the user's current chapters setting."""
    if get_chapters(cid):
        return t(cid, 'btn_chapters_on')
    return t(cid, 'btn_chapters_off')


# =============================================================
# Media (audio/video) mode helpers
# =============================================================

def is_audio_mode(cid) -> bool:
    """Return True if the user has selected music mode."""
    return config.user_audio_mode.get(cid, False)


def toggle_audio_mode(cid) -> bool:
    """Toggle media mode and return the new value."""
    new_val = not config.user_audio_mode.get(cid, False)
    config.user_audio_mode[cid] = new_val
    return new_val


def get_audio_mode_label(cid) -> str:
    """Return the localized display label for the user's current media mode."""
    if is_audio_mode(cid):
        return t(cid, 'media_audio')
    return t(cid, 'media_video')
