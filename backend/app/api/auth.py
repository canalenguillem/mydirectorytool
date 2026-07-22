import hashlib
import hmac
import os
import secrets
import time

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel


router = APIRouter()
COOKIE_NAME = "ai_maps_session"
SESSION_SECONDS = int(os.environ.get("AUTH_SESSION_SECONDS", "43200"))


class LoginRequest(BaseModel):
    username: str
    password: str


def _credentials() -> tuple[str, str, str]:
    username = os.environ.get("AUTH_USERNAME", "enguillem")
    password = os.environ.get("AUTH_PASSWORD", "")
    secret = os.environ.get("AUTH_SECRET", "")
    if not password or not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El login no está configurado en el servidor",
        )
    return username, password, secret


def _signature(value: str, secret: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def create_session(username: str) -> str:
    _, _, secret = _credentials()
    expires = int(time.time()) + SESSION_SECONDS
    payload = f"{username}:{expires}:{secrets.token_hex(16)}"
    return f"{payload}:{_signature(payload, secret)}"


def valid_session(token: str | None) -> bool:
    if not token:
        return False
    try:
        username, expires, nonce, signature = token.split(":", 3)
        expected_username, _, secret = _credentials()
        payload = f"{username}:{expires}:{nonce}"
        return (
            hmac.compare_digest(username, expected_username)
            and int(expires) > int(time.time())
            and hmac.compare_digest(signature, _signature(payload, secret))
        )
    except (HTTPException, ValueError):
        return False


@router.post("/login")
def login(data: LoginRequest, response: Response):
    username, password, _ = _credentials()
    if not (
        hmac.compare_digest(data.username, username)
        and hmac.compare_digest(data.password, password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    response.set_cookie(
        key=COOKIE_NAME,
        value=create_session(username),
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=os.environ.get("AUTH_COOKIE_SECURE", "false").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"username": username}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me")
def me(request: Request):
    if not valid_session(request.cookies.get(COOKIE_NAME)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return {"username": os.environ.get("AUTH_USERNAME", "enguillem")}
