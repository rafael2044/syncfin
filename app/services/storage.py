import os
import re
import uuid
import mimetypes
import httpx
from fastapi import UploadFile
from app.config import get_settings

settings = get_settings()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "uploads")

BLOB_API_URL = "https://blob.squarecloud.app/v1/objects"


async def upload_file(file: UploadFile, prefix: str = "anexos") -> str:
    if settings.STORAGE_TYPE == "blob":
        return await _upload_to_blob(file, prefix)
    return await _upload_to_local(file)


async def _upload_to_local(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename)[1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    return f"/uploads/{filename}"


def _sanitize_blob_name(filename: str) -> str:
    name = os.path.splitext(filename)[0]
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if len(name) < 3:
        name = (name + "_blob")[:32]
    if len(name) > 32:
        name = name[:32]
    return name


def _sanitize_blob_prefix(prefix: str) -> str:
    prefix = re.sub(r"[^a-zA-Z0-9_]", "_", prefix)
    prefix = re.sub(r"_+", "_", prefix).strip("_")
    if len(prefix) < 3:
        prefix = (prefix + "_upload")[:32]
    if len(prefix) > 32:
        prefix = prefix[:32]
    return prefix


async def _upload_to_blob(file: UploadFile, prefix: str) -> str:
    content = await file.read()
    name = _sanitize_blob_name(file.filename)
    prefix = _sanitize_blob_prefix(prefix)
    mime_type = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            BLOB_API_URL,
            headers={"Authorization": settings.SQUARE_CLOUD_API_KEY},
            params={"name": name, "prefix": prefix},
            files={"file": (file.filename, content, mime_type)},
        )
        response.raise_for_status()

    data = response.json()
    if data.get("status") == "success":
        return data["response"]["url"]
    return ""
