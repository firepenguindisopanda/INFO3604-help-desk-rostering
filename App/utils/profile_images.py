from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse

DEFAULT_PROFILE_IMAGE_URL = "https://0vc0bkr0m1.ufs.sh/f/LpP4WqZnW7NcQvi15SsN937VJ2v56DCBKwtydH8oIWqnjYXp"


ProfileData = Dict[str, Any]


def _parse_profile_data(raw: Any) -> ProfileData:
    """Safely parse profile_data stored as JSON text or dict."""
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return {}
    return {}


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _select_candidate(data: ProfileData) -> Optional[str]:
    for key in (
        "profile_picture_url",
        "profilePictureUrl",
        "image_url",
        "imageUrl",
        "image_filename",
        "imageFilename",
    ):
        value = data.get(key)
        if value:
            return str(value).strip()
    return None


def resolve_profile_image(
    raw_profile_data: Any,
    *,
    static_base: Optional[str] = None,
    fallback_url: Optional[str] = None,
) -> str:
    """Return a usable profile image URL with a safe default."""
    data = _parse_profile_data(raw_profile_data)
    candidate = _select_candidate(data)

    if candidate and _is_http_url(candidate):
        return candidate

    if candidate and static_base:
        return urljoin(static_base.rstrip('/') + '/', candidate.lstrip('/'))

    return fallback_url or DEFAULT_PROFILE_IMAGE_URL
