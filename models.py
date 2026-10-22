
import datetime
from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username cannot be empty.")
        return value


class UserLogin(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    id: int
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0, allow_inf_nan=False)
    category: str = Field(default="General", min_length=1, max_length=50)
    date: datetime.date = Field(
        default_factory=datetime.date.today
    )

    @field_validator("title", "category")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value


class Expense(ExpenseCreate):
    id: int = Field(gt=0)
