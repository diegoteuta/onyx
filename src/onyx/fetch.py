"""Cliente HTTP cortes: robots.txt, rate limit y reintentos con backoff."""

from __future__ import annotations

import time
from types import TracebackType
from urllib.robotparser import RobotFileParser

import httpx

from onyx.config import SiteProfile

RETRY_STATUS = {429, 500, 502, 503, 504}


class PoliteFetcher:
    """Realiza peticiones respetando robots.txt y un intervalo minimo por host."""

    def __init__(
        self,
        profile: SiteProfile,
        *,
        timeout: float = 20.0,
        ignore_robots: bool = False,
        max_attempts: int = 3,
    ) -> None:
        self.profile = profile
        self.ignore_robots = ignore_robots
        self.max_attempts = max_attempts
        self.min_interval = profile.rate_limit_seconds
        self._last_request = 0.0
        self._robots: RobotFileParser | None = None
        self._robots_loaded = False
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": profile.user_agent, "Accept-Language": profile.lang},
        )

    def __enter__(self) -> PoliteFetcher:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._client.close()

    def _load_robots(self) -> None:
        if self._robots_loaded:
            return
        self._robots_loaded = True
        parser = RobotFileParser()
        try:
            response = self._client.get(f"{self.profile.base_url}/robots.txt")
        except httpx.HTTPError:
            return
        if response.status_code != 200:
            return
        parser.parse(response.text.splitlines())
        delay = parser.crawl_delay(self.profile.user_agent) or parser.crawl_delay("*")
        if delay:
            self.min_interval = max(self.min_interval, float(delay))
        self._robots = parser

    def allowed(self, url: str) -> bool:
        """True si robots.txt permite leer esa URL para nuestro user-agent."""
        if self.ignore_robots:
            return True
        self._load_robots()
        if self._robots is None:
            return True
        return self._robots.can_fetch(self.profile.user_agent, url)

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request = time.monotonic()

    def get(self, url: str, *, etag: str = "", last_modified: str = "") -> httpx.Response | None:
        """GET con reintentos. Devuelve None si robots.txt lo prohibe o falla la red."""
        if not self.allowed(url):
            return None

        headers: dict[str, str] = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        for attempt in range(self.max_attempts):
            self._throttle()
            try:
                response = self._client.get(url, headers=headers)
            except httpx.HTTPError:
                if attempt == self.max_attempts - 1:
                    return None
                time.sleep(2**attempt)
                continue
            if response.status_code in RETRY_STATUS and attempt < self.max_attempts - 1:
                time.sleep(2**attempt)
                continue
            return response
        return None

    def text(self, url: str) -> str | None:
        """Cuerpo de la respuesta si fue 200; None en cualquier otro caso."""
        response = self.get(url)
        if response is None or response.status_code != 200:
            return None
        return response.text
