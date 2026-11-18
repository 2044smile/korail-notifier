"""빈 좌석 감시 로직 (네트워크와 분리해서 테스트 가능하도록 구성)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from korail2 import AdultPassenger, Korail, NoResultsError, Train

from .config import Config, SeatMode

log = logging.getLogger(__name__)


def is_available(train: Train, mode: SeatMode) -> bool:
    """일반실 기준 알림 대상 여부 (특실은 보지 않음)."""
    if train.has_general_seat():
        return True
    if mode is SeatMode.SEAT_OR_STANDING:
        return train.has_standing_seat()
    return False


def in_time_window(train: Train, time_from: str, time_to: str) -> bool:
    hhmm = (train.dep_time or "")[:4]
    return time_from <= hhmm <= time_to


def seat_label(train: Train) -> str:
    return "일반실" if train.has_general_seat() else "입석+좌석"


def train_key(train: Train) -> str:
    return f"{train.dep_date}-{train.train_no}"


def format_train(train: Train) -> str:
    dep = f"{train.dep_time[:2]}:{train.dep_time[2:4]}"
    arr = f"{train.arr_time[:2]}:{train.arr_time[2:4]}"
    return f"[{train.train_type_name} {int(train.train_no)}] {train.dep_name} {dep} → {train.arr_name} {arr} · {seat_label(train)}"


@dataclass
class Watcher:
    config: Config
    korail: Korail
    _seen: set[str] = field(default_factory=set)

    def fetch(self) -> list[Train]:
        c = self.config
        try:
            trains = self.korail.search_train_allday(
                c.dep, c.arr, c.date, c.time_from + "00", c.train_type,
                passengers=[AdultPassenger(c.adults)], include_no_seats=True,
            )
        except NoResultsError:
            return []
        return [t for t in trains if in_time_window(t, c.time_from, c.time_to)]

    def diff(self, trains: list[Train]) -> list[Train]:
        """이번 조회에서 '새로' 자리가 생긴 열차만 반환하고 상태를 갱신한다.

        자리가 사라졌다가 다시 생기면 다시 알린다.
        """
        available = [t for t in trains if is_available(t, self.config.seat_mode)]
        current = {train_key(t) for t in available}
        new = [t for t in available if train_key(t) not in self._seen]
        self._seen = current
        return new

    def check(self) -> list[Train]:
        return self.diff(self.fetch())


def build_message(config: Config, trains: list[Train]) -> str:
    d = config.date
    lines = [f"🚄 빈자리 발견! {config.dep}→{config.arr} {d[:4]}-{d[4:6]}-{d[6:]}"]
    lines += [f"• {format_train(t)}" for t in trains]
    lines.append("코레일톡 앱에서 직접 예매하세요.")
    return "\n".join(lines)
