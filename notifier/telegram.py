"""Telegram Bot API 로 메시지 전송."""
from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)


def find_chat_ids(token: str, timeout: float = 10) -> list[tuple[str, str]]:
    """봇에게 메시지를 보낸 사용자들의 (chat_id, 이름) 목록을 getUpdates 로 조회."""
    r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=timeout)
    if r.status_code == 401:
        raise ValueError("봇 토큰이 올바르지 않습니다")
    if r.status_code == 409:
        raise ValueError("이 봇에 webhook 이 설정돼 있거나 다른 프로그램이 메시지를 받고 있습니다. "
                         "예전 프로그램을 끄고, 필요하면 브라우저에서 "
                         "https://api.telegram.org/bot<토큰>/deleteWebhook 을 연 뒤 다시 시도하세요")
    r.raise_for_status()
    found: dict[str, str] = {}
    for upd in r.json().get("result", []):
        chat = (upd.get("message") or upd.get("my_chat_member") or {}).get("chat")
        if chat:
            name = chat.get("username") or chat.get("first_name") or chat.get("title") or ""
            found[str(chat["id"])] = name
    return list(found.items())


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
