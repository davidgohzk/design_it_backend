import os
from dataclasses import dataclass

DEFAULT_SOCLAAS_BASE_URL = "https://soclaas-api.comp.nus.edu.sg/v1"


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else default


@dataclass(frozen=True)
class Settings:
    soclaas_model: str
    # /api/assess can use a different (e.g. stronger) model; empty means soclaas_model.
    soclaas_assess_model: str = ""
    soclaas_api_key: str | None = None
    soclaas_base_url: str = DEFAULT_SOCLAAS_BASE_URL
    allowed_origins: tuple[str, ...] = ()
    rate_limit_per_minute: int = 20
    rate_limit_per_day: int = 300
    max_concurrent_upstream: int = 6
    enable_docs: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        model = os.environ.get("SOCLAAS_MODEL", "").strip()
        if not model:
            raise RuntimeError("SOCLAAS_MODEL must be set.")
        origins = tuple(
            origin.strip().rstrip("/")
            for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        )
        return cls(
            soclaas_model=model,
            soclaas_assess_model=os.environ.get("SOCLAAS_ASSESS_MODEL", "").strip(),
            soclaas_api_key=os.environ.get("SOCLAAS_API_KEY", "").strip() or None,
            soclaas_base_url=os.environ.get("SOCLAAS_BASE_URL", "").strip().rstrip("/") or DEFAULT_SOCLAAS_BASE_URL,
            allowed_origins=origins,
            rate_limit_per_minute=_int_env("RATE_LIMIT_PER_MINUTE", 20),
            rate_limit_per_day=_int_env("RATE_LIMIT_PER_DAY", 300),
            max_concurrent_upstream=_int_env("MAX_CONCURRENT_UPSTREAM", 6),
            enable_docs=os.environ.get("ENABLE_DOCS", "").strip() == "1",
        )
