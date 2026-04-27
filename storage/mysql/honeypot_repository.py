from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from storage.mysql.connection import create_connection


class MySQLHoneypotRepository:
    def __init__(self, connection=None) -> None:
        self.conn = connection or create_connection()
        self.cursor = self.conn.cursor()

    def close(self) -> None:
        self.cursor.close()
        self.conn.close()

    def log_request(self, *, method: str, path: str, source_ip: str | None, user_agent: str | None, request_headers: dict, response_status_code: int, response_body) -> None:
        body = response_body.encode("utf-8") if isinstance(response_body, str) else response_body
        body = body or b""
        self.cursor.execute(
            """
            INSERT INTO honeypot_request_logs (
                request_id, method, path, source_ip, user_agent, request_headers,
                response_status_code, response_body_hash, response_size
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid4()),
                method,
                path,
                source_ip,
                user_agent,
                json.dumps(request_headers, ensure_ascii=False, default=str),
                response_status_code,
                hashlib.sha256(body).hexdigest(),
                len(body),
            ),
        )
        self.conn.commit()
