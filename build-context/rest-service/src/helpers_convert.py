import base64, hashlib, os
from werkzeug.exceptions import BadRequest
from src.helpers import log

def validate_convert_request_data(payload):

    if not isinstance(payload, dict):
        raise BadRequest("Request payload must be a JSON object.")

    required_fields = ["data", "convert_to", "convert_from", "write_to"]
    for field in required_fields:
        if field not in payload:
            raise BadRequest(f"Missing required field: '{field}'")

    allowed_sources = ["docx", "doc"]
    if payload["convert_from"] not in allowed_sources:
        raise BadRequest(f"'convert_from' field must be one of: {allowed_sources}")
    
    allowed_targets = ["pdf", "html"]
    if payload["convert_to"] not in allowed_targets:
        raise BadRequest(f"'convert_to' field must be one of: {allowed_targets}")
    
    if payload["write_to"] not in ["stream", "base64"]:

        payload["write_to"] = payload["write_to"].removeprefix("/data/")
        if payload["write_to"].startswith("/"):
              raise ValueError("Attempting to write outside of /data")

        payload["write_to"] = os.path.join("/data",  payload["write_to"] )
        if not payload["write_to"]  or os.path.basename(payload["write_to"] ).strip() == '':
            raise ValueError("No filename specified.")
        target_dir = os.path.dirname(payload["write_to"] )

        # Check if target directory exists
        if not os.path.isdir(target_dir):
            raise FileNotFoundError(f"Target directory '{target_dir}' does not exist.")

        # Check for permissions
        if not os.access(target_dir, os.W_OK):
            raise PermissionError(f"No write permission for directory '{target_dir}'.")

        # Check if file already exists
        if ("overwrite" not in payload or not payload["overwrite"]) and os.path.exists(payload["write_to"]):
            raise BadRequest(f"Error: File '{payload["write_to"] }' already exists. Set overwrite to true to allow.")
    
    if "bust" not in payload:
        payload["bust"] = False

    log(f"Incoming request validated. Converting file to {payload["convert_to"]}, destination is: {payload["write_to"] }")

    return payload


def extract_file_bytes(data_url: str) -> bytes:
    import re
    if not data_url.startswith("data:"):
        raise ValueError("Invalid data URL format")
    try:
        header, base64_data = data_url.split(',', 1)
    except ValueError:
        raise ValueError("Malformed data URL")
    if not re.search(r';base64$', header):
        raise ValueError("Data URL must be base64 encoded")
    return base64.b64decode(base64_data)

def compute_hash(content: bytes) -> str:
    """Compute SHA256 hash of content."""
    sha = hashlib.sha256()
    sha.update(content)
    return sha.hexdigest()