"""Google Admin SDK Directory API user provisioning."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.generate_users import UserRecord, save_csv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/admin.directory.user"]
REPORT_COLUMNS = [
    "first_name",
    "last_name",
    "full_name",
    "username",
    "primary_email",
    "temporary_password",
    "org_unit_path",
    "change_password_at_next_login",
    "status",
    "google_user_id",
    "error_message",
]


@dataclass
class ProvisionResult:
    user: UserRecord
    success: bool
    google_user_id: str | None = None
    error_message: str | None = None


class GoogleAdminProvisioner:
    """Create Workspace users via Directory API with safe retries."""

    def __init__(
        self,
        *,
        service_account_file: str | None = None,
        admin_email: str | None = None,
        max_retries: int = 5,
        base_delay_seconds: float = 2.0,
    ) -> None:
        self.service_account_file = service_account_file or os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
        self.admin_email = admin_email or os.getenv("GOOGLE_ADMIN_EMAIL", "")
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self._service: Any | None = None

    def validate_config(self) -> list[str]:
        errors: list[str] = []
        if not self.service_account_file:
            errors.append("GOOGLE_SERVICE_ACCOUNT_FILE is not set.")
        elif not Path(self.service_account_file).is_file():
            errors.append(f"Service account file not found: {self.service_account_file}")
        if not self.admin_email:
            errors.append("GOOGLE_ADMIN_EMAIL is not set.")
        return errors

    @property
    def service(self) -> Any:
        if self._service is None:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=SCOPES,
            ).with_subject(self.admin_email)
            self._service = build("admin", "directory_v1", credentials=credentials, cache_discovery=False)
        return self._service

    def _build_user_body(self, user: UserRecord) -> dict[str, Any]:
        return {
            "name": {
                "givenName": user.first_name,
                "familyName": user.last_name,
            },
            "password": user.temporary_password,
            "primaryEmail": user.primary_email,
            "orgUnitPath": user.org_unit_path,
            "changePasswordAtNextLogin": user.change_password_at_next_login,
        }

    def _is_retryable(self, error: HttpError) -> bool:
        status = getattr(error.resp, "status", None)
        return status in {403, 429, 500, 503}

    def create_user(self, user: UserRecord) -> ProvisionResult:
        body = self._build_user_body(user)
        last_error: str | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.service.users().insert(body=body).execute()
                return ProvisionResult(
                    user=user,
                    success=True,
                    google_user_id=response.get("id"),
                )
            except HttpError as exc:
                last_error = self._format_http_error(exc)
                if self._is_retryable(exc) and attempt < self.max_retries:
                    delay = self.base_delay_seconds * (2**attempt)
                    time.sleep(delay)
                    continue
                break
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                break

        return ProvisionResult(user=user, success=False, error_message=last_error)

    @staticmethod
    def _format_http_error(error: HttpError) -> str:
        try:
            payload = error.error_details if hasattr(error, "error_details") else error.content
            return str(payload)
        except Exception:  # noqa: BLE001
            return str(error)

    def provision_users(self, users: list[UserRecord]) -> list[ProvisionResult]:
        config_errors = self.validate_config()
        if config_errors:
            raise ValueError("; ".join(config_errors))

        results: list[ProvisionResult] = []
        for index, user in enumerate(users, start=1):
            result = self.create_user(user)
            results.append(result)
            if index < len(users):
                time.sleep(0.2)
        return results

    def export_report(self, results: list[ProvisionResult], path: Path) -> Path:
        rows: list[dict[str, Any]] = []
        for result in results:
            user = result.user
            rows.append(
                {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "full_name": user.full_name,
                    "username": user.username,
                    "primary_email": user.primary_email,
                    "temporary_password": user.temporary_password,
                    "org_unit_path": user.org_unit_path,
                    "change_password_at_next_login": user.change_password_at_next_login,
                    "status": "created" if result.success else "failed",
                    "google_user_id": result.google_user_id or "",
                    "error_message": result.error_message or "",
                }
            )
        return save_csv(pd.DataFrame(rows, columns=REPORT_COLUMNS), path)
