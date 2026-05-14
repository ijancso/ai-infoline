import logging
import os
from typing import Optional

import boto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError

from config import settings

logger = logging.getLogger(__name__)

_s3_client = None


def _get_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name="us-east-1",
            endpoint_url=settings.do_spaces_endpoint,
            aws_access_key_id=settings.do_spaces_key,
            aws_secret_access_key=settings.do_spaces_secret,
        )
    return _s3_client


async def upload_recording(
    recording_url: str,
    call_sid: str,
    recording_sid: str,
    twilio_auth: Optional[tuple[str, str]] = None,
) -> str:
    """Download recording from Twilio and upload to DO Spaces. Returns the Spaces object key."""
    mp3_url = recording_url if recording_url.endswith(".mp3") else recording_url + ".mp3"
    object_key = f"recordings/{call_sid}/{recording_sid}.mp3"

    async with httpx.AsyncClient(timeout=60) as http:
        response = await http.get(mp3_url, auth=twilio_auth)
        response.raise_for_status()
        audio_bytes = response.content

    try:
        _get_client().put_object(
            Bucket=settings.do_spaces_bucket,
            Key=object_key,
            Body=audio_bytes,
            ContentType="audio/mpeg",
            ACL="private",
        )
    except (BotoCoreError, ClientError) as exc:
        logger.error(
            "Spaces feltöltés sikertelen | call_sid=%s | recording_sid=%s | %s",
            call_sid,
            recording_sid,
            exc,
        )
        raise

    logger.info(
        "Felvétel feltöltve | call_sid=%s | key=%s | bytes=%d",
        call_sid,
        object_key,
        len(audio_bytes),
    )
    return object_key
