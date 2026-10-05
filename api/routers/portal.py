import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db
from models import Call, PhoneNumber, Tenant
from schemas import CallOut, CallWithMessagesOut, PhoneNumberOut, TenantOut, TenantUpdate

router = APIRouter(prefix="/api/portal", tags=["portal"])

DB = Annotated[AsyncSession, Depends(get_db)]


async def _get_tenant(
    db: Annotated[AsyncSession, Depends(get_db)],
    x_tenant_key: Annotated[str | None, Header()] = None,
) -> Tenant:
    if not x_tenant_key:
        raise HTTPException(status_code=401, detail="Missing X-Tenant-Key header")
    try:
        key = uuid.UUID(x_tenant_key)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid tenant key")
    result = await db.execute(select(Tenant).where(Tenant.api_key == key))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=401, detail="Invalid tenant key")
    return tenant


Auth = Annotated[Tenant, Depends(_get_tenant)]


@router.get("/me", response_model=TenantOut)
async def get_me(tenant: Auth) -> Tenant:
    return tenant


@router.patch("/me", response_model=TenantOut)
async def update_me(body: TenantUpdate, tenant: Auth, db: DB) -> Tenant:
    editable = {"system_prompt", "greeting", "knowledge_base"}
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in editable:
            setattr(tenant, field, value)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("/phone-numbers", response_model=list[PhoneNumberOut])
async def list_phone_numbers(tenant: Auth, db: DB):
    result = await db.execute(
        select(PhoneNumber)
        .where(PhoneNumber.tenant_id == tenant.id)
        .order_by(PhoneNumber.created_at)
    )
    return result.scalars().all()


@router.get("/calls", response_model=list[CallOut])
async def list_calls(
    tenant: Auth,
    db: DB,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = await db.execute(
        select(Call)
        .where(Call.tenant_id == tenant.id)
        .order_by(Call.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/calls/{call_id}", response_model=CallWithMessagesOut)
async def get_call(call_id: uuid.UUID, tenant: Auth, db: DB):
    result = await db.execute(
        select(Call)
        .where(Call.id == call_id, Call.tenant_id == tenant.id)
        .options(selectinload(Call.messages))
    )
    call = result.scalar_one_or_none()
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return call
