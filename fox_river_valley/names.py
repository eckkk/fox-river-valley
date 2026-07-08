from __future__ import annotations

MAX_NAME_LENGTH = 40


class NameValidationError(ValueError):
    pass


def clean_name(raw: str | None, *, field: str = "名字") -> str:
    text = "" if raw is None else str(raw)
    if "\n" in text or "\r" in text:
        raise NameValidationError(f"{field}不能包含换行。")
    cleaned = "".join(ch for ch in text.strip() if ch >= " " and ch != "\x7f")
    if not cleaned:
        raise NameValidationError(f"{field}不能为空。")
    if len(cleaned) > MAX_NAME_LENGTH:
        raise NameValidationError(f"{field}太长，最多 {MAX_NAME_LENGTH} 个字符。")
    return cleaned
