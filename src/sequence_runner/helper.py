from pathlib import Path
from typing import Any, Dict, Tuple
import io, base64

def _tiny_png_bytes() -> bytes:
    # 1x1 transparent PNG
    _B64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
        "ASsJTYQAAAAASUVORK5CYII="
    )
    return base64.b64decode(_B64)

def _bytes_from_data_url(data_url: str) -> Tuple[str, bytes]:
    head, _, b64 = data_url.partition(",")
    mime = "application/octet-stream"
    if head.startswith("data:"):
        mime = head[5:].split(";")[0] or mime
    ext = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/gif": "gif",
        "image/webp": "webp",
    }.get(mime, "bin")
    raw = base64.b64decode(b64)
    return (f"upload.{ext}", raw)

def _split_body_into_form_and_files(body: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, tuple]]:
    """
    Convert JSON body to (form_fields, files) for requests.
    Recognizes file-ish keys and special values:
      - keys: avatar/file/image/upload/attachment
      - 'file:/path.png' → path upload
      - 'dummy:png'      → generate 1x1 PNG bytes
      - 'data:image/...;base64,....' → data URL
      - existing real paths still work
    """
    if not isinstance(body, dict):
        return {}, {}

    form_fields: Dict[str, Any] = {}
    files: Dict[str, tuple] = {}

    for k, v in body.items():
        if isinstance(v, str):
            val = v.strip()

            # data URL inline
            if val.startswith("data:image/"):
                fname, data = _bytes_from_data_url(val)
                files[k] = (fname, io.BytesIO(data))
                continue

            # dummy placeholder image
            if val.lower().startswith("dummy:png"):
                files[k] = ("avatar.png", io.BytesIO(_tiny_png_bytes()))
                continue

            # explicit file path via file:
            if val.startswith("file:"):
                p = Path(val[5:])
                if p.exists() and p.is_file():
                    files[k] = (p.name, p.open("rb"))
                else:
                    # keep as form value; server may reject (useful signal)
                    form_fields[k] = val
                continue

            # bare path string that actually exists
            p = Path(val)
            if p.exists() and p.is_file():
                files[k] = (p.name, p.open("rb"))
                continue

            # not a real file → keep as plain form value
            form_fields[k] = val
            continue

        form_fields[k] = "" if v is None else v

    return form_fields, files
