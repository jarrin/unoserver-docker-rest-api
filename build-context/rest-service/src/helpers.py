import hashlib
import mimetypes, re, base64
from flask_caching import Cache

# Helper function to log to dockers console, in case the application runs in the background
def log (message: str, err = False):
    with open("/proc/1/fd/1" if not err else "/proc/1/fd/2", 'w') as stdout:
        stdout.write(message + "\n")

def compute_hash(content: bytes) -> str:
    """Compute SHA256 hash of content."""
    sha = hashlib.sha256()
    sha.update(content)
    return sha.hexdigest()

def handle_file(base64_data: str, bust: bool, cache: Cache):
    bytes = base64.b64decode(base64_data)
    key = compute_hash(bytes)

    result = None
    if bust:
        cache.delete(key)
    else:
        result = cache.get(key)
    
    if result is None:
        result = {"converted_base64": None, "expires_at": None}

    result["key"] = key
    result["input_bytes"] = bytes

    return result