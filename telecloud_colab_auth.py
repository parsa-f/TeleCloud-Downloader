"""
TeleCloud-Downloader — Google Drive Auth Script
================================================
Run this script inside Google Colab (or locally) to:
  1. Authenticate with your Google account
  2. Create the "TeleCloud-Downloads" folder in your Drive (if it doesn't exist)
  3. Generate a ready-to-use rclone.conf locked to that folder
  4. Download the config file automatically to your device

After the file downloads, send it to the bot via Telegram — it will
be stored as your personal rclone config and all uploads will go
straight to YOUR Google Drive.

Token expiry note:
  The OAuth2 tokens embedded in the generated rclone.conf include a
  refresh_token. rclone will automatically exchange it for a new
  access_token whenever needed, so the config stays valid indefinitely
  as long as you don't revoke access from your Google Account settings.
"""

# ─────────────────────────────────────────────────────────────
# Cell 1 — Install dependencies (run once per Colab session)
# ─────────────────────────────────────────────────────────────
# !pip install -q google-auth google-auth-oauthlib google-api-python-client

# ─────────────────────────────────────────────────────────────
# Cell 2 — Authenticate & build Drive config
# ─────────────────────────────────────────────────────────────
import json
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ── Colab-specific import (only works inside Google Colab) ──
try:
    from google.colab import auth as colab_auth
    from google.colab import files as colab_files
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

# Scopes required: full Drive access so rclone can read/write files
SCOPES = [
    "https://www.googleapis.com/auth/drive",
]

# ── rclone OAuth2 client credentials ──
# Google is retiring the shared rclone client_id in 2026, so each user MUST
# provide their OWN credentials. Create them at:
#   https://console.cloud.google.com/apis/credentials
#   1. "Create OAuth client ID" → Application type: "Desktop app"
#   2. Copy the Client ID and Client Secret below.
# If left blank, the script will fall back to the (deprecated) shared rclone id.
RCLONE_CLIENT_ID     = ""   # ← paste your own Client ID here
RCLONE_CLIENT_SECRET = ""   # ← paste your own Client Secret here

# Token endpoint used by rclone
RCLONE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Name of the Drive folder that will receive all bot uploads
DRIVE_FOLDER_NAME = "TeleCloud-Downloads"


# =============================================================
# Auth helpers
# =============================================================

def _get_credentials_via_flow() -> Credentials:
    """
    Run an OAuth2 InstalledAppFlow using rclone's public client credentials
    with a localhost redirect.

    The user:
      1. Clicks the printed URL
      2. Authorises the app in their browser
      3. Gets redirected to localhost (which fails — that is expected)
      4. Copies the full redirect URL and pastes it back here
    """
    client_config = {
        "installed": {
            "client_id":     RCLONE_CLIENT_ID or "202264815644.apps.googleusercontent.com",
            "client_secret": RCLONE_CLIENT_SECRET or "X4Z3ca8xfWDb1Voo-F9a7ZxJ",
            "auth_uri":                    "https://accounts.google.com/o/oauth2/auth",
            "token_uri":                   RCLONE_TOKEN_URL,
            "redirect_uris":               ["http://localhost"],
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = "http://localhost"

    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

    print("\n" + "🌐 " + "-" * 60)
    print("۱. لطفاً روی لینک زیر کلیک کنید و اکانت گوگل خود را انتخاب کنید:")
    print(f"\n   {auth_url}\n")
    print("-" * 62)
    print("⚠️  نکته مهم: بعد از دادن دسترسی، مرورگر شما به یک صفحه خطا")
    print("   (مثلاً 'Site cannot be reached' یا 'Localhost') می‌رود.")
    print("   این کاملاً طبیعی است! کل آدرس (URL) آن صفحه را از بالای")
    print("   مرورگر کپی کنید و اینجا پیست کنید.\n")

    response_url = input(
        "🔗 کل آدرس (URL) صفحه خطا را اینجا پیست کنید و Enter بزنید: "
    ).strip()

    # Smart code extraction from the redirect URL
    parsed = urlparse(response_url)
    code_list = parse_qs(parsed.query).get("code")

    if code_list:
        code = code_list[0]
    elif response_url.startswith("4/"):
        # User pasted only the bare auth code, not the full URL
        code = response_url
    else:
        raise ValueError(
            "❌ کد تایید در لینکی که دادید پیدا نشد!\n"
            "مطمئن شوید که کل آدرس مرورگر (نه فقط بخشی از آن) را کپی کردید."
        )

    flow.fetch_token(code=code)
    return flow.credentials


# =============================================================
# Google Drive folder helper  ← THE MISSING FUNCTION (now added)
# =============================================================

def _get_or_create_folder(service) -> str:
    """
    Look up the ``TeleCloud-Downloads`` folder in the authenticated user's
    Google Drive.  If it does not exist, create it.

    Returns the folder's ID string.
    """
    # Search for an existing folder with the exact name (not trashed)
    query = (
        f"mimeType='application/vnd.google-apps.folder' "
        f"and name='{DRIVE_FOLDER_NAME}' "
        f"and trashed=false"
    )
    response = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)", pageSize=1)
        .execute()
    )
    items = response.get("files", [])

    if items:
        folder_id = items[0]["id"]
        print(f"   ✅ پوشه موجود است (ID: {folder_id})")
        return folder_id

    # Folder not found — create it
    print(f"   📁 پوشه '{DRIVE_FOLDER_NAME}' پیدا نشد. در حال ساخت…")
    file_metadata = {
        "name":     DRIVE_FOLDER_NAME,
        "mimeType": "application/vnd.google-apps.folder",
    }
    folder = (
        service.files()
        .create(body=file_metadata, fields="id")
        .execute()
    )
    folder_id = folder["id"]
    print(f"   ✅ پوشه ساخته شد (ID: {folder_id})")
    return folder_id


# =============================================================
# rclone.conf builder
# =============================================================

def _build_rclone_conf(creds: Credentials, root_folder_id: str) -> str:
    """
    Construct a valid rclone.conf string for a Google Drive remote
    locked to ``root_folder_id``.

    Token structure expected by rclone:
      {"access_token": "...", "token_type": "Bearer",
       "refresh_token": "...", "expiry": "2006-01-02T15:04:05.999999999Z07:00"}
    """
    token_dict = {
        "access_token":  creds.token or "",
        "token_type":    "Bearer",
        "refresh_token": creds.refresh_token or "",
        # rclone accepts an empty expiry string; it will refresh automatically.
        "expiry": (
            creds.expiry.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")
            if creds.expiry else "0001-01-01T00:00:00Z"
        ),
    }
    token_json = json.dumps(token_dict)

    conf = f"""\
[gdrive]
type = drive
client_id = {RCLONE_CLIENT_ID}
client_secret = {RCLONE_CLIENT_SECRET}
scope = drive
root_folder_id = {root_folder_id}
token = {token_json}
"""
    return conf


# =============================================================
# Main
# =============================================================

def main():
    print("=" * 62)
    print("  TeleCloud-Downloader — Google Drive Setup")
    print("=" * 62)
    print()

    # ── Step 1: Authenticate ──────────────────────────────────
    print("🔐 Step 1: Authenticating with Google…")
    creds = _get_credentials_via_flow()
    print("   ✅ Authentication successful.\n")

    # ── Step 2: Locate / create Drive folder ─────────────────
    print(f"🔍 Step 2: Checking Google Drive for '{DRIVE_FOLDER_NAME}' folder…")
    service   = build("drive", "v3", credentials=creds)
    folder_id = _get_or_create_folder(service)
    print()

    # ── Step 3: Build rclone.conf ─────────────────────────────
    print("📝 Step 3: Generating rclone.conf…")
    conf_text = _build_rclone_conf(creds, folder_id)
    print("   ✅ Config generated.\n")

    # ── Step 4: Save & trigger download ──────────────────────
    output_path = Path("/tmp/rclone.conf") if IN_COLAB else Path("rclone.conf")
    output_path.write_text(conf_text, encoding="utf-8")
    print(f"💾 Config written to: {output_path}")

    if IN_COLAB:
        print("📥 Step 4: Triggering file download to your device…")
        colab_files.download(str(output_path))
        print()
        print("✅ تمام! فایل 'rclone.conf' را که دانلود شد به ربات تلگرام بفرستید.")
    else:
        print()
        print("✅ تمام! فایل 'rclone.conf' (در پوشه جاری) را به ربات تلگرام بفرستید.")

    print()
    print("─" * 62)
    print("  After connecting, your downloads will appear in:")
    print(f"  My Drive → {DRIVE_FOLDER_NAME} → <source platform>")
    print("─" * 62)


if __name__ == "__main__":
    main()
