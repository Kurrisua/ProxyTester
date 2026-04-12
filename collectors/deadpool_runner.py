from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

from collectors.defaults import DEADPOOL_DIR, DEADPOOL_FIR_PATH


class DeadpoolSeedRunner:
    def __init__(self, project_dir: Path | None = None, logger: logging.Logger | None = None):
        self.project_dir = Path(project_dir or DEADPOOL_DIR)
        self.logger = logger or logging.getLogger(__name__)

    def run(self, timeout_seconds: int = 180) -> dict:
        script_path = self.project_dir / DEADPOOL_FIR_PATH.name
        if not script_path.exists():
            self.logger.error("Deadpool seed script missing: %s", script_path)
            return {
                "success": False,
                "status": "missing_script",
                "message": f"Deadpool seed script not found: {script_path}",
                "projectDir": str(self.project_dir),
            }

        self.logger.info("Starting Deadpool seed refresh: %s", script_path)
        started_at = time.perf_counter()
        try:
            result = subprocess.run(
                ["python", script_path.name],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            elapsed = time.perf_counter() - started_at
            self.logger.warning("Deadpool seed refresh timed out after %.2fs", elapsed)
            return {
                "success": False,
                "status": "timeout",
                "message": f"Deadpool seed refresh timed out after {timeout_seconds}s.",
                "projectDir": str(self.project_dir),
            }
        except FileNotFoundError as exc:
            self.logger.exception("Unable to execute Deadpool seed refresh")
            return {
                "success": False,
                "status": "execution_error",
                "message": str(exc),
                "projectDir": str(self.project_dir),
            }

        elapsed = time.perf_counter() - started_at
        stdout_tail = self._tail(result.stdout)
        stderr_tail = self._tail(result.stderr)
        self.logger.info(
            "Deadpool seed refresh finished in %.2fs with code %s",
            elapsed,
            result.returncode,
        )
        for line in stdout_tail[-10:]:
            self.logger.info("Deadpool stdout: %s", line)
        for line in stderr_tail[-10:]:
            self.logger.warning("Deadpool stderr: %s", line)

        return {
            "success": result.returncode == 0,
            "status": "ok" if result.returncode == 0 else "failed",
            "returnCode": result.returncode,
            "stdoutTail": stdout_tail,
            "stderrTail": stderr_tail,
            "elapsedSeconds": round(elapsed, 2),
            "projectDir": str(self.project_dir),
        }

    @staticmethod
    def _tail(content: str, limit: int = 20) -> list[str]:
        lines = [line for line in content.splitlines() if line.strip()]
        return lines[-limit:]
