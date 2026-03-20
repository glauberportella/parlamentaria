"""Meta (Facebook) data-deletion callback endpoint.

Required by Meta Platform Policy for apps that handle user data.
When a user removes the app from their Facebook settings, Meta sends
a signed POST request with the user ID requesting data deletion.

Reference:
    https://developers.facebook.com/docs/development/create-an-app/app-dashboard/data-deletion-callback
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.session import async_session_factory
from app.logging import get_logger
from app.middleware import limiter
from app.services.eleitor_service import EleitorService

router = APIRouter(tags=["meta"])
logger = get_logger(__name__)


def _verify_meta_signed_request(signed_request: str, app_secret: str) -> dict | None:
    """Parse and verify a Meta signed_request parameter.

    The signed_request is a base64url-encoded JSON payload preceded by
    an HMAC-SHA256 signature, separated by a dot.

    Returns:
        Parsed payload dict if signature is valid, None otherwise.
    """
    try:
        parts = signed_request.split(".", 1)
        if len(parts) != 2:
            return None

        encoded_sig, payload_b64 = parts

        # Decode signature (base64url)
        padding = 4 - len(encoded_sig) % 4
        encoded_sig += "=" * padding
        sig = base64.urlsafe_b64decode(encoded_sig)

        # Verify HMAC-SHA256
        expected_sig = hmac.new(
            app_secret.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(sig, expected_sig):
            return None

        # Decode payload
        padding = 4 - len(payload_b64) % 4
        payload_b64 += "=" * padding
        payload_json = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_json)
    except Exception:
        return None


@router.post("/webhook/meta/data-deletion")
@limiter.limit("10/minute")
async def meta_data_deletion(request: Request) -> JSONResponse:
    """Handle Meta data-deletion callback.

    Meta sends a POST with form-encoded `signed_request` containing
    the user_id. We verify the HMAC signature, delete associated data
    and return a JSON response with a confirmation_code and a url
    where the user can check deletion status.
    """
    form = await request.form()
    signed_request = form.get("signed_request", "")

    if not signed_request or not settings.meta_app_secret:
        logger.warning("meta.data_deletion.missing_params")
        return JSONResponse(
            status_code=400,
            content={"error": "Requisição inválida."},
        )

    payload = _verify_meta_signed_request(
        str(signed_request), settings.meta_app_secret
    )
    if payload is None:
        logger.warning("meta.data_deletion.invalid_signature")
        return JSONResponse(
            status_code=403,
            content={"error": "Assinatura inválida."},
        )

    meta_user_id = payload.get("user_id", "")
    confirmation_code = uuid.uuid4().hex[:12]

    logger.info(
        "meta.data_deletion.request",
        meta_user_id=meta_user_id,
        confirmation_code=confirmation_code,
    )

    # Attempt to find and delete user data linked to this Meta user ID.
    # The chat_id for WhatsApp/Facebook channels is the Meta user_id.
    deleted = False
    try:
        async with async_session_factory() as session:
            service = EleitorService(session)
            await service.solicitar_exclusao_por_chat_id(str(meta_user_id))
            await session.commit()
            deleted = True
    except Exception:
        # User may not exist in our system — that's fine, we still
        # respond with success per Meta's requirements.
        logger.info(
            "meta.data_deletion.no_user_found",
            meta_user_id=meta_user_id,
        )

    logger.info(
        "meta.data_deletion.completed",
        meta_user_id=meta_user_id,
        deleted=deleted,
        confirmation_code=confirmation_code,
    )

    # Meta expects JSON with url and confirmation_code
    return JSONResponse(
        content={
            "url": f"https://parlamentaria.app/exclusao-de-dados?code={confirmation_code}",
            "confirmation_code": confirmation_code,
        },
    )
