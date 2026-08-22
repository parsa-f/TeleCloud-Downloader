"""
s3_upload.py - Upload a file to the Railway Bucket (S3-compatible) and return
a working download link.

Railway buckets are not served at RAILWAY_PUBLIC_DOMAIN directly, so we return
a presigned GET URL (valid 7 days). This works regardless of bucket privacy.
"""

import os
import boto3
from config import (
    AWS_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    AWS_DEFAULT_REGION, AWS_BUCKET_NAME,
)


def _client():
    return boto3.client(
        "s3",
        endpoint_url=AWS_ENDPOINT_URL,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION,
    )


def upload_to_s3(file_path: str, chat_id: int, status_msg=None) -> str | None:
    """Upload file_path to the bucket, return a presigned download URL or None."""
    if not AWS_BUCKET_NAME:
        return None
    fname = os.path.basename(file_path)
    # object key: files/<chat_id>/<filename>
    key = f"files/{chat_id}/{fname}"
    try:
        _client().upload_file(file_path, AWS_BUCKET_NAME, key)
    except Exception as e:
        print(f"[s3] upload failed: {e}")
        return None

    # Custom public domain (PUBLIC_BASE_URL) → permanent pretty link.
    # Fallback: presigned URL (7 days), works regardless of bucket privacy.
    base = os.environ.get('PUBLIC_BASE_URL', '').strip().rstrip('/')
    if base:
        from urllib.parse import quote
        return f"{base}/files/{chat_id}/{quote(fname)}"

    try:
        url = _client().generate_presigned_url(
            "get_object",
            Params={"Bucket": AWS_BUCKET_NAME, "Key": key},
            ExpiresIn=7 * 24 * 3600,  # 7 days
        )
        return url
    except Exception as e:
        print(f"[s3] presign failed: {e}")
        return None
