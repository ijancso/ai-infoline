import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from config import settings
from models import Call, PhoneNumber, Recording, Tenant
from schemas import (
    CallOut,
    PhoneNumberCreate,
    PhoneNumberOut,
    RecordingOut,
    TenantCreate,
    TenantOut,
    TenantUpdate,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(x_admin_key: Annotated[str | None, Header()] = None) -> None:
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")


Auth = Annotated[None, Depends(_require_admin)]
DB = Annotated[AsyncSession, Depends(get_db)]


# --- Tenants ---

@router.post("/tenants", response_model=TenantOut, status_code=201)
async def create_tenant(body: TenantCreate, _: Auth, db: DB):
    existing = await db.execute(select(Tenant).where(Tenant.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Slug already taken")

    tenant = Tenant(**body.model_dump())
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("/tenants", response_model=list[TenantOut])
async def list_tenants(
    _: Auth,
    db: DB,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()).offset(offset).limit(limit))
    return result.scalars().all()


@router.get("/tenants/{tenant_id}", response_model=TenantOut)
async def get_tenant(_: Auth, db: DB, tenant_id: uuid.UUID):
    return await _get_tenant_or_404(db, tenant_id)


@router.patch("/tenants/{tenant_id}", response_model=TenantOut)
async def update_tenant(body: TenantUpdate, _: Auth, db: DB, tenant_id: uuid.UUID):
    tenant = await _get_tenant_or_404(db, tenant_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.delete("/tenants/{tenant_id}", status_code=204)
async def delete_tenant(_: Auth, db: DB, tenant_id: uuid.UUID):
    tenant = await _get_tenant_or_404(db, tenant_id)
    await db.delete(tenant)
    await db.commit()


# --- Phone numbers ---

@router.post("/tenants/{tenant_id}/phone-numbers", response_model=PhoneNumberOut, status_code=201)
async def add_phone_number(body: PhoneNumberCreate, _: Auth, db: DB, tenant_id: uuid.UUID):
    await _get_tenant_or_404(db, tenant_id)

    existing = await db.execute(select(PhoneNumber).where(PhoneNumber.phone_number == body.phone_number))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Phone number already assigned")

    phone = PhoneNumber(tenant_id=tenant_id, **body.model_dump())
    db.add(phone)
    await db.commit()
    await db.refresh(phone)
    return phone


@router.get("/tenants/{tenant_id}/phone-numbers", response_model=list[PhoneNumberOut])
async def list_phone_numbers(_: Auth, db: DB, tenant_id: uuid.UUID):
    await _get_tenant_or_404(db, tenant_id)
    result = await db.execute(
        select(PhoneNumber).where(PhoneNumber.tenant_id == tenant_id).order_by(PhoneNumber.created_at)
    )
    return result.scalars().all()


@router.delete("/tenants/{tenant_id}/phone-numbers/{phone_id}", status_code=204)
async def delete_phone_number(_: Auth, db: DB, tenant_id: uuid.UUID, phone_id: uuid.UUID):
    await _get_tenant_or_404(db, tenant_id)
    result = await db.execute(
        select(PhoneNumber).where(PhoneNumber.id == phone_id, PhoneNumber.tenant_id == tenant_id)
    )
    phone = result.scalar_one_or_none()
    if phone is None:
        raise HTTPException(status_code=404, detail="Phone number not found")
    await db.delete(phone)
    await db.commit()


# --- Calls ---

@router.get("/tenants/{tenant_id}/calls", response_model=list[CallOut])
async def list_calls(
    _: Auth,
    db: DB,
    tenant_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    await _get_tenant_or_404(db, tenant_id)
    result = await db.execute(
        select(Call)
        .where(Call.tenant_id == tenant_id)
        .order_by(Call.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


# --- Recordings ---

@router.get("/tenants/{tenant_id}/calls/{call_id}/recordings", response_model=list[RecordingOut])
async def list_recordings(_: Auth, db: DB, tenant_id: uuid.UUID, call_id: uuid.UUID):
    await _get_tenant_or_404(db, tenant_id)
    result = await db.execute(select(Call).where(Call.id == call_id, Call.tenant_id == tenant_id))
    call = result.scalar_one_or_none()
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    result = await db.execute(
        select(Recording).where(Recording.call_sid == call.call_sid).order_by(Recording.created_at)
    )
    return result.scalars().all()


# --- Helpers ---

async def _get_tenant_or_404(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
