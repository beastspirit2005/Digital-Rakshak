from pydantic import BaseModel, EmailStr, Field

class RegistrationRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(..., description="Role requested by user (e.g., citizen, investigator)")
    department: str | None = None

class RegistrationResponse(BaseModel):
    user_id: str
    status: str
    message: str

class RequestOTPRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
