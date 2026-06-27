"""Browser automation for Google Admin Console bulk user upload."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import Page, Playwright, TimeoutError as PlaywrightTimeoutError, sync_playwright

load_dotenv()

USERS_URL = "https://admin.google.com/ac/users"
LOGIN_URL_PATTERN = re.compile(r"(accounts\.google\.com|signin)", re.IGNORECASE)
DEFAULT_ADMIN_EMAIL = os.getenv("GOOGLE_ADMIN_EMAIL", "admin@getinmarketing.site")


@dataclass
class BrowserUploadResult:
    success: bool
    message: str
    screenshot_path: Path | None = None


def _wait_for_admin_console(page: Page, login_timeout_ms: int) -> None:
    """Wait until the user finishes Google sign-in and lands in Admin Console."""
    deadline = time.time() + (login_timeout_ms / 1000)
    prompted = False

    while time.time() < deadline:
        current_url = page.url
        if "admin.google.com" in current_url and not LOGIN_URL_PATTERN.search(current_url):
            page.wait_for_load_state("domcontentloaded")
            return

        if LOGIN_URL_PATTERN.search(current_url) and not prompted:
            _prefill_admin_email(page)
            prompted = True

        page.wait_for_timeout(1000)

    raise TimeoutError(
        "Timed out waiting for Google Admin Console login. "
        "Complete sign-in in the browser window (including 2-Step Verification), then run again."
    )


def _prefill_admin_email(page: Page) -> None:
    email_input = page.locator('input[type="email"]')
    if email_input.count() == 0:
        return
    try:
        email_input.first.fill(DEFAULT_ADMIN_EMAIL)
        next_button = page.get_by_role("button", name="Next")
        if next_button.count() > 0:
            next_button.first.click()
    except Exception:  # noqa: BLE001
        pass


def _click_first_visible(page: Page, labels: list[str], timeout_ms: int = 8000) -> bool:
    for label in labels:
        for role in ("link", "button", "menuitem"):
            locator = page.get_by_role(role, name=label, exact=False)
            if locator.count() > 0:
                try:
                    locator.first.click(timeout=timeout_ms)
                    return True
                except Exception:  # noqa: BLE001
                    continue
        locator = page.get_by_text(label, exact=False)
        if locator.count() > 0:
            try:
                locator.first.click(timeout=timeout_ms)
                return True
            except Exception:  # noqa: BLE001
                continue
    return False


def _open_bulk_upload_dialog(page: Page) -> None:
    """Open the bulk user upload dialog from the Users page."""
    page.goto(USERS_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    opened = _click_first_visible(
        page,
        [
            "Bulk update users",
            "Bulk upload users",
            "Bulk invite users",
        ],
    )
    if not opened:
        more_options = page.get_by_text("More options", exact=False)
        if more_options.count() > 0:
            more_options.first.click()
            page.wait_for_timeout(1000)
            opened = _click_first_visible(
                page,
                [
                    "Bulk update users",
                    "Bulk upload users",
                    "Bulk invite users",
                ],
            )

    if not opened:
        raise RuntimeError(
            "Could not find 'Bulk update users' on the Users page. "
            "Check that your admin account has permission and enough user licenses."
        )

    page.wait_for_timeout(1500)


def _attach_csv_and_upload(page: Page, csv_path: Path) -> None:
    file_input = page.locator('input[type="file"]')
    if file_input.count() == 0:
        if not _click_first_visible(
            page,
            [
                "Attach CSV file",
                "Select CSV file",
                "Choose file",
                "Browse",
            ],
        ):
            raise RuntimeError("Could not find the CSV file attachment control.")
        file_input = page.locator('input[type="file"]')

    file_input.first.set_input_files(str(csv_path.resolve()))
    page.wait_for_timeout(2000)

    uploaded = _click_first_visible(page, ["Upload", "Import", "Continue", "Confirm"])
    if not uploaded:
        raise RuntimeError("CSV attached but could not find the Upload/Confirm button.")


def _wait_for_upload_result(page: Page, result_timeout_ms: int) -> str:
    success_markers = [
        "upload complete",
        "successfully",
        "users added",
        "users updated",
        "users created",
        "processing",
        "review",
    ]
    error_markers = [
        "insufficient licenses",
        "action failed",
        "invalid",
        "could not",
    ]

    deadline = time.time() + (result_timeout_ms / 1000)
    while time.time() < deadline:
        body_text = page.locator("body").inner_text(timeout=3000).lower()
        if any(marker in body_text for marker in success_markers):
            return "Upload submitted. Review the Admin Console confirmation for details."
        if any(marker in body_text for marker in error_markers):
            return "Upload finished with warnings or errors. Review the Admin Console message."
        page.wait_for_timeout(2000)

    return "Upload action completed. Verify the result in the browser window."


def bulk_upload_via_browser(
    csv_path: Path,
    *,
    headless: bool = False,
    login_timeout_ms: int = 600_000,
    result_timeout_ms: int = 180_000,
    screenshot_dir: Path | None = None,
    profile_dir: Path | None = None,
) -> BrowserUploadResult:
    """Upload a bulk user CSV through the Google Admin Console UI."""
    csv_path = csv_path.resolve()
    if not csv_path.is_file():
        return BrowserUploadResult(False, f"CSV file not found: {csv_path}")

    screenshot_dir = screenshot_dir or csv_path.parent
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_dir / "bulk_upload_result.png"

    profile_dir = profile_dir or csv_path.parents[1] / ".browser_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    playwright: Playwright | None = None
    context = None
    page: Page | None = None
    try:
        playwright = sync_playwright().start()
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            args=["--start-maximized"],
            no_viewport=True,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(60_000)

        page.goto(USERS_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        if LOGIN_URL_PATTERN.search(page.url):
            _prefill_admin_email(page)
        _wait_for_admin_console(page, login_timeout_ms)
        _open_bulk_upload_dialog(page)
        _attach_csv_and_upload(page, csv_path)
        message = _wait_for_upload_result(page, result_timeout_ms)
        page.screenshot(path=str(screenshot_path), full_page=True)

        return BrowserUploadResult(
            success=True,
            message=message,
            screenshot_path=screenshot_path,
        )
    except PlaywrightTimeoutError as exc:
        if page is not None:
            page.screenshot(path=str(screenshot_path), full_page=True)
        return BrowserUploadResult(
            success=False,
            message=f"Browser automation timed out: {exc}",
            screenshot_path=screenshot_path if screenshot_path.exists() else None,
        )
    except Exception as exc:  # noqa: BLE001
        if page is not None:
            try:
                page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception:  # noqa: BLE001
                pass
        return BrowserUploadResult(
            success=False,
            message=str(exc),
            screenshot_path=screenshot_path if screenshot_path.exists() else None,
        )
    finally:
        if context is not None:
            context.close()
        if playwright is not None:
            playwright.stop()
