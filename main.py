
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError
import sqlite3

import database
from models import (
    UserCreate,
    UserLogin,
    UserPublic,
    TokenResponse,
    Expense,
    ExpenseCreate,
)


SECRET_KEY = os.getenv("FINTRACK_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "Set the FINTRACK_SECRET_KEY environment variable before starting the API."
    )

ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60
password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(
    title="FinTrack API",
    description="Expense tracker with user accounts",
    version="2.0.0",
    lifespan=lifespan,
)


def create_access_token(user_id: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expires},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user_id = int(payload["sub"])
    except (InvalidTokenError, ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired login. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = database.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found. Please log in again.",
        )
    return user


@app.get("/")
def home():
    return {"message": "Welcome to FinTrack API"}


@app.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
def register(user: UserCreate):
    try:
        user_id = database.create_user(
            user.username,
            password_hash.hash(user.password),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already taken.",
        )

    return {"id": user_id, "username": user.username.strip()}


@app.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin):
    user = database.get_user_by_username(credentials.username)

    if user is None or not password_hash.verify(
        credentials.password, user["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    return {
        "access_token": create_access_token(user["id"]),
        "token_type": "bearer",
        "username": user["username"],
    }


@app.get("/me", response_model=UserPublic)
def get_me(user=Depends(get_current_user)):
    return {"id": user["id"], "username": user["username"]}


@app.post(
    "/expenses",
    response_model=Expense,
    status_code=status.HTTP_201_CREATED,
)
def create_expense(
    expense: ExpenseCreate,
    user=Depends(get_current_user),
):
    expense_id = database.add_expense(
        expense.title,
        expense.amount,
        expense.category,
        expense.date.isoformat(),
        user["id"],
    )
    return Expense(id=expense_id, **expense.model_dump())


@app.get("/expenses", response_model=list[Expense])
def list_expenses(user=Depends(get_current_user)):
    return [dict(row) for row in database.get_expenses(user["id"])]


@app.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_expense(
    expense_id: int,
    user=Depends(get_current_user),
):
    if not database.delete_expense(expense_id, user["id"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found.",
        )
    return None
