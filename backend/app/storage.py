import os
import hashlib
import uuid

# Stands in for S3-compatible object storage in local/dev runs. Swapping
# this module for a boto3-backed implementation is a configuration change,
# not an architecture change — routers never touch the filesystem directly,
# they only call save_content()/read_content(), so the separation between
# metadata (DB) and content (object storage) holds either way.

STORAGE_ROOT = os.getenv("DOCKIT_STORAGE_ROOT", os.path.join(os.path.dirname(__file__), "..", "storage"))
os.makedirs(STORAGE_ROOT, exist_ok=True)


def save_content(content_bytes: bytes) -> tuple[str, str]:
    """Writes content to storage, returns (storage_path, sha256_hash)."""
    sha = hashlib.sha256(content_bytes).hexdigest()
    filename = f"{uuid.uuid4()}.bin"
    path = os.path.join(STORAGE_ROOT, filename)
    with open(path, "wb") as f:
        f.write(content_bytes)
    return filename, sha


def read_content(storage_path: str) -> bytes:
    path = os.path.join(STORAGE_ROOT, storage_path)
    with open(path, "rb") as f:
        return f.read()


def recompute_hash(storage_path: str) -> str:
    return hashlib.sha256(read_content(storage_path)).hexdigest()
