"""실행: python -m notifier [--once] [--test-telegram]"""
from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time

import requests

from korail2 import Korail, KorailError, MacroBlockedError

from .config import Config, ConfigError
from .telegram import TelegramNotifier
from .watcher import Watcher, build_message

log = logging.getLogger("notifier")

# 연속 실패 시 알림 / 백오프 상한
FAILURE_ALERT_THRESHOLD = 3
MAX_BACKOFF_MINUTES = 60

_stop = False


def _handle_stop(signum, _frame):
    global _stop
    log.info("종료 신호(%s) 수신", signum)
    _stop = True


def _sleep(seconds: float) -> None:
    end = time.monotonic() + seconds
    while not _stop and time.monotonic() < end:
        time.sleep(min(1.0, end - time.monotonic()))


def run(config: Config, once: bool = False) -> int:
    tg = TelegramNotifier(config.telegram_token, config.telegram_chat_id)
    watcher = Watcher(config, Korail(auto_login=False))

    if config.notify_on_start and not once:
        tg.send(f"👀 감시 시작: {config.dep}→{config.arr} {config.date} "
                f"{config.time_from}~{config.time_to} ({config.seat_mode.value}, {config.interval_minutes:g}분 간격)")

    failures = 0
    while not _stop:
        try:
            new = watcher.check()
            failures = 0
            if new:
                log.info("새 빈자리 %d건", len(new))
                tg.send(build_message(config, new))
            else:
                log.info("새 빈자리 없음")
        except MacroBlockedError as e:
            # 차단 신호를 받으면 재시도/우회하지 않고 즉시 종료한다.
            log.error("코레일이 요청을 차단했습니다: %s", e)
            tg.send("⛔ 코레일 서버가 자동화 요청을 차단(MACRO ERROR)했습니다. 감시를 중단합니다.")
            return 2
        except (KorailError, requests.RequestException, ValueError) as e:
            failures += 1
            log.warning("조회 실패 (%d회 연속): %s", failures, e)
            if failures == FAILURE_ALERT_THRESHOLD:
                tg.send(f"⚠️ 조회가 {failures}회 연속 실패했습니다: {e}")

        if once:
            break

        backoff = min(config.interval_minutes * (2 ** min(failures, 5)), MAX_BACKOFF_MINUTES) \
            if failures else config.interval_minutes
        _sleep(backoff * 60)

    return 0


def _set_env_value(key: str, value: str, path: str = ".env") -> None:
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        lines = []
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def get_chat_id() -> int:
    from .telegram import find_chat_ids

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print(".env 의 TELEGRAM_BOT_TOKEN 을 먼저 채워주세요 (BotFather 가 준 토큰)", file=sys.stderr)
        return 1
    try:
        chats = find_chat_ids(token)
    except (ValueError, requests.RequestException) as e:
        print(f"조회 실패: {e}", file=sys.stderr)
        return 1
    if not chats:
        print("메시지를 찾지 못했습니다. 텔레그램에서 내 봇을 열고 /start 를 보낸 뒤 다시 실행하세요.")
        return 1
    for chat_id, name in chats:
        print(f"chat_id={chat_id}  ({name})")
    if len(chats) == 1:
        _set_env_value("TELEGRAM_CHAT_ID", chats[0][0])
        print(".env 의 TELEGRAM_CHAT_ID 에 저장했습니다.")
    else:
        print("여러 개가 나왔습니다. 본인 것을 .env 의 TELEGRAM_CHAT_ID 에 넣어주세요.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notifier", description="코레일 빈자리 텔레그램 알림")
    parser.add_argument("--once", action="store_true", help="한 번만 조회하고 종료 (cron 용)")
    parser.add_argument("--test-telegram", action="store_true", help="텔레그램 테스트 메시지만 전송")
    parser.add_argument("--get-chat-id", action="store_true",
                        help="봇에게 메시지를 보낸 뒤 실행하면 TELEGRAM_CHAT_ID 를 찾아 .env 에 저장")
    parser.add_argument("-v", "--verbose", action="store_true")
    trip = parser.add_argument_group("여정 (.env 값보다 우선)")
    trip.add_argument("--from", dest="dep", help="출발역 (예: '울산(통도사)')")
    trip.add_argument("--to", dest="arr", help="도착역 (예: 서울)")
    trip.add_argument("--date", help="YYYY-MM-DD")
    trip.add_argument("--after", help="이 시각 이후 출발 (HH:MM)")
    trip.add_argument("--before", help="이 시각 이전 출발 (HH:MM)")
    trip.add_argument("--mode", choices=["seat", "seat_or_standing"], help="알림 조건")
    args = parser.parse_args(argv)

    overrides = {
        "WATCH_DEP": args.dep, "WATCH_ARR": args.arr, "WATCH_DATE": args.date,
        "WATCH_TIME_FROM": args.after, "WATCH_TIME_TO": args.before, "SEAT_MODE": args.mode,
    }
    os.environ.update({k: v for k, v in overrides.items() if v})

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # urllib3 디버그 로그에 텔레그램 토큰(URL)이 찍히지 않도록
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    if args.get_chat_id:
        return get_chat_id()

    try:
        config = Config.from_env()
    except ConfigError as e:
        print(f"설정 오류: {e}", file=sys.stderr)
        return 1

    if args.test_telegram:
        ok = TelegramNotifier(config.telegram_token, config.telegram_chat_id).send("✅ korail-notifier 텔레그램 연결 테스트")
        return 0 if ok else 1

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)
    return run(config, once=args.once)


if __name__ == "__main__":
    sys.exit(main())
