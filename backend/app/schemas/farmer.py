import re
from datetime import datetime
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

INDIAN_PHONE_REGEX = r"^\+91[6-9]\d{9}$"


def validate_indian_phone(phone: str) -> bool:
    return bool(re.match(INDIAN_PHONE_REGEX, phone))


class FarmerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    full_name: str = Field(default="Farmer", max_length=128)
    phone_number: str = Field(..., description="E.164 Indian mobile format (+91XXXXXXXXXX)")
    language_pref: str = Field(default="te", description="Preferred language (te, hi, en)")

    @field_validator("full_name", mode="before")
    @classmethod
    def check_full_name(cls, v: Any) -> str:
        s = str(v).strip() if v else ""
        return s if len(s) >= 2 else "Farmer"

    @field_validator("language_pref", mode="before")
    @classmethod
    def normalize_lang(cls, v: Any) -> str:
        if not v:
            return "te"
        s = str(v).lower()
        if "te" in s:
            return "te"
        if "hi" in s:
            return "hi"
        return "en"

    @field_validator("phone_number", mode="before")
    @classmethod
    def check_phone_format(cls, v: Any) -> str:
        s = str(v).strip()
        if not re.match(INDIAN_PHONE_REGEX, s):
            raise ValueError(f"Invalid Indian mobile phone format. Expected {INDIAN_PHONE_REGEX}, got: {s}")
        return s


class FarmerCreate(FarmerBase):
    id: Optional[str] = None
    farmer_id: Optional[str] = None


class FarmerRegisterRequest(FarmerBase):
    farmer_id: Optional[str] = None
    id: Optional[str] = None


class FarmerLoginRequest(BaseModel):
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def check_phone_format(cls, v: str) -> str:
        if not validate_indian_phone(v):
            raise ValueError(f"Invalid Indian phone number: '{v}'.")
        return v


class LanguageUpdateRequest(BaseModel):
    language_pref: Literal["te", "hi", "en"]


class FarmerResponse(FarmerBase):
    id: str
    created_at: datetime


class FarmerAuthResponse(BaseModel):
    farmer: FarmerResponse
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400

    # Top-level convenience accessors
    id: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    language_pref: Optional[str] = None
    created_at: Optional[datetime] = None
