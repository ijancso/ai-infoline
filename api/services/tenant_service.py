from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import PhoneNumber, Tenant


async def get_tenant_by_phone(db: AsyncSession, phone_number: str) -> Optional[Tenant]:
    result = await db.execute(
        select(Tenant)
        .join(PhoneNumber, PhoneNumber.tenant_id == Tenant.id)
        .where(PhoneNumber.phone_number == phone_number)
    )
    return result.scalar_one_or_none()
