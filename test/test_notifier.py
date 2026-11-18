"""네트워크 없이 실행되는 단위 테스트: python -m unittest test.test_notifier"""
import os
import unittest
from unittest import mock

from korail2 import MacroBlockedError, NoResultsError
from korail2.korail2 import Korail, Train
from notifier.config import Config, ConfigError, SeatMode
from notifier.watcher import Watcher, build_message, in_time_window, is_available


def make_train(no="101", dep_time="090000", gen="13", spe="13", psb_nm="매진", **extra):
    data = {
        "h_trn_clsf_cd": "00", "h_trn_clsf_nm": "KTX", "h_trn_gp_cd": "100", "h_trn_no": no,
        "h_dpt_rs_stn_nm": "서울", "h_dpt_rs_stn_cd": "0001", "h_dpt_dt": "20261225", "h_dpt_tm": dep_time,
        "h_arv_rs_stn_nm": "부산", "h_arv_rs_stn_cd": "0020", "h_arv_dt": "20261225", "h_arv_tm": "113000",
        "h_run_dt": "20261225", "h_rsv_psb_flg": "N", "h_rsv_psb_nm": psb_nm,
        "h_gen_rsv_cd": gen, "h_spe_rsv_cd": spe, "h_wait_rsv_flg": "0",
    }
    data.update(extra)
    return Train(data)


ENV = {
    "WATCH_DEP": "서울", "WATCH_ARR": "부산", "WATCH_DATE": "2026-12-25",
    "WATCH_TIME_FROM": "08:00", "WATCH_TIME_TO": "1200",
    "TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "1",
}


def make_config(**env):
    with mock.patch.dict(os.environ, {**ENV, **env}, clear=True):
        return Config.from_env()


class TrainTest(unittest.TestCase):
    def test_general_seat(self):
        self.assertTrue(make_train(gen="11").has_general_seat())
        self.assertFalse(make_train(gen="13").has_general_seat())

    def test_standing_by_code(self):
        self.assertTrue(make_train(h_stnd_rsv_cd="11").has_standing_seat())
        self.assertFalse(make_train(h_stnd_rsv_cd="13", psb_nm="입석+좌석").has_standing_seat())

    def test_standing_by_name_fallback(self):
        self.assertTrue(make_train(psb_nm="입석+좌석\n예약가능").has_standing_seat())
        self.assertFalse(make_train(psb_nm="입석 역발매중").has_standing_seat())
        self.assertFalse(make_train(psb_nm="입석 매진").has_standing_seat())

    def test_macro_error_raised(self):
        k = Korail(auto_login=False)
        with self.assertRaises(MacroBlockedError):
            k._result_check({"strResult": "FAIL", "h_msg_cd": "MACRO ERROR", "h_msg_txt": "..."})

    def test_separate_sessions(self):
        self.assertIsNot(Korail(auto_login=False)._session, Korail(auto_login=False)._session)


class ConfigTest(unittest.TestCase):
    def test_parse(self):
        c = make_config(SEAT_MODE="seat_or_standing")
        self.assertEqual(c.date, "20261225")
        self.assertEqual(c.time_from, "0800")
        self.assertIs(c.seat_mode, SeatMode.SEAT_OR_STANDING)

    def test_min_interval(self):
        with self.assertRaises(ConfigError):
            make_config(CHECK_INTERVAL_MINUTES="1")

    def test_missing_required(self):
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaises(ConfigError):
            Config.from_env()


class WatcherTest(unittest.TestCase):
    def test_is_available_modes(self):
        standing = make_train(psb_nm="입석+좌석")
        self.assertFalse(is_available(standing, SeatMode.SEAT))
        self.assertTrue(is_available(standing, SeatMode.SEAT_OR_STANDING))
        # 특실만 있는 경우는 일반석 기준이므로 알림 대상 아님
        self.assertFalse(is_available(make_train(spe="11"), SeatMode.SEAT_OR_STANDING))

    def test_time_window(self):
        self.assertTrue(in_time_window(make_train(dep_time="080000"), "0800", "1200"))
        self.assertFalse(in_time_window(make_train(dep_time="120100"), "0800", "1200"))

    def test_diff_notifies_only_new_and_reappeared(self):
        w = Watcher(make_config(), korail=None)
        a, b = make_train("101", gen="11"), make_train("103", gen="11")
        self.assertEqual([t.train_no for t in w.diff([a])], ["101"])
        self.assertEqual(w.diff([a]), [])  # 그대로면 재알림 안 함
        self.assertEqual([t.train_no for t in w.diff([a, b])], ["103"])
        self.assertEqual(w.diff([]), [])  # 사라짐
        self.assertEqual([t.train_no for t in w.diff([a])], ["101"])  # 다시 생기면 알림

    def test_fetch_filters_window_and_handles_no_results(self):
        k = mock.Mock()
        k.search_train_allday.return_value = [make_train("1", "070000", gen="11"), make_train("2", "090000", gen="11")]
        w = Watcher(make_config(), k)
        self.assertEqual([t.train_no for t in w.fetch()], ["2"])
        k.search_train_allday.side_effect = NoResultsError()
        self.assertEqual(w.fetch(), [])

    def test_message(self):
        msg = build_message(make_config(), [make_train("101", gen="11")])
        self.assertIn("2026-12-25", msg)
        self.assertIn("KTX 101", msg)
        self.assertIn("일반실", msg)


if __name__ == "__main__":
    unittest.main()
