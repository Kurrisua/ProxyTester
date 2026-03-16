from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(eq=False)
class ProxyModel:
    ip: str
    port: int
    source: str = "unknown"
    is_alive: bool = False
    http: bool = False
    https: bool = False
    socks5: bool = False
    proxy_type: str | None = None
    anonymity: str | None = None
    geo_source: str | None = None
    exit_ip: str | None = None
    country: str | None = None
    city: str | None = None
    isp: str | None = None
    response_time: float | None = None
    business_score: int = 0
    success_count: int = 0
    fail_count: int = 0
    last_check_time: datetime | None = None
    quality_score: int = 0
    security_risk: str = "unknown"
    security_flags: list[str] = field(default_factory=list)
    security_evidence: dict = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.ip, self.port))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ProxyModel) and self.ip == other.ip and self.port == other.port

    @property
    def is_usable(self) -> bool:
        return self.is_alive and bool(self.proxy_type)

    def update_proxy_type(self) -> None:
        protocols: list[str] = []
        if self.http:
            protocols.append("HTTP")
        if self.https:
            protocols.append("HTTPS")
        if self.socks5:
            protocols.append("SOCKS5")

        if not protocols:
            self.proxy_type = None
        elif len(protocols) == 1:
            self.proxy_type = protocols[0]
        elif len(protocols) == 2:
            self.proxy_type = f"{protocols[0]}_{protocols[1]}"
        else:
            self.proxy_type = "ALL"

    def update_check_time(self) -> None:
        self.last_check_time = datetime.now()

    def record_success(self) -> None:
        self.success_count += 1
        self.is_alive = True

    def record_fail(self) -> None:
        self.fail_count += 1

    def to_db_dict(self) -> dict:
        return {
            "ip": self.ip,
            "port": self.port,
            "source": self.source,
            "country": self.country,
            "city": self.city,
            "proxy_type": self.proxy_type,
            "anonymity": self.anonymity,
            "response_time": self.response_time,
            "business_score": self.business_score,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "last_check_time": self.last_check_time,
            "is_alive": 1 if self.is_alive else 0,
            "quality_score": self.quality_score,
            "security_risk": self.security_risk,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "ProxyModel":
        proxy = cls(
            ip=row["ip"],
            port=int(row["port"]),
            source=row.get("source") or "unknown",
        )
        proxy.is_alive = bool(row.get("is_alive"))
        proxy.country = row.get("country")
        proxy.city = row.get("city")
        proxy.proxy_type = row.get("proxy_type")
        proxy.anonymity = row.get("anonymity")
        proxy.response_time = row.get("response_time")
        proxy.business_score = row.get("business_score", 0) or 0
        proxy.success_count = row.get("success_count", 0) or 0
        proxy.fail_count = row.get("fail_count", 0) or 0
        proxy.last_check_time = row.get("last_check_time")
        proxy.quality_score = row.get("quality_score", 0) or 0
        proxy.security_risk = row.get("security_risk", "unknown") or "unknown"
        if proxy.proxy_type:
            proxy.http = "HTTP" in proxy.proxy_type
            proxy.https = "HTTPS" in proxy.proxy_type
            proxy.socks5 = "SOCKS5" in proxy.proxy_type
        return proxy
