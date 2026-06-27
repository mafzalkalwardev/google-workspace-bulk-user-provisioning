"""Generate Google Workspace user records with British-style names."""

from __future__ import annotations

import re
import secrets
import string
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd
from faker import Faker

PasswordMode = Literal["fixed", "random"]
UsernameFormat = Literal["firstname.lastname", "firstinitiallastname", "firstname123"]

BULK_UPLOAD_COLUMNS = [
    "First Name",
    "Last Name",
    "Email Address",
    "Password",
    "Org Unit Path",
    "Change Password at Next Sign-In",
]

EXPORT_COLUMNS = [
    "first_name",
    "last_name",
    "full_name",
    "username",
    "primary_email",
    "temporary_password",
    "org_unit_path",
    "change_password_at_next_login",
    "status",
]

FIXED_TEMP_PASSWORD = "Kalwar@123"
EMAIL_PATTERN = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")


@dataclass(frozen=True)
class UserRecord:
    first_name: str
    last_name: str
    full_name: str
    username: str
    primary_email: str
    temporary_password: str
    org_unit_path: str
    change_password_at_next_login: bool
    status: str = "pending"

    def to_bulk_upload_row(self) -> dict[str, str]:
        return {
            "First Name": self.first_name,
            "Last Name": self.last_name,
            "Email Address": self.primary_email,
            "Password": self.temporary_password,
            "Org Unit Path": self.org_unit_path,
            "Change Password at Next Sign-In": "True" if self.change_password_at_next_login else "False",
        }

    def to_export_row(self) -> dict[str, str | bool]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "username": self.username,
            "primary_email": self.primary_email,
            "temporary_password": self.temporary_password,
            "org_unit_path": self.org_unit_path,
            "change_password_at_next_login": self.change_password_at_next_login,
            "status": self.status,
        }


def normalize_name(value: str) -> str:
    """Strip accents and non-alphanumeric characters for username building."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]", "", ascii_text).lower()


def generate_secure_password(length: int = 16) -> str:
    """Generate a strong password meeting Google Workspace requirements."""
    if length < 12:
        length = 12

    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*-_=+"

    required = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(symbols),
    ]
    pool = lowercase + uppercase + digits + symbols
    remaining = [secrets.choice(pool) for _ in range(length - len(required))]
    password_chars = required + remaining
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def build_username(
    first_name: str,
    last_name: str,
    username_format: UsernameFormat,
    used_usernames: set[str],
) -> str:
    """Build a unique username for the given format."""
    first = normalize_name(first_name)
    last = normalize_name(last_name)
    if not first or not last:
        raise ValueError("First and last name must contain usable characters.")

    if username_format == "firstname.lastname":
        base = f"{first}.{last}"
    elif username_format == "firstinitiallastname":
        base = f"{first[0]}{last}"
    else:
        base = first

    candidate = base
    suffix = 1
    while candidate in used_usernames:
        if username_format == "firstname123":
            candidate = f"{first}{suffix}"
        else:
            candidate = f"{base}{suffix}"
        suffix += 1

    used_usernames.add(candidate)
    return candidate


def validate_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(email))


def generate_users(
    *,
    domain: str,
    count: int,
    password_mode: PasswordMode,
    username_format: UsernameFormat,
    org_unit_path: str,
    change_password_at_next_login: bool,
    fixed_password: str = FIXED_TEMP_PASSWORD,
    seed: int | None = None,
) -> list[UserRecord]:
    """Generate unique user records with British-style names."""
    if count < 1:
        raise ValueError("number_of_users must be at least 1.")
    if count > 5000:
        raise ValueError("number_of_users cannot exceed 5000 in one batch.")

    domain = domain.strip().lower()
    if not domain or "." not in domain:
        raise ValueError("Invalid domain.")

    org_unit_path = org_unit_path.strip() or "/"
    if not org_unit_path.startswith("/"):
        org_unit_path = f"/{org_unit_path}"

    faker = Faker("en_GB")
    if seed is not None:
        Faker.seed(seed)

    used_usernames: set[str] = set()
    users: list[UserRecord] = []

    attempts = 0
    max_attempts = count * 25

    while len(users) < count and attempts < max_attempts:
        attempts += 1
        first_name = faker.first_name()
        last_name = faker.last_name()

        try:
            username = build_username(first_name, last_name, username_format, used_usernames)
        except ValueError:
            continue

        primary_email = f"{username}@{domain}"
        if not validate_email(primary_email):
            used_usernames.discard(username)
            continue

        password = fixed_password if password_mode == "fixed" else generate_secure_password()
        full_name = f"{first_name} {last_name}"

        users.append(
            UserRecord(
                first_name=first_name,
                last_name=last_name,
                full_name=full_name,
                username=username,
                primary_email=primary_email,
                temporary_password=password,
                org_unit_path=org_unit_path,
                change_password_at_next_login=change_password_at_next_login,
            )
        )

    if len(users) < count:
        raise RuntimeError(
            f"Could only generate {len(users)} unique users after {max_attempts} attempts."
        )

    return users


def users_to_bulk_upload_df(users: list[UserRecord]) -> pd.DataFrame:
    return pd.DataFrame([user.to_bulk_upload_row() for user in users], columns=BULK_UPLOAD_COLUMNS)


def users_to_export_df(users: list[UserRecord]) -> pd.DataFrame:
    return pd.DataFrame([user.to_export_row() for user in users], columns=EXPORT_COLUMNS)


def save_csv(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def save_user_exports(
    users: list[UserRecord],
    exports_dir: Path,
    *,
    bulk_filename: str = "workspace_users_bulk_upload.csv",
    export_filename: str = "workspace_users.csv",
) -> tuple[Path, Path]:
    bulk_path = save_csv(users_to_bulk_upload_df(users), exports_dir / bulk_filename)
    export_path = save_csv(users_to_export_df(users), exports_dir / export_filename)
    return bulk_path, export_path


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def load_users_from_bulk_csv(path: Path) -> list[UserRecord]:
    """Load user records from a Google Admin bulk-upload CSV."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    missing = [col for col in BULK_UPLOAD_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {', '.join(missing)}")

    users: list[UserRecord] = []
    for _, row in df.iterrows():
        email = str(row["Email Address"]).strip().lower()
        if "@" not in email:
            raise ValueError(f"Invalid email address: {email}")
        username = email.split("@", 1)[0]
        first_name = str(row["First Name"]).strip()
        last_name = str(row["Last Name"]).strip()
        users.append(
            UserRecord(
                first_name=first_name,
                last_name=last_name,
                full_name=f"{first_name} {last_name}".strip(),
                username=username,
                primary_email=email,
                temporary_password=str(row["Password"]),
                org_unit_path=str(row["Org Unit Path"]).strip() or "/",
                change_password_at_next_login=_parse_bool(row["Change Password at Next Sign-In"]),
            )
        )
    return users
