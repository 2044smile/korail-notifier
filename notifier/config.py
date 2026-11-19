"""환경변수(.env) 기반 설정."""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum

from korail2 import TrainType

def _load_env_file(path: str = ".env") -> None:
    """python-dotenv 가 없을 때의 최소 .env 로더 (이미 설정된 환경변수는 덮어쓰지 않음)."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.split(" #", 1)[0].strip().strip("'\"")
        os.environ.setdefault(key.strip(), value)


try:  # python-dotenv 가 있으면 .env 자동 로드
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    _load_env_file()

# 서버에 부담을 주지 않도록 최소 조회 간격을 강제한다.
MIN_INTERVAL_MINUTES = 3


class SeatMode(str, Enum):
    """일반실 기준 알림 조건."""
    SEAT = "seat"  # 일반실 좌석만
    SEAT_OR_STANDING = "seat_or_standing"  # 일반실 좌석 또는 입석+좌석


TRAIN_TYPES = {
    "all": TrainType.ALL,
    "ktx": TrainType.KTX,
    "saemaeul": TrainType.SAEMAEUL,
    "itx-saemaeul": TrainType.ITX_SAEMAEUL,
    "mugunghwa": TrainType.MUGUNGHWA,
    "itx-cheongchun": TrainType.ITX_CHEONGCHUN,
}


class ConfigError(ValueError):
    pass


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"환경변수 {name} 가 필요합니다 (.env.example 참고)")
    return value


def _hhmm(value: str, name: str) -> str:
    v = value.replace(":", "")
    if len(v) != 4 or not v.isdigit() or int(v[:2]) > 23 or int(v[2:]) > 59:
        raise ConfigError(f"{name} 는 HHMM 형식이어야 합니다: {value!r}")
    return v


@dataclass(frozen=True)
class Config:
    dep: str
    arr: str
    date: str  # yyyyMMdd
    time_from: str  # HHMM
    time_to: str  # HHMM
    train_type: str
    seat_mode: SeatMode
    adults: int
    interval_minutes: float
    telegram_token: str
    telegram_chat_id: str
    notify_on_start: bool = True

    @classmethod
    def from_env(cls) -> Config:
        date = _require("WATCH_DATE").replace("-", "")
        if len(date) != 8 or not date.isdigit():
            raise ConfigError(f"WATCH_DATE 는 YYYYMMDD 형식이어야 합니다: {date!r}")

        train_type_key = os.environ.get("WATCH_TRAIN_TYPE", "ktx").strip().lower()
        if train_type_key not in TRAIN_TYPES:
            raise ConfigError(f"WATCH_TRAIN_TYPE 은 {list(TRAIN_TYPES)} 중 하나여야 합니다")

        try:
            seat_mode = SeatMode(os.environ.get("SEAT_MODE", SeatMode.SEAT.value).strip().lower())
        except ValueError:
            raise ConfigError(f"SEAT_MODE 는 {[m.value for m in SeatMode]} 중 하나여야 합니다") from None

        interval = float(os.environ.get("CHECK_INTERVAL_MINUTES", "5"))
        if interval < MIN_INTERVAL_MINUTES:
            raise ConfigError(f"CHECK_INTERVAL_MINUTES 는 최소 {MIN_INTERVAL_MINUTES}분 이상이어야 합니다")

        return cls(
            dep=_require("WATCH_DEP"),
            arr=_require("WATCH_ARR"),
            date=date,
            time_from=_hhmm(os.environ.get("WATCH_TIME_FROM", "0000"), "WATCH_TIME_FROM"),
            time_to=_hhmm(os.environ.get("WATCH_TIME_TO", "2359"), "WATCH_TIME_TO"),
            train_type=TRAIN_TYPES[train_type_key],
            seat_mode=seat_mode,
            adults=int(os.environ.get("WATCH_ADULTS", "1")),
            interval_minutes=interval,
            telegram_token=_require("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=_require("TELEGRAM_CHAT_ID"),
            notify_on_start=os.environ.get("NOTIFY_ON_START", "true").lower() in ("1", "true", "yes"),
        )
