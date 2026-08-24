"""
s3_upload.py - Upload a file to the Railway Bucket (S3-compatible) and return
a working download link.

Railway buckets are not served at RAILWAY_PUBLIC_DOMAIN directly, so we return
a presigned GET URL (valid 7 days). This works regardless of bucket privacy.
"""

import os
import base64
import secrets
import boto3
from urllib.parse import quote
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


# ponytail: env-config cap; per-user quotas if this ever becomes a hotspot
BUCKET_MAX_BYTES = int(os.environ.get('BUCKET_MAX_GB', '5')) * 1024 ** 3


def _evict_oldest_if_full(client, incoming_bytes: int):
    """If bucket usage + incoming exceeds the cap, delete oldest objects
    until there's room. Keeps the newest files, evicts the oldest first."""
    try:
        paginator = client.get_paginator('list_objects_v2')
        objs = []
        total = 0
        for page in paginator.paginate(Bucket=AWS_BUCKET_NAME):
            for o in page.get('Contents', []):
                objs.append({'Key': o['Key'], 'Size': o['Size'],
                             'LastModified': o['LastModified']})
                total += o['Size']
        if total + incoming_bytes <= BUCKET_MAX_BYTES:
            return
        freed = 0
        need = total + incoming_bytes - BUCKET_MAX_BYTES
        for o in sorted(objs, key=lambda x: x['LastModified']):
            if freed >= need:
                break
            client.delete_object(Bucket=AWS_BUCKET_NAME, Key=o['Key'])
            freed += o['Size']
        print(f"[s3] evicted {freed/1e6:.0f}MB of old objects to make room")
    except Exception as e:
        print(f"[s3] evict failed (non-fatal): {e}")


def upload_to_s3(file_path: str, chat_id: int, status_msg=None) -> str | None:
    """Upload file_path to the bucket (encrypted with SSE-C), return a
    download URL. The per-file AES key rides in the URL fragment (#...),
    which browsers send to the proxy but S3-style servers ignore — privacy
    without a key database."""
    if not AWS_BUCKET_NAME:
        return None
    fname = os.path.basename(file_path)
    # object key: files/<chat_id>/<filename>
    key = f"files/{chat_id}/{fname}"

    client = _client()
    _evict_oldest_if_full(client, os.path.getsize(file_path))

    # SSE-C: server-side encryption with a customer-provided per-file key.
    file_key = secrets.token_bytes(32)
    key_md5 = base64.b64encode(__import__('hashlib').md5(file_key).digest()).decode()
    try:
        client.upload_file(
            file_path, AWS_BUCKET_NAME, key,
            ExtraArgs={'SSECustomerAlgorithm': 'AES256',
                       'SSECustomerKey': file_key,
                       'SSECustomerKeyMD5': key_md5})
    except Exception as e:
        print(f"[s3] encrypted upload failed ({type(e).__name__}), falling back to plain: {e}")
        try:
            client.upload_file(file_path, AWS_BUCKET_NAME, key)
        except Exception as e2:
            print(f"[s3] upload failed: {e2}")
            return None
        file_key = None  # stored unencrypted

    # Custom public domain (PUBLIC_BASE_URL) → permanent pretty link.
    # Fallback: presigned URL (7 days), works regardless of bucket privacy.
    base = os.environ.get('PUBLIC_BASE_URL', '').strip().rstrip('/')
    frag = f"#k={base64.urlsafe_b64encode(file_key).decode()}" if file_key else ""
    if base:
        return f"{base}/files/{chat_id}/{quote(fname)}{frag}"

    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": AWS_BUCKET_NAME, "Key": key},
            ExpiresIn=7 * 24 * 3600,  # 7 days
        )
        return url + frag
    except Exception as e:
        print(f"[s3] presign failed: {e}")
        return None
