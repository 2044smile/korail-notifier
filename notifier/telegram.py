"""Telegram Bot API 로 메시지 전송."""
from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, timeout: float = 10):
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._chat_id = chat_id
        self._timeout = timeout

    def send(self, text: str) -> bool:
        try:
            r = requests.post(
                self._url,
                json={"chat_id": self._chat_id, "text": text, "disable_web_page_preview": True},
                timeout=self._timeout,
            )
        except requests.RequestException as e:
            log.error("텔레그램 전송 실패: %s", e)
            return False
        if not r.ok:
            # 토큰이 로그에 남지 않도록 응답 본문만 기록
            log.error("텔레그램 전송 실패: HTTP %s %s", r.status_code, r.text[:200])
            return False
        return True
