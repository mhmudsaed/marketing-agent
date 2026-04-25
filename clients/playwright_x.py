"""Playwright publisher for X/Twitter using a persistent browser profile."""
import re
from dataclasses import dataclass
from typing import Optional

from config.settings import settings
from utils.logger import logger


class XPublishError(Exception):
    """Base publishing error."""


class XLoginRequired(XPublishError):
    """Raised when the persistent browser profile is not logged into X."""


class XPlaywrightUnavailable(XPublishError):
    """Raised when Playwright or browser binaries are not installed."""


@dataclass
class XPublishResult:
    status: str
    message: str
    platform_post_url: Optional[str] = None


class XPlaywrightPublisher:
    """Automates a single X post through the web composer."""

    X_MAX_CHARS = 280
    _login_playwright = None
    _login_context = None

    def __init__(self):
        self.user_data_dir = settings.PLAYWRIGHT_USER_DATA_DIR
        self.headless = settings.PLAYWRIGHT_HEADLESS
        self.slow_mo = settings.PLAYWRIGHT_SLOW_MO_MS
        self.browser_channel = settings.PLAYWRIGHT_BROWSER_CHANNEL.strip() or None
        self.compose_url = settings.X_COMPOSE_URL
        self.login_url = settings.X_LOGIN_URL
        self.dry_run = settings.PLAYWRIGHT_DRY_RUN

    def format_post_text(self, headline: str = "", body: str = "", cta: str = "", hashtags: Optional[list[str]] = None) -> str:
        parts = [headline, body, cta, " ".join(hashtags or [])]
        text = "\n\n".join(part.strip() for part in parts if part and part.strip())
        text = self._strip_markdown(text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    def format_x_post_text(self, headline: str = "", body: str = "", cta: str = "", hashtags: Optional[list[str]] = None) -> str:
        """Create an X-ready single post from longer generated content."""
        text = self.format_post_text(headline, body, cta, hashtags)
        if len(text) <= self.X_MAX_CHARS:
            return text

        tag_text = self._format_hashtags(hashtags or [])
        lines = self._meaningful_lines("\n".join([headline or "", body or "", cta or ""]))
        if not lines:
            return self._fit_with_suffix(text, tag_text)

        pieces = []
        if headline:
            pieces.append(self._strip_markdown(headline).strip())
        for line in lines:
            if line.lower() not in {piece.lower() for piece in pieces}:
                pieces.append(line)
            if len(" ".join(pieces)) >= 210:
                break
        if cta:
            clean_cta = self._strip_markdown(cta).strip()
            if clean_cta and clean_cta.lower() not in {piece.lower() for piece in pieces}:
                pieces.append(clean_cta)

        compact = "\n\n".join(piece for piece in pieces if piece)
        return self._fit_with_suffix(compact, tag_text)

    async def check_login(self) -> XPublishResult:
        """Open X with the persistent profile and determine if a session exists."""
        playwright, context, should_close = await self._context_for_work()
        try:
            page = await context.new_page()
            await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
            if await self._is_login_required(page):
                return XPublishResult(
                    status="login_required",
                    message="X login is required. Open the login window once, sign in, then publish again.",
                )
            return XPublishResult(status="ready", message="X session is ready.")
        finally:
            if should_close:
                await context.close()
                await playwright.stop()

    async def open_login(self) -> XPublishResult:
        """Open a persistent browser window at X login and keep it alive."""
        context = await self._ensure_login_context()
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(self.login_url, wait_until="domcontentloaded", timeout=60000)
        await page.bring_to_front()
        return XPublishResult(
            status="login_opened",
            message="X login window opened and will stay attached to this app. Sign in there, then return and click Publish again.",
        )

    async def publish_text(self, text: str) -> XPublishResult:
        """Publish text to X. The app-level click is the only user action."""
        if not text:
            raise XPublishError("Post content is empty.")
        if len(text) > 280:
            raise XPublishError(f"Post is {len(text)} characters; X standard posts must be 280 characters or less.")
        if self.dry_run:
            logger.info("Playwright dry-run enabled; skipping X publish click")
            return XPublishResult(status="dry_run", message="Dry run passed. The post was not published.")

        playwright, context, should_close = await self._context_for_work()
        try:
            page = await context.new_page()
            await page.goto(self.compose_url, wait_until="domcontentloaded", timeout=60000)
            if await self._is_login_required(page):
                raise XLoginRequired("X login is required before publishing.")

            composer = page.locator('[data-testid="tweetTextarea_0"]').first
            await composer.wait_for(state="visible", timeout=30000)
            await composer.click()
            await page.keyboard.insert_text(text)

            post_button = page.locator('[data-testid="tweetButton"], [data-testid="tweetButtonInline"]').last
            await post_button.wait_for(state="visible", timeout=30000)
            await post_button.click()
            await page.wait_for_timeout(2500)

            current_url = page.url if "compose" not in page.url else None
            return XPublishResult(
                status="published",
                message="Post published to X.",
                platform_post_url=current_url,
            )
        finally:
            if should_close:
                await context.close()
                await playwright.stop()

    async def _context_for_work(self):
        if self._login_context_is_alive():
            return self.__class__._login_playwright, self.__class__._login_context, False
        playwright, context = await self._open_context()
        return playwright, context, True

    async def _ensure_login_context(self):
        if self._login_context_is_alive():
            return self.__class__._login_context
        playwright, context = await self._open_context()
        self.__class__._login_playwright = playwright
        self.__class__._login_context = context
        return context

    def _login_context_is_alive(self) -> bool:
        context = self.__class__._login_context
        if context is None:
            return False
        try:
            _ = context.pages
            return True
        except Exception:
            self.__class__._login_context = None
            self.__class__._login_playwright = None
            return False

    async def _open_context(self):
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise XPlaywrightUnavailable(
                "Playwright is not installed. Run `pip install -r requirements.txt` and `playwright install chromium`."
            ) from exc

        try:
            playwright = await async_playwright().start()
            self.user_data_dir.mkdir(parents=True, exist_ok=True)
            launch_options = {
                "user_data_dir": str(self.user_data_dir),
                "headless": self.headless,
                "slow_mo": self.slow_mo,
                "viewport": {"width": 1280, "height": 900},
                "args": ["--disable-blink-features=AutomationControlled"],
            }
            if self.browser_channel:
                launch_options["channel"] = self.browser_channel
            context = await playwright.chromium.launch_persistent_context(**launch_options)
            return playwright, context
        except Exception as exc:
            raise XPlaywrightUnavailable(
                "Could not start Chromium. Run `playwright install chromium` and try again."
            ) from exc

    async def _is_login_required(self, page) -> bool:
        url = page.url.lower()
        if "/login" in url or "/i/flow/login" in url:
            return True
        login_links = await page.locator('a[href*="/login"]').count()
        login_text = await page.get_by_text(re.compile(r"Log in|Sign in", re.IGNORECASE)).count()
        composer_count = await page.locator('[data-testid="tweetTextarea_0"]').count()
        home_count = await page.locator('[data-testid="AppTabBar_Home_Link"]').count()
        return (login_links > 0 or login_text > 0) and composer_count == 0 and home_count == 0

    def _strip_markdown(self, text: str) -> str:
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        text = re.sub(r"\*(.*?)\*", r"\1", text)
        text = re.sub(r"`(.*?)`", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
        text = re.sub(r"^\s*[-*]\s+", "- ", text, flags=re.MULTILINE)
        return text

    def _meaningful_lines(self, text: str) -> list[str]:
        labels = {
            "hook",
            "post",
            "proof angle",
            "cta",
            "hashtags",
            "image idea",
            "caption",
            "body",
        }
        cleaned = self._strip_markdown(text)
        raw_lines = re.split(r"[\n\r]+", cleaned)
        lines = []
        for raw_line in raw_lines:
            line = re.sub(r"^\s*[-•]\s*", "", raw_line).strip()
            line = re.sub(r"\s+", " ", line)
            label = line.rstrip(":").strip().lower()
            if not line or label in labels or line.startswith("#"):
                continue
            lines.append(line)
        return lines

    def _format_hashtags(self, hashtags: list[str]) -> str:
        formatted = []
        for tag in hashtags:
            clean = str(tag or "").strip()
            if not clean:
                continue
            if not clean.startswith("#"):
                clean = f"#{clean}"
            if clean not in formatted:
                formatted.append(clean)
            if len(formatted) == 3:
                break
        return " ".join(formatted)

    def _fit_with_suffix(self, text: str, suffix: str = "") -> str:
        suffix = suffix.strip()
        suffix_block = f"\n\n{suffix}" if suffix else ""
        budget = self.X_MAX_CHARS - len(suffix_block)
        if budget < 60:
            suffix_block = ""
            budget = self.X_MAX_CHARS

        clean = re.sub(r"\s+", " ", text).strip()
        if len(clean) <= budget:
            return f"{clean}{suffix_block}".strip()

        shortened = clean[: max(0, budget - 3)].rsplit(" ", 1)[0].rstrip(".,;: ")
        if not shortened:
            shortened = clean[: max(0, budget - 3)].rstrip()
        return f"{shortened}...{suffix_block}".strip()
