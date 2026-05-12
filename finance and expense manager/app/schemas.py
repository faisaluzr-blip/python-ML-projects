from pydantic import BaseModel, EmailStr, Field


class SignupIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8)
    currency: str = "USD"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class TransactionIn(BaseModel):
    kind: str = Field(pattern="^(income|expense)$")
    amount: float = Field(gt=0)
    currency: str = "USD"
    category: str | None = None
    merchant: str = ""
    description: str = ""
    occurred_on: str


class BudgetIn(BaseModel):
    category: str
    limit_amount: float = Field(gt=0)
    period: str = "monthly"


class GoalIn(BaseModel):
    name: str
    target_amount: float = Field(gt=0)
    saved_amount: float = Field(ge=0)
    deadline: str


class ReminderIn(BaseModel):
    name: str
    amount: float = Field(gt=0)
    currency: str = "USD"
    due_day: int = Field(ge=1, le=31)
    category: str = "Subscriptions"
    active: bool = True


class AssistantIn(BaseModel):
    message: str


class VoiceIn(BaseModel):
    transcript: str
    occurred_on: str | None = None
