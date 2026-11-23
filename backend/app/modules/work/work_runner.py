"""전용 호스트에서 승인된 개발 요청을 Codex CLI로 실행합니다."""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Timer

from sqlalchemy import Engine

from app.database import create_workplace_engine, upgrade_workplace

from . import work_service
from .work_schemas import WorkView

PATCH_LIMIT = 120_000
PHASES = {
    "agent_message": "결과 요약 작성",
    "command_execution": "명령 및 테스트 실행",
    "file_change": "파일 수정",
}


def git(repo: Path, *args: str) -> bytes:
    """설정한 저장소에서 제한된 Git 명령을 실행합니다."""
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        stderr=subprocess.DEVNULL,
        timeout=30,
    )


def collect_patch(repo: Path, base: str) -> tuple[str, bool]:
    """커밋된 변경과 미커밋 변경, 새 파일을 기준 커밋과 비교합니다."""
    git(repo, "add", "--intent-to-add", "--", ".")
    with tempfile.TemporaryFile() as output:
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                base,
                "--",
            ],
            stdout=output,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=30,
        )
        output.seek(0)
        raw = output.read(PATCH_LIMIT + 1)
    return raw[:PATCH_LIMIT].decode("utf-8", errors="replace"), len(raw) > PATCH_LIMIT


def terminate(process: subprocess.Popen) -> None:
    """실행 제한에 도달하면 Codex와 자식 프로세스를 종료합니다."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def execute(
    engine: Engine, work: WorkView, source: Path, codex: str, env: dict
) -> None:
    """격리 저장소에서 실행하고 파일 변경과 토큰 사용량을 남깁니다."""
    started = False
    tokens = None
    try:
        with tempfile.TemporaryDirectory(prefix="lemontree-codex-") as directory:
            repo = Path(directory) / "repo"
            git(
                source,
                "clone",
                "--quiet",
                "--no-local",
                "--no-recurse-submodules",
                "--",
                str(source),
                str(repo),
            )
            git(repo, "remote", "remove", "origin")
            base = git(repo, "rev-parse", "HEAD").decode().strip()
            work_service.progress(engine, work.id, "Codex 작업 중")
            prompt = (
                f"담당 직원 사번: {work.employee_id}\n제목: {work.title}\n"
                f"승인된 요청:\n{work.prompt}\n\n"
                "이 복제본에서만 작업하고 테스트하세요. 원격으로 푸시하지 말고 "
                "수정 내용과 검증 결과를 한국어로 요약하세요."
            )
            image_paths = []
            for position, content in enumerate(
                work_service.execution_images(engine, work.id), 1
            ):
                image = Path(directory) / f"attachment-{position}.png"
                image.write_bytes(content)
                image_paths.append(str(image))
            image_args = ["--image", ",".join(image_paths)] if image_paths else []
            with tempfile.TemporaryFile() as request:
                request.write(prompt.encode())
                request.seek(0)
                with subprocess.Popen(
                    [
                        codex,
                        "--ask-for-approval",
                        "never",
                        "exec",
                        "--json",
                        "--ephemeral",
                        "--ignore-user-config",
                        "--sandbox",
                        "workspace-write",
                        "-c",
                        "sandbox_workspace_write.network_access=false",
                        "-c",
                        'shell_environment_policy.inherit="none"',
                        *image_args,
                        "-",
                    ],
                    cwd=repo,
                    env=env,
                    stdin=request,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                ) as process:
                    started = True
                    timer = Timer(work_service.RUN_TIMEOUT, terminate, args=(process,))
                    timer.start()
                    phase = ""
                    summary = ""
                    completed = False
                    try:
                        assert process.stdout is not None
                        for line in process.stdout:
                            try:
                                event = json.loads(line)
                            except (ValueError, UnicodeError):
                                continue
                            if not isinstance(event, dict):
                                continue
                            item = event.get("item") or {}
                            kind = item.get("type")
                            next_phase = PHASES.get(kind)
                            if next_phase and phase != next_phase:
                                work_service.progress(engine, work.id, next_phase)
                                phase = next_phase
                            if (
                                event.get("type") == "item.completed"
                                and kind == "agent_message"
                            ):
                                summary = str(item.get("text", ""))[:4000]
                            if event.get("type") == "turn.completed":
                                usage = event.get("usage", {})
                                tokens = sum(
                                    int(usage.get(key, 0))
                                    for key in ("input_tokens", "output_tokens")
                                )
                                completed = True
                        success = process.wait() == 0 and completed
                    finally:
                        timer.cancel()
                        if process.poll() is None:
                            terminate(process)
                changes, truncated = collect_patch(repo, base)
                if not success:
                    summary = "Codex 실행이 완료되지 않았습니다. 실행기의 인증 또는 실행 제한을 확인하세요."
                elif not summary:
                    summary = "Codex 실행이 완료되었습니다."
                if truncated:
                    summary += "\n변경 내용이 커서 검토용 패치의 앞부분만 표시합니다."
                work_service.finish(
                    engine,
                    work.id,
                    summary,
                    success=success,
                    started=started,
                    tokens=tokens,
                    changes=changes,
                )
    except (OSError, ValueError, subprocess.SubprocessError):
        work_service.finish(
            engine,
            work.id,
            "작업 공간 준비 또는 실행 결과 수집에 실패했습니다.",
            started=started,
            tokens=tokens,
        )


def main() -> None:
    """설정된 Git 체크아웃만 대상으로 최대 두 작업을 병행합니다."""
    configured = os.getenv("LEMON_CODEX_REPO")
    codex = shutil.which("codex")
    if not configured or not codex or not os.getenv("CODEX_HOME"):
        sys.exit("LEMON_CODEX_REPO, 전용 CODEX_HOME, Codex CLI가 필요합니다.")
    repo = Path(configured).resolve()
    git(repo, "rev-parse", "--verify", "HEAD")
    env = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "CODEX_HOME", "LANG", "TMPDIR", "OPENAI_API_KEY"}
    }
    env["CODEX_HOME"] = str(Path(env["CODEX_HOME"]).resolve())
    if Path(env["CODEX_HOME"]).is_relative_to(repo):
        sys.exit("CODEX_HOME은 작업 저장소 밖에 두세요.")
    engine = create_workplace_engine()
    upgrade_workplace(engine)
    try:
        with ThreadPoolExecutor(max_workers=2) as workers:
            running = set()
            while True:
                for future in tuple(running):
                    if future.done():
                        future.result()
                        running.remove(future)
                if len(running) < 2 and (work := work_service.claim(engine)):
                    running.add(workers.submit(execute, engine, work, repo, codex, env))
                else:
                    time.sleep(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
