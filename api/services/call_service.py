from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Call


async def upsert_call(
    db: AsyncSession,
    call_sid: str,
    from_number: Optional[str] = None,
    to_number: Optional[str] = None,
    status: Optional[str] = None,
    duration_seconds: Optional[int] = None,
) -> Call:
    result = await db.execute(select(Call).where(Call.call_sid == call_sid))
    call = result.scalar_one_or_none()

    if call is None:
        call = Call(call_sid=call_sid)
        db.add(call)

    if from_number is not None:
        call.from_number = from_number
    if to_number is not None:
        call.to_number = to_number
    if status is not None:
        call.status = status
    if duration_seconds is not None:
        call.duration_seconds = duration_seconds

    call.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(call)
    return call
