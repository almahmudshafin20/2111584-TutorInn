import json
from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
try:
    from backend.database import Base
except ModuleNotFoundError:
    from database import Base

def split_legacy_subjects(value: str | None) -> list[str]:
    return normalize_subjects([part.strip() for part in (value or "").replace(";", ",").split(",")])

def normalize_subjects(values: list[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        value = str(raw).strip()
        key = value.casefold()
        if value and key not in seen:
            result.append(value[:80])
            seen.add(key)
    return result[:20]

def read_subjects(raw: str | None, legacy: str | None = None) -> list[str]:
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return normalize_subjects(parsed)
        except (TypeError, ValueError):
            pass
    return split_legacy_subjects(legacy)

class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    education_level: Mapped[str] = mapped_column(String(80), nullable=False)
    preferred_subjects: Mapped[str] = mapped_column(String(255), default="", nul¶»§q«^