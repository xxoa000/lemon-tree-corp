"""계정의 역할 확인 및 개인 프로필과 사진을 관리합니다."""

from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import lock_sqlite_write

from .auth_model import Account
from .auth_schemas import AccountProfile, ProfileUpdate, StaffAccount
from .auth_schemas import Session as SessionView

MAX_AVATAR = 5 * 1024 * 1024


def account_id(subject: str) -> int:
    """가입 계정에 연결된 세션의 내부 식별자를 읽습니다."""
    if not subject.startswith("acct:"):
        raise HTTPException(404, "회원 계정이 필요합니다.")
    return int(subject[5:])


def account_view(row: Account) -> AccountProfile:
    """민감한 자격 증명을 제외한 소유자용 프로필을 만듭니다."""
    return AccountProfile(
        username=row.username,
        display_name=row.display_name or row.username,
        email="" if row.email.endswith("@lemontree.invalid") else row.email,
        phone=row.phone,
        bio=row.bio,
        role=row.role,
        has_avatar=row.avatar is not None,
    )


def session_view(engine: Engine, subject: str) -> SessionView:
    """계정 식별자와 업무 담당자 식별자, 권한을 반환합니다."""
    if not subject.startswith("acct:"):
        return SessionView(employee_id=subject, org_employee_id=subject)
    with Session(engine) as db:
        row = db.get(Account, account_id(subject))
        if row is None:
            raise HTTPException(401, "로그인이 필요합니다.")
        return SessionView(
            employee_id=subject, org_employee_id=row.employee_id, role=row.role
        )


def read_profile(engine: Engine, subject: str) -> AccountProfile:
    """로그인한 계정의 프로필을 읽습니다."""
    with Session(engine) as db:
        row = db.get(Account, account_id(subject))
        if row is None:
            raise HTTPException(404, "프로필을 찾을 수 없습니다.")
        return account_view(row)


def update_profile(engine: Engine, subject: str, data: ProfileUpdate) -> AccountProfile:
    """로그인한 계정의 이름, 이메일, 전화번호, 소개를 수정합니다."""
    try:
        with Session(engine) as db, db.begin():
            lock_sqlite_write(db)
            row = db.get(Account, account_id(subject), with_for_update=True)
            if row is None:
                raise HTTPException(404, "프로필을 찾을 수 없습니다.")
            row.display_name, row.email, row.phone, row.bio = (
                data.display_name,
                data.email.lower(),
                data.phone,
                data.bio,
            )
            return account_view(row)
    except IntegrityError as error:
        raise HTTPException(409, "이미 사용 중인 이메일입니다.") from error


def read_avatar(engine: Engine, subject: str) -> bytes:
    """로그인한 계정에 저장된 프로필 사진을 가져옵니다."""
    with Session(engine) as db:
        row = db.get(Account, account_id(subject))
        if not row or not row.avatar:
            raise HTTPException(404, "프로필 사진이 없습니다.")
        return row.avatar


def update_avatar(engine: Engine, subject: str, upload: UploadFile) -> None:
    """JPEG·PNG·WebP를 검사하고 최대 512픽셀 WebP로 저장합니다."""
    raw = upload.file.read(MAX_AVATAR + 1)
    if len(raw) > MAX_AVATAR:
        raise HTTPException(413, "프로필 사진은 최대 5MB입니다.")
    try:
        with Image.open(BytesIO(raw), formats=("JPEG", "PNG", "WEBP")) as original:
            if original.width * original.height > 16_000_000:
                raise HTTPException(422, "프로필 사진은 최대 1,600만 픽셀입니다.")
            image = ImageOps.exif_transpose(original).convert("RGBA")
            image.thumbnail((512, 512))
            encoded = BytesIO()
            image.save(encoded, "WEBP", quality=85)
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(
            422, "유효한 JPEG, PNG 또는 WebP 이미지를 올려 주세요."
        ) from error

    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        row = db.get(Account, account_id(subject), with_for_update=True)
        if row is None:
            raise HTTPException(404, "프로필을 찾을 수 없습니다.")
        row.avatar = encoded.getvalue()


def list_staff(engine: Engine, subject: str) -> list[StaffAccount]:
    """관리자 권한을 검증한 뒤 직원 계정 상태를 반환합니다."""
    if session_view(engine, subject).role != "admin":
        raise HTTPException(403, "관리자 권한이 필요합니다.")
    with Session(engine) as db:
        rows = db.scalars(
            select(Account)
            .where(Account.employee_id.is_not(None))
            .order_by(Account.employee_id)
        )
        return [
            StaffAccount(
                employee_id=row.employee_id,
                username=row.username,
                display_name=row.display_name,
                role=row.role,
                enabled=row.password_hash != "!",
            )
            for row in rows
            if row.employee_id is not None
        ]
