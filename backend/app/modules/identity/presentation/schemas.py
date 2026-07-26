"""
Identity presentation: Pydantic request/response schemas matching
TRADEOS_API_SPECIFICATION.md §6.1 field-for-field.
"""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    # §6.1: "minimum length per Section 9 validation rules" — §9 never
    # states a concrete number. 8 is a documented implementation default
    # (CHANGELOG.md, Sprint 1.1) until the spec states one explicitly.
    password: str = Field(min_length=8)


class RegisterResponse(BaseModel):
    user_id: str
    email: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str
