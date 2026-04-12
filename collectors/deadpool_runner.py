from __future__ import annotations

import subprocess
from pathlib import Path

from collectors.defaults import DEADPOOL_DIR, DEADPOOL_FIR_PATH


class DeadpoolSeedRunner:
    def __init__(self, project_dir: Path | None = None):
        self.project_dir = Path(project_dir or DEADPOOL_DIR)

    def run(self, timeout_seconds: int = 180) -> dict:
        script_path = self.project_dir / DEADPOOL_FIR_PATH.name
        if not script_path.exists():
            return {
                "success": False,
                "status": "missing_script",
                "message": f"Deadpool seed script not found: {script_path}",
                "projectDir": str(self.project_dir),
            }

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
            return {
                "success": False,
                "status": "timeout",
                "message": f"Deadpool seed refresh timed out after {timeout_seconds}s.",
                "projectDir": str(self.project_dir),
            }
        except FileNotFoundError as exc:
            return {
                "success": False,
                "status": "execution_error",
                "message": str(exc),
                "projectDir": str(self.project_dir),
            }

        return {
            "success": result.returncode == 0,
            "status": "ok" if result.returncode == 0 else "failed",
            "returnCode": result.returncode,
            "stdoutTail": self._tail(result.stdout),
            "stderrTail": self._tail(result.stderr),
            "projectDir": str(self.project_dir),
        }

    @staticmethod
    def _tail(content: str, limit: int = 20) -> list[str]:
        lines = [line for line in content.splitlines() if line.strip()]
        return lines[-limit:]
