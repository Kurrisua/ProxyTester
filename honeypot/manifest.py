from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Union


BASIC_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>ProxyTester Honeypot Static Page</title>
    <link rel="stylesheet" href="/honeypot/assets/site.css">
  </head>
  <body>
    <main id="proxytester-honeypot">
      <h1>ProxyTester Honeypot</h1>
      <p class="stable-copy">This page is intentionally static for proxy tampering checks.</p>
      <form id="stable-form" action="/honeypot/submit" method="post">
        <input name="probe" value="stable" readonly>
      </form>
      <img src="/honeypot/assets/pixel.txt" alt="stable resource marker">
      <script src="/honeypot/assets/site.js"></script>
    </main>
  </body>
</html>
"""

SITE_CSS = "body{font-family:system-ui,sans-serif;background:#fff;color:#111}main{max-width:720px;margin:3rem auto}\n"
SITE_JS = "window.__PROXYTESTER_HONEYPOT__ = 'stable';\n"
PIXEL_TXT = "proxytester-stable-resource\n"
DOWNLOAD_TXT = "proxytester-download-fixture\nversion=1\nsha=stable\n"
FAKE_ZIP = "PK\x03\x04proxytester-fake-zip-fixture\n"
IMAGE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="96" height="48" viewBox="0 0 96 48">
  <rect width="96" height="48" fill="#f8fafc"/>
  <circle cx="24" cy="24" r="12" fill="#2563eb"/>
  <path d="M46 18h34v4H46zm0 8h26v4H46z" fill="#111827"/>
</svg>
"""
COMPLEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>ProxyTester Complex Honeypot</title>
    <link rel="stylesheet" href="/honeypot/assets/site.css">
  </head>
  <body>
    <main id="proxytester-complex-honeypot">
      <h1>Complex static target</h1>
      <section id="resource-list">
        <a href="/honeypot/download/sample.txt">download sample</a>
        <img src="/honeypot/assets/marker.svg" alt="marker">
        <script src="/honeypot/assets/site.js"></script>
      </section>
      <form id="complex-form" action="/honeypot/submit" method="post">
        <input name="email" value="research@example.test" readonly>
      </form>
    </main>
  </body>
</html>
"""


def sha256_body(value: Union[str, bytes]) -> str:
    body = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(body).hexdigest()


@dataclass(frozen=True)
class HoneypotTarget:
    name: str
    path: str
    target_type: str
    content_type: str
    body: Union[str, bytes]
    expected_status_code: int = 200
    expected_sha256: str = field(init=False)
    required_selectors: tuple[str, ...] = ()
    forbidden_tags: tuple[str, ...] = ("iframe",)
    forbidden_attrs_prefix: tuple[str, ...] = ("on",)

    def __post_init__(self) -> None:
        object.__setattr__(self, "expected_sha256", sha256_body(self.body))

    def to_manifest(self, base_url: str = "") -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "url": f"{base_url}{self.path}",
            "targetType": self.target_type,
            "expectedStatusCode": self.expected_status_code,
            "expectedMimeType": self.content_type,
            "expectedSha256": self.expected_sha256,
            "requiredSelectors": list(self.required_selectors),
            "forbiddenTags": list(self.forbidden_tags),
            "forbiddenAttrsPrefix": list(self.forbidden_attrs_prefix),
        }


TARGETS = {
    "/honeypot/static/basic": HoneypotTarget(
        name="basic_static_html",
        path="/honeypot/static/basic",
        target_type="html",
        content_type="text/html; charset=utf-8",
        body=BASIC_HTML,
        required_selectors=("#proxytester-honeypot", "#stable-form"),
    ),
    "/honeypot/assets/site.css": HoneypotTarget(
        name="site_css",
        path="/honeypot/assets/site.css",
        target_type="css",
        content_type="text/css; charset=utf-8",
        body=SITE_CSS,
    ),
    "/honeypot/assets/site.js": HoneypotTarget(
        name="site_js",
        path="/honeypot/assets/site.js",
        target_type="javascript",
        content_type="application/javascript; charset=utf-8",
        body=SITE_JS,
    ),
    "/honeypot/assets/pixel.txt": HoneypotTarget(
        name="pixel_text",
        path="/honeypot/assets/pixel.txt",
        target_type="text",
        content_type="text/plain; charset=utf-8",
        body=PIXEL_TXT,
    ),
    "/honeypot/static/complex": HoneypotTarget(
        name="complex_static_html",
        path="/honeypot/static/complex",
        target_type="html",
        content_type="text/html; charset=utf-8",
        body=COMPLEX_HTML,
        required_selectors=("#proxytester-complex-honeypot", "#complex-form"),
    ),
    "/honeypot/assets/marker.svg": HoneypotTarget(
        name="marker_svg",
        path="/honeypot/assets/marker.svg",
        target_type="image",
        content_type="image/svg+xml; charset=utf-8",
        body=IMAGE_SVG,
    ),
    "/honeypot/download/sample.txt": HoneypotTarget(
        name="download_text",
        path="/honeypot/download/sample.txt",
        target_type="download",
        content_type="text/plain; charset=utf-8",
        body=DOWNLOAD_TXT,
    ),
    "/honeypot/download/sample.zip": HoneypotTarget(
        name="download_zip_fixture",
        path="/honeypot/download/sample.zip",
        target_type="download",
        content_type="application/zip",
        body=FAKE_ZIP,
    ),
}


def list_targets(base_url: str = "") -> list[dict]:
    return [target.to_manifest(base_url) for target in TARGETS.values()]
