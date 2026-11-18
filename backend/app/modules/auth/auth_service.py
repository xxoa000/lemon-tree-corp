"""계정 등록, 복구 및 JWT 세션을 처리합니다."""

import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth_model import Account
from .auth_schemas import Login, Recovery, Reset, Signup

EMPLOYEE_ID = "LT-011"
SESSION_SECONDS = 8 * 60 * 60


def configured_secret() -> str:
    """JWT 서명 키의 최소 길이를 확인합니다."""
    secret = os.getenv("WORKPLACE_JWT_SECRET", "")
    if len(secret.encode()) < 32:
        raise HTTPException(503, "로그인 설정이 필요합니다.")
    return secret


def password_hash(password: str, salt: bytes) -> str:
    """비밀번호를 솔트와 함께 scrypt 방식으로 해시합니다."""
    key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}:{key.hex()}"


def recovery_hash(code: str) -> str:
    """무작위 복구 코드의 검증용 해시를 반환합니다."""
    return hashlib.sha256(code.encode()).hexdigest()


def signup(engine: Engine, data: Signup) -> str:
    """계정을 만들고 사용자에게 한 번 표시할 복구 코드를 반환합니다."""
    username = data.username.lower()
    if username == os.getenv("WORKPLACE_USERNAME", "junior").lower():
        raise HTTPException(409, "이미 사용 중인 아이디 또는 이메일입니다.")
    code = secrets.token_urlsafe(24)
    try:
        with Session(engine) as db, db.begin():
            db.add(
                Account(
                    username=username,
                    email=data.email.lower(),
                    password_hash=password_hash(data.password, secrets.token_bytes(16)),
                    recovery_hash=recovery_hash(code),
                    session_version=1,
                )
            )
    except IntegrityError as error:
        raise HTTPException(409, "이미 사용 중인 아이디 또는 이메일입니다.") from error
    return code


def verify_recovery(db: Session, data: Recovery) -> Account:
    """가입 이메일과 복구 코드가 일치하는 계정을 확인합니다."""
    account = db.scalar(select(Account).where(Account.email == data.email.lower()))
    if not account or not hmac.compare_digest(
        account.recovery_hash, recovery_hash(data.recovery_code)
    ):
        raise HTTPException(400, "이메일 또는 복구 코드를 확인해 주세요.")
    return account


def find_username(engine: Engine, data: Recovery) -> str:
    """검증된 복구 요청에 로그인 아이디를 반환합니다."""
    with Session(engine) as db:
        return verify_recovery(db, data).username


def reset_password(engine: Engine, data: Reset) -> str:
    """비밀번호와 복구 코드를 교체하고 기존 JWT를 만료 처리합니다."""
    code = secrets.token_urlsafe(24)
    new_hash = password_hash(data.password, secrets.token_bytes(16))
    with Session(engine) as db, db.begin():
        db.execute(text("BEGIN IMMEDIATE"))
        account = verify_recovery(db, data)
        account.password_hash = new_hash
        account.recovery_hash = recovery_hash(code)
        account.session_version += 1
    return code


def issue_token(engine: Engine, credentials: Login) -> tuple[str, str]:
    """자격 증명을 확인하고 사용자 식별자와 JWT를 반환합니다."""
    secret = configured_secret()
    username = credentials.username.lower()
    version = 0
    if username == os.getenv("WORKPLACE_USERNAME", "junior").lower():
        password = os.getenv("WORKPLACE_PASSWORD", "")
        if not password or not hmac.compare_digest(
            credentials.password.encode(), password.encode()
        ):
            raise HTTPException(401, "아이디 또는 비밀번호를 확인해 주세요.")
        subject = EMPLOYEE_ID
    else:
        with Session(engine) as db:
            account = db.scalar(select(Account).where(Account.username == username))
            salt = (
                bytes.fromhex(account.password_hash.split(":")[0])
                if account
                else bytes(16)
            )
            candidate = password_hash(credentials.password, salt)
            if not account or not hmac.compare_digest(candidate, account.password_hash):
                raise HTTPException(401, "아이디 또는 비밀번호를 확인해 주세요.")
            subject = f"acct:{account.id}"
            version = account.session_version

    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": subject,
            "ver": version,
            "iat": now,
            "exp": now + timedelta(seconds=SESSION_SECONDS),
        },
        secret,
        algorithm="HS256",
    )
    return subject, token


def authenticated_employee(engine: Engine, token: str | None) -> str:
    """JWT 유효성과 가입 계정의 세션 버전을 확인합니다."""
    if token:
        try:
            claims = jwt.decode(
                token,
                configured_secret(),
                algorithms=["HS256"],
                options={"require": ["exp", "iat", "sub"]},
            )
            subject = claims["sub"]
            if subject == EMPLOYEE_ID:
                return EMPLOYEE_ID
            if subject.startswith("acct:") and subject[5:].isdigit():
                with Session(engine) as db:
                    account = db.get(Account, int(subject[5:]))
                    if account and claims.get("ver") == account.session_version:
                        return subject
        except jwt.InvalidTokenError:
            pass
    raise HTTPException(401, "로그인이 필요합니다.")
