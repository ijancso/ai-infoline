import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# --- Tenant ---

class TenantCreate(BaseModel):
    name: str
    slug: str
    system_prompt: Optional[str] = None
    stripe_customer_id: Optional[str] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    stripe_customer_id: Optional[str] = None


class TenantOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    system_prompt: Optional[str]
    stripe_customer_id: Optional[str]
    api_key: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# --- PhoneNumber ---

class PhoneNumberCreate(BaseModel):
    phone_number: str
    label: Optional[str] = None


class PhoneNumberOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    phone_number: str
    label: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Call ---

class CallOut(BaseModel):
    id: uuid.UUID
    call_sid: str
    from_number: Optional[str]
    to_number: Optional[str]
    status: Optional[str]
    duration_seconds: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- CallMessage ---

class CallMessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CallWithMessagesOut(CallOut):
    messages: list[CallMessageOut] = []


# --- Recording ---

class RecordingOut(BaseModel):
    id: uuid.UUID
    call_sid: str
    recording_sid: str
    spaces_key: str
    duration_seconds: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}
