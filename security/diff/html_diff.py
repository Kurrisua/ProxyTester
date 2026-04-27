from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser

from security.access.models import AccessResult


@dataclass
class HtmlDiffSummary:
    direct_hash: str | None
    proxy_hash: str | None
    status_changed: bool
    hash_changed: bool
    added_tags: list[str] = field(default_factory=list)
    removed_tags: list[str] = field(default_factory=list)
    added_external_urls: list[str] = field(default_factory=list)
    added_event_handlers: list[str] = field(default_factory=list)
    form_action_changed: bool = False

    @property
    def has_dom_risk(self) -> bool:
        return bool(
            set(self.added_tags).intersection({"script", "iframe"})
            or self.added_external_urls
            or self.added_event_handlers
            or self.form_action_changed
        )

    def to_dict(self) -> dict:
        return {
            "directHash": self.direct_hash,
            "proxyHash": self.proxy_hash,
            "statusChanged": self.status_changed,
            "hashChanged": self.hash_changed,
            "addedTags": self.added_tags,
            "removedTags": self.removed_tags,
            "addedExternalUrls": self.added_external_urls,
            "addedEventHandlers": self.added_event_handlers,
            "formActionChanged": self.form_action_changed,
            "hasDomRisk": self.has_dom_risk,
        }


class _HtmlProbeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.urls: list[str] = []
        self.event_handlers: list[str] = []
        self.form_actions: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        attr_map = {key.lower(): value or "" for key, value in attrs}
        for attr_name, attr_value in attr_map.items():
            if attr_name.startswith("on"):
                self.event_handlers.append(f"{tag}.{attr_name}")
            if attr_name in {"src", "href"} and attr_value:
                self.urls.append(attr_value)
        if tag == "form":
            self.form_actions.append(attr_map.get("action", ""))


def compare_access_results(direct: AccessResult, proxied: AccessResult) -> HtmlDiffSummary:
    direct_probe = _parse(direct.body_text)
    proxy_probe = _parse(proxied.body_text)
    return HtmlDiffSummary(
        direct_hash=direct.body_bytes_sha256,
        proxy_hash=proxied.body_bytes_sha256,
        status_changed=direct.status_code != proxied.status_code,
        hash_changed=direct.body_bytes_sha256 != proxied.body_bytes_sha256,
        added_tags=sorted(set(proxy_probe.tags) - set(direct_probe.tags)),
        removed_tags=sorted(set(direct_probe.tags) - set(proxy_probe.tags)),
        added_external_urls=sorted(set(proxy_probe.urls) - set(direct_probe.urls)),
        added_event_handlers=sorted(set(proxy_probe.event_handlers) - set(direct_probe.event_handlers)),
        form_action_changed=direct_probe.form_actions != proxy_probe.form_actions,
    )


def _parse(body_text: str | None) -> _HtmlProbeParser:
    parser = _HtmlProbeParser()
    if body_text:
        parser.feed(body_text)
    return parser
