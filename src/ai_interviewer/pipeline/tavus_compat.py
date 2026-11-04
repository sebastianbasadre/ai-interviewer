"""Adapt Pipecat 1.15's legacy Tavus REST calls to the Face/PAL API.

The SDK keeps its verified audio/video, Echo, interrupt and cleanup behavior. Only
its session boundary is adapted; neither installed SDK code nor globals are patched.
No provider SDKs are imported and no requests are made when importing this module.
"""
from __future__ import annotations

import re

TAVUS_BASE_URL = "https://tavusapi.com/v2"
_IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,128}")


class TavusCompatibilityError(Exception):
    """Fixed diagnostics only: provider response bodies can contain credentials."""


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise TavusCompatibilityError("Invalid Tavus resource identifier.")
    return value


class _PalResponse:
    def __init__(self, response):
        self._response = response

    def raise_for_status(self):
        return self._response.raise_for_status()

    async def json(self):
        data = await self._response.json()
        if not isinstance(data, dict) or not isinstance(data.get("pal_name"), str):
            raise TavusCompatibilityError("Tavus PAL response is missing its name.")
        # Pipecat's get_persona_name() consumes only this legacy key. Do not pass
        # PAL prompts, tool secrets or provider credentials through that boundary.
        return {"persona_name": data["pal_name"]}


class _PalRequest:
    def __init__(self, context):
        self._context = context

    async def __aenter__(self):
        return _PalResponse(await self._context.__aenter__())

    async def __aexit__(self, *args):
        return await self._context.__aexit__(*args)


class TavusSessionAdapter:
    """The get/post async context-manager interface used by TavusApi in 1.15.

The underlying aiohttp session remains owned by MediaManager. Restrict requests
to the three inspected SDK operations and keep authentication server-side.
"""

    def __init__(self, session, *, face_id: str, pal_id: str, max_duration_seconds: int):
        if type(max_duration_seconds) is not int or not 1 <= max_duration_seconds <= 1800:
            raise TavusCompatibilityError("Invalid Tavus conversation duration.")
        self._session = session
        self._face_id = _identifier(face_id)
        self._pal_id = _identifier(pal_id)
        self._max_duration = max_duration_seconds

    def post(self, url, **kwargs):
        if url == TAVUS_BASE_URL + "/conversations":
            legacy = kwargs.get("json")
            if legacy != {"replica_id": self._face_id, "persona_id": self._pal_id}:
                raise TavusCompatibilityError("Unexpected Pipecat Tavus create request.")
            kwargs["json"] = {
                "face_id": self._face_id,
                "pal_id": self._pal_id,
                "properties": {
                    "max_call_duration": self._max_duration,
                    "participant_left_timeout": min(10, self._max_duration),
                    "participant_absent_timeout": min(20, self._max_duration),
                    "enable_recording": False,
                    "auto_start_recording": False,
                },
            }
        elif not re.fullmatch(re.escape(TAVUS_BASE_URL) + r"/conversations/[A-Za-z0-9_-]{1,128}/end", str(url)):
            raise TavusCompatibilityError("Unexpected Pipecat Tavus endpoint.")
        kwargs["allow_redirects"] = False
        return self._session.post(url, **kwargs)

    def get(self, url, **kwargs):
        if url != TAVUS_BASE_URL + "/personas/" + self._pal_id:
            raise TavusCompatibilityError("Unexpected Pipecat Tavus endpoint.")
        kwargs["allow_redirects"] = False
        return _PalRequest(self._session.get(TAVUS_BASE_URL + "/pals/" + self._pal_id, **kwargs))


def create_tavus_video_service(settings, session, *, max_duration_seconds: int):
    """Construction is local; the SDK opens the provider session during setup."""
    if not settings.realtime_enabled or not settings.tavus_enabled or settings.avatar_mode != "tavus":
        raise TavusCompatibilityError("Tavus is not enabled.")
    if settings.missing_tavus_settings():
        raise TavusCompatibilityError("Tavus configuration is incomplete.")
    face_id = settings.resolved_tavus_face_id.get_secret_value().strip()
    pal_id = settings.tavus_pal_id.get_secret_value().strip()
    adapted_session = TavusSessionAdapter(session, face_id=face_id, pal_id=pal_id,
                                         max_duration_seconds=max_duration_seconds)
    from pipecat.services.tavus.video import TavusVideoService
    # Constructor names remain legacy in pinned Pipecat 1.15. All outgoing HTTP
    # payloads use current field names, and PAL metadata uses /pals/{pal_id}.
    return TavusVideoService(api_key=settings.tavus_api_key.get_secret_value(),
                             replica_id=face_id, persona_id=pal_id, session=adapted_session)
