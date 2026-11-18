"""시드 직원 계정에 운영자가 입력한 비밀번호와 복구 코드를 설정합니다."""

import argparse
import secrets
from getpass import getpass

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.database import create_workplace_engine, lock_sqlite_write

from .auth_model import Account
from .auth_service import password_hash, recovery_hash


def provision(engine: Engine, employee_id: str, password: str) -> str:
    """조직 구성원 계정의 자격 증명을 설정하고 기존 세션을 폐기합니다."""
    if not 10 <= len(password) <= 256:
        raise ValueError("비밀번호는 10~256자여야 합니다.")
    code = secrets.token_urlsafe(24)
    encoded = password_hash(password, secrets.token_bytes(16))
    with Session(engine) as session, session.begin():
        lock_sqlite_write(session)
        account = session.scalar(
            select(Account)
            .where(Account.employee_id == employee_id.upper())
            .with_for_update()
        )
        if account is None:
            raise ValueError(
                "직원 계정을 찾지 못했습니다. 사번과 Alembic 적용 상태를 확인하세요."
            )
        account.password_hash = encoded
        account.recovery_hash = recovery_hash(code)
        account.session_version += 1
    return code


def main() -> int:
    """비밀번호를 화면에 노출하지 않고 관리자 터미널에서 입력받습니다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("employee_id")
    args = parser.parse_args()
    password = getpass("새 비밀번호: ")
    if password != getpass("새 비밀번호 확인: "):
        print("비밀번호가 일치하지 않습니다.")
        return 1
    engine = create_workplace_engine()
    try:
        code = provision(engine, args.employee_id, password)
    except ValueError as error:
        print(error)
        return 1
    finally:
        engine.dispose()
    print(f"아이디: staff:{args.employee_id.lower()}\n복구 코드: {code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
