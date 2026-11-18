"""
    korail2.korail2
    ~~~~~~~~~~~~~~~

    Python 3.10+ port of carpedm20/korail2.

    :copyright: (c) 2014 by Taehoon Kim.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import annotations

import base64
import itertools
import json
import re
from datetime import datetime, timedelta, timezone
from functools import reduce
from typing import Any, Iterable

import requests

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
PHONE_NUMBER_REGEX = re.compile(r"(\d{3})-(\d{3,4})-(\d{4})")

KST = timezone(timedelta(hours=9))

SCHEME = "https"
KORAIL_HOST = "smart.letskorail.com"
KORAIL_PORT = "443"

KORAIL_DOMAIN = f"{SCHEME}://{KORAIL_HOST}:{KORAIL_PORT}"
KORAIL_MOBILE = f"{KORAIL_DOMAIN}/classes/com.korail.mobile"

KORAIL_LOGIN = f"{KORAIL_MOBILE}.login.Login"
KORAIL_LOGOUT = f"{KORAIL_MOBILE}.common.logout"
KORAIL_SEARCH_SCHEDULE = f"{KORAIL_MOBILE}.seatMovie.ScheduleView"
KORAIL_TICKETRESERVATION = f"{KORAIL_MOBILE}.certification.TicketReservation"
KORAIL_REFUND = f"{KORAIL_MOBILE}.refunds.RefundsRequest"
KORAIL_MYTICKETLIST = f"{KORAIL_MOBILE}.myTicket.MyTicketList"
KORAIL_MYTICKET_SEAT = f"{KORAIL_MOBILE}.refunds.SelTicketInfo"

KORAIL_MYRESERVATIONLIST = f"{KORAIL_MOBILE}.reservation.ReservationView"
KORAIL_CANCEL = f"{KORAIL_MOBILE}.reservationCancel.ReservationCancelChk"

KORAIL_STATION_DB = f"{KORAIL_MOBILE}.common.stationinfo?device=ip"
KORAIL_STATION_DB_DATA = f"{KORAIL_MOBILE}.common.stationdata"
KORAIL_EVENT = f"{KORAIL_MOBILE}.common.event"
KORAIL_PAYMENT = f"{KORAIL_DOMAIN}/ebizmw/PrdPkgMainList.do"
KORAIL_PAYMENT_VOUCHER = f"{KORAIL_DOMAIN}/ebizmw/PrdPkgBoucherView.do"

KORAIL_CODE = f"{KORAIL_MOBILE}.common.code.do"

DEFAULT_USER_AGENT = "Dalvik/2.1.0 (Linux; U; Android 5.1.1; Nexus 4 Build/LMY48T)"
DEFAULT_TIMEOUT = 10  # seconds


def _get(data: dict, key: str, default: Any = None) -> Any:
    return data.get(key, default)


class Schedule:
    """Korail train object. Highly inspired by `korail.py
    <https://raw.githubusercontent.com/devxoul/korail/master/korail/korail.py>`_
    by `Suyeol Jeon <http://xoul.kr/>`_ at 2014.

    train_type (h_trn_clsf_cd):
        00: KTX, 01: 새마을호, 02: 무궁화호, 03: 통근열차, 04: 누리로,
        05: 전체(검색시에만 사용), 06: 공항직통, 07: KTX-산천, 08: ITX-새마을, 09: ITX-청춘
    """

    def __init__(self, data: dict):
        self.raw: dict = data

        self.train_type = _get(data, "h_trn_clsf_cd")
        self.train_type_name = _get(data, "h_trn_clsf_nm")
        self.train_group = _get(data, "h_trn_gp_cd")
        self.train_no = _get(data, "h_trn_no")
        self.delay_time = _get(data, "h_expct_dlay_hr")

        self.dep_name = _get(data, "h_dpt_rs_stn_nm")
        self.dep_code = _get(data, "h_dpt_rs_stn_cd")
        self.dep_date = _get(data, "h_dpt_dt")  # yyyyMMdd
        self.dep_time = _get(data, "h_dpt_tm")  # hhmmss

        self.arr_name = _get(data, "h_arv_rs_stn_nm")
        self.arr_code = _get(data, "h_arv_rs_stn_cd")
        self.arr_date = _get(data, "h_arv_dt")
        self.arr_time = _get(data, "h_arv_tm")

        self.run_date = _get(data, "h_run_dt")

    def __repr__(self) -> str:
        dep_time = f"{self.dep_time[:2]}:{self.dep_time[2:4]}"
        arr_time = f"{self.arr_time[:2]}:{self.arr_time[2:4]}"
        dep_date = f"{int(self.dep_date[4:6])}월 {int(self.dep_date[6:])}일"
        return (f"[{self.train_type_name}] {dep_date}, "
                f"{self.dep_name}~{self.arr_name}({dep_time}~{arr_time})")


class Train(Schedule):
    """검색 결과 열차.

    special_seat (h_spe_rsv_cd) / general_seat (h_gen_rsv_cd):
        00: 해당 객실 없음, 11: 예약 가능, 13: 매진
    wait_reserve_flag (h_wait_rsv_flg):
        -2: 좌석 있음, 9: 예약 대기(일반실), 0: 예약 대기 없음
    """

    def __init__(self, data: dict):
        super().__init__(data)
        self.reserve_possible = _get(data, "h_rsv_psb_flg")  # 'Y' or 'N'
        self.reserve_possible_name = _get(data, "h_rsv_psb_nm")

        self.special_seat = _get(data, "h_spe_rsv_cd")
        self.general_seat = _get(data, "h_gen_rsv_cd")

        flag = _get(data, "h_wait_rsv_flg")
        self.wait_reserve_flag = int(flag) if flag not in (None, "") else None

    def __repr__(self) -> str:
        repr_str = super().__repr__()

        if self.reserve_possible_name is not None:
            seats = []
            if self.has_special_seat():
                seats.append("특실")
            if self.has_general_seat():
                seats.append("일반실")
            if self.has_standing_seat():
                seats.append("입석+좌석")
            if self.has_general_waiting_list():
                seats.append("예약 대기(일반)")

            repr_str += " " + ",".join(seats) + " " + self.reserve_possible_name.replace("\n", " ")

        return repr_str

    def has_special_seat(self) -> bool:
        return self.special_seat == "11"

    def has_general_seat(self) -> bool:
        return self.general_seat == "11"

    def has_standing_seat(self) -> bool:
        """입석(+좌석) 구매 가능 여부.

        NOTE: 코레일 API 의 입석 관련 필드는 공개 문서가 없어 실측 검증이 필요하다.
        1) 'h_stnd_rsv_cd' 필드가 응답에 있으면 '11'(가능) 여부로 판단하고,
        2) 없으면 예약가능 안내문구(h_rsv_psb_nm)에 '입석'이 있고 '매진'/'역발매'가 없을 때 가능으로 본다.
        """
        code = self.raw.get("h_stnd_rsv_cd")
        if code not in (None, ""):
            return code == "11"
        name = (self.reserve_possible_name or "").replace("\n", " ")
        return "입석" in name and "매진" not in name and "역발매" not in name

    def has_seat(self) -> bool:
        return self.has_general_seat() or self.has_special_seat()

    def has_waiting_list(self) -> bool:
        return self.has_general_waiting_list()

    def has_general_waiting_list(self) -> bool:
        return self.wait_reserve_flag == 9


class Ticket(Train):
    """Ticket object"""

    def __init__(self, data: dict):
        raw_data = data["ticket_list"][0]["train_info"][0]
        super().__init__(raw_data)

        self.seat_no_end = _get(raw_data, "h_seat_no_end")
        self.seat_no_count = int(_get(raw_data, "h_seat_cnt"))

        self.buyer_name = _get(raw_data, "h_buy_ps_nm")
        self.sale_date = _get(raw_data, "h_orgtk_sale_dt")
        self.sale_info1 = _get(raw_data, "h_orgtk_wct_no")
        self.sale_info2 = _get(raw_data, "h_orgtk_ret_sale_dt")
        self.sale_info3 = _get(raw_data, "h_orgtk_sale_sqno")
        self.sale_info4 = _get(raw_data, "h_orgtk_ret_pwd")
        self.price = int(_get(raw_data, "h_rcvd_amt"))

        self.car_no = _get(raw_data, "h_srcar_no")
        self.seat_no = _get(raw_data, "h_seat_no")

    def __repr__(self) -> str:
        repr_str = Schedule.__repr__(self)
        repr_str += f" => {self.car_no}호"
        if int(self.seat_no_count) != 1:
            repr_str += f" {self.seat_no}~{self.seat_no_end}"
        else:
            repr_str += f" {self.seat_no}"
        repr_str += f", {self.price}원"
        return repr_str

    def get_ticket_no(self) -> str:
        return "-".join(map(str, (self.sale_info1, self.sale_info2, self.sale_info3, self.sale_info4)))


class Passenger:
    """승객. Passenger List를 검색과 예약에 쓰도록 한다."""
    typecode: str | None = None  # txtPsgTpCd1 (어른 1, 어린이 3)
    discount_type = "000"  # txtDiscKndCd1 (경로, 동반유아, 군장병 등..)
    count = 1  # txtCompaCnt1
    card = ""
    card_no = ""
    card_pw = ""

    @staticmethod
    def reduce(passenger_list: Iterable[Passenger]) -> list[Passenger]:
        """Reduce passenger's list."""
        passenger_list = list(passenger_list)
        if any(not isinstance(x, Passenger) for x in passenger_list):
            raise TypeError("Passengers must be based on Passenger")

        groups = itertools.groupby(passenger_list, lambda x: x.group_key())
        merged = [reduce(lambda a, b: a + b, g) for _, g in groups]
        return [x for x in merged if x.count > 0]

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Passenger is abstract class. Do not make instance.")

    def __init_internal__(self, typecode, count=1, discount_type="000", card="", card_no="", card_pw=""):
        self.typecode = typecode
        self.count = count
        self.discount_type = discount_type
        self.card = card
        self.card_no = card_no
        self.card_pw = card_pw

    def __add__(self, other: Passenger) -> Passenger:
        assert isinstance(other, self.__class__)
        if self.group_key() == other.group_key():
            return self.__class__(count=self.count + other.count, discount_type=self.discount_type,
                                  card=self.card, card_no=self.card_no, card_pw=self.card_pw)
        raise TypeError(f"other's group_key({other.group_key()}) is not equal to self's group_key({self.group_key()}).")

    def group_key(self) -> str:
        """get group string from attributes except count"""
        return f"{self.typecode}_{self.discount_type}_{self.card}_{self.card_no}_{self.card_pw}"

    def get_dict(self, index: int) -> dict:
        assert isinstance(index, int)
        i = str(index)
        return {
            "txtPsgTpCd" + i: self.typecode,
            "txtDiscKndCd" + i: self.discount_type,
            "txtCompaCnt" + i: self.count,
            "txtCardCode_" + i: self.card,
            "txtCardNo_" + i: self.card_no,
            "txtCardPw_" + i: self.card_pw,
        }


# noinspection PyMissingConstructor
class AdultPassenger(Passenger):
    def __init__(self, count=1, discount_type="000", card="", card_no="", card_pw=""):
        Passenger.__init_internal__(self, "1", count, discount_type, card, card_no, card_pw)


# noinspection PyMissingConstructor
class ChildPassenger(Passenger):
    def __init__(self, count=1, discount_type="000", card="", card_no="", card_pw=""):
        Passenger.__init_internal__(self, "3", count, discount_type, card, card_no, card_pw)


# noinspection PyMissingConstructor
class ToddlerPassenger(Passenger):
    def __init__(self, count=1, discount_type="321", card="", card_no="", card_pw=""):
        Passenger.__init_internal__(self, "3", count, discount_type, card, card_no, card_pw)


# noinspection PyMissingConstructor
class SeniorPassenger(Passenger):
    def __init__(self, count=1, discount_type="131", card="", card_no="", card_pw=""):
        Passenger.__init_internal__(self, "1", count, discount_type, card, card_no, card_pw)


class TrainType:
    KTX = "100"  # KTX, KTX-산천
    SAEMAEUL = "101"  # 새마을호
    MUGUNGHWA = "102"  # 무궁화호
    TONGGUEN = "103"  # 통근열차
    NURIRO = "102"  # 누리로
    ALL = "109"  # 전체
    AIRPORT = "105"  # 공항직통
    KTX_SANCHEON = "100"  # KTX-산천
    ITX_SAEMAEUL = "101"  # ITX-새마을
    ITX_CHEONGCHUN = "104"  # ITX-청춘

    def __init__(self):
        raise NotImplementedError("Do not make instance.")


class ReserveOption:
    GENERAL_FIRST = "GENERAL_FIRST"  # 일반실 우선
    GENERAL_ONLY = "GENERAL_ONLY"  # 일반실만
    SPECIAL_FIRST = "SPECIAL_FIRST"  # 특실 우선
    SPECIAL_ONLY = "SPECIAL_ONLY"  # 특실만

    def __init__(self):
        raise NotImplementedError("Do not make instance.")


class Reservation(Train):
    """Reservation object"""

    def __init__(self, data: dict):
        super().__init__(data)
        # 이 두 필드가 결과에 빠져있음
        self.dep_date = _get(data, "h_run_dt")
        self.arr_date = _get(data, "h_run_dt")

        self.rsv_id = _get(data, "h_pnr_no")
        self.seat_no_count = int(_get(data, "h_tot_seat_cnt"))
        self.buy_limit_date = _get(data, "h_ntisu_lmt_dt")
        self.buy_limit_time = _get(data, "h_ntisu_lmt_tm")
        self.price = int(_get(data, "h_rsv_amt"))
        self.journey_no = _get(data, "txtJrnySqno", "001")
        self.journey_cnt = _get(data, "txtJrnyCnt", "01")
        self.rsv_chg_no = _get(data, "hidRsvChgNo", "00000")

    def __repr__(self) -> str:
        repr_str = super().__repr__()
        repr_str += f", {self.price}원({self.seat_no_count}석)"
        buy_limit_time = f"{self.buy_limit_time[:2]}:{self.buy_limit_time[2:4]}"
        buy_limit_date = f"{int(self.buy_limit_date[4:6])}월 {int(self.buy_limit_date[6:])}일"
        repr_str += f", 구입기한 {buy_limit_date} {buy_limit_time}"
        return repr_str


class ExceptionForm(type):
    codes: set[str] = set()

    def __contains__(cls, item):
        return item in cls.codes


class KorailError(Exception, metaclass=ExceptionForm):
    """Korail Base Error Class"""

    def __init__(self, msg, code=None):
        super().__init__(msg, code)
        self.msg = msg
        self.code = code

    def __str__(self):
        return f"{self.msg} ({self.code})"


class NeedToLoginError(KorailError):
    codes = {"P058"}

    def __init__(self, code=None):
        super().__init__("Need to Login", code)


class NoResultsError(KorailError):
    codes = {
        "P100",
        "WRG000000",
        "WRD000061",  # 직통열차는 없지만, 환승으로 조회 가능합니다.
        "WRT300005",
    }

    def __init__(self, code=None):
        super().__init__("No Results", code)


class SoldOutError(KorailError):
    codes = {"ERR211161"}

    def __init__(self, code=None):
        super().__init__("Sold out", code)


class MacroBlockedError(KorailError):
    """코레일 서버가 비공식 클라이언트/자동화 요청을 차단한 경우.

    이 에러가 나면 재시도하지 말고 즉시 중단해야 한다.
    (차단 조치를 회피하는 재시도는 이용약관 및 정보통신망법상 문제가 될 수 있음)
    """
    codes = {"MACRO ERROR"}

    def __init__(self, code=None):
        super().__init__("Korail blocked the request as a macro", code)


class Korail:
    """Korail object"""

    _device = "AD"
    _version = "190617001"

    def __init__(self, korail_id=None, korail_pw=None, auto_login=True, want_feedback=False,
                 timeout: float = DEFAULT_TIMEOUT):
        # 원본은 클래스 변수로 세션을 공유해서 인스턴스간 쿠키가 섞이는 문제가 있었음
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
        self._key = "korail1234567890"
        self._idx = None
        self.timeout = timeout

        self.korail_id = korail_id
        self.korail_pw = korail_pw
        self.want_feedback = want_feedback
        self.logined = False
        self.membership_number = None
        self.name = None
        self.email = None
        if auto_login and korail_id and korail_pw:
            self.login(korail_id, korail_pw)

    def _get(self, url, params):
        r = self._session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return json.loads(r.text)

    def _post(self, url, data):
        r = self._session.post(url, data=data, timeout=self.timeout)
        r.raise_for_status()
        return json.loads(r.text)

    def __enc_password(self, password: str):
        # 로그인할 때만 필요하므로 지연 import (알림 전용 사용 시 pycryptodome 불필요)
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad

        j = self._post(KORAIL_CODE, {"code": "app.login.cphd"})

        if j["strResult"] == "SUCC" and j.get("app.login.cphd") is not None:
            self._idx = j["app.login.cphd"]["idx"]
            key = j["app.login.cphd"]["key"]

            encrypt_key = key.encode("utf-8")
            iv = key[:16].encode("utf-8")
            cipher = AES.new(encrypt_key, AES.MODE_CBC, iv)
            padded_data = pad(password.encode("utf-8"), AES.block_size)
            return base64.b64encode(base64.b64encode(cipher.encrypt(padded_data))).decode("utf-8")
        return False

    def login(self, korail_id=None, korail_pw=None) -> bool:
        """Login to Korail server.

        :param korail_id: membership number(8 digits) / phone number(xxx-xxxx-xxxx) / email
        :param korail_pw: password
        """
        if korail_id is None:
            korail_id = self.korail_id
        else:
            self.korail_id = korail_id

        if korail_pw is None:
            korail_pw = self.korail_pw
        else:
            self.korail_pw = korail_pw

        if EMAIL_REGEX.match(korail_id):
            txt_input_flg = "5"
        elif PHONE_NUMBER_REGEX.match(korail_id):
            txt_input_flg = "4"
        else:
            txt_input_flg = "2"

        data = {
            "Device": self._device,
            "Version": "231231001",  # HACK
            # 2: membership number, 4: phone number, 5: email
            "txtInputFlg": txt_input_flg,
            "txtMemberNo": korail_id,
            "txtPwd": self.__enc_password(korail_pw),
            "idx": self._idx,
        }

        j = self._post(KORAIL_LOGIN, data)

        if j["strResult"] == "SUCC" and j.get("strMbCrdNo") is not None:
            self._key = j["Key"]
            self.membership_number = j["strMbCrdNo"]
            self.name = j["strCustNm"]
            self.email = j["strEmailAdr"]
            self.logined = True
            return True

        if _get(j, "h_msg_cd") in MacroBlockedError:
            raise MacroBlockedError(_get(j, "h_msg_cd"))
        self.logined = False
        return False

    def logout(self) -> None:
        """Logout from Korail server"""
        self._session.get(KORAIL_LOGOUT, timeout=self.timeout)
        self.logined = False

    def _result_check(self, j: dict) -> bool:
        """Result data check"""
        if self.want_feedback:
            print(j.get("h_msg_txt"))

        if j.get("strResult") == "FAIL":
            h_msg_cd = _get(j, "h_msg_cd")
            h_msg_txt = _get(j, "h_msg_txt")
            for err in (NoResultsError, NeedToLoginError, SoldOutError, MacroBlockedError):
                if h_msg_cd in err:
                    raise err(h_msg_cd)
            raise KorailError(h_msg_txt, h_msg_cd)
        return True

    def search_train_allday(self, dep, arr, date=None, time=None, train_type=TrainType.ALL,
                            passengers=None, include_no_seats=False) -> list[Train]:
        """Search all trains for specific time and date."""
        min1 = timedelta(minutes=1)
        all_trains: list[Train] = []
        dep_time = time
        for _ in range(15):  # 최대 15번 호출
            try:
                trains = self.search_train(dep, arr, date, dep_time, train_type, passengers, True)
            except NoResultsError:
                break
            all_trains.extend(trains)
            # 마지막 승차권의 출발시각이 23시 59분이면 검색 중지 (다음 날 승차권 검색 방지)
            last_dep_time = datetime.strptime(all_trains[-1].dep_time, "%H%M%S")
            if last_dep_time.hour == 23 and last_dep_time.minute == 59:
                break
            # 마지막 열차시간에 1분 더해서 계속 검색
            dep_time = (last_dep_time + min1).strftime("%H%M%S")

        if not include_no_seats:
            all_trains = [x for x in all_trains if x.has_seat()]

        if not all_trains:
            raise NoResultsError()

        return all_trains

    def search_train(self, dep, arr, date=None, time=None, train_type=TrainType.ALL,
                     passengers=None, include_no_seats=False, include_waiting_list=False) -> list[Train]:
        """Search trains for specific time and date.

        :param dep: 출발역 (예: '서울')
        :param arr: 도착역 (예: '부산')
        :param date: (optional) yyyyMMdd
        :param time: (optional) hhmmss
        :param train_type: (optional) TrainType.*
        :param passengers: (optional) Passenger 리스트. None 이면 어른 1명
        :param include_no_seats: True 면 좌석 없는 열차도 포함
        :param include_waiting_list: True 면 예약대기 가능한 열차도 포함

            >>> korail.search_train('서울', '동대구', '20140815', '144000')
        """
        # 코레일에 열차 티켓 리스트 API 요청시 한국시간을 기준으로 함.
        kst_now = datetime.now(KST)
        if date is None:
            date = kst_now.strftime("%Y%m%d")
        if time is None:
            time = kst_now.strftime("%H%M%S")

        if passengers is None:
            passengers = [AdultPassenger()]

        passengers = Passenger.reduce(passengers)

        def count_of(cls):
            return sum(p.count for p in passengers if isinstance(p, cls))

        data = {
            "Device": self._device,
            "radJobId": "1",
            "selGoTrain": train_type,
            "txtCardPsgCnt": "0",
            "txtGdNo": "",
            "txtGoAbrdDt": date,
            "txtGoEnd": arr,
            "txtGoHour": time,
            "txtGoStart": dep,
            "txtJobDv": "",
            "txtMenuId": "11",
            "txtPsgFlg_1": count_of(AdultPassenger),  # 어른
            "txtPsgFlg_2": count_of(ChildPassenger),  # 어린이
            "txtPsgFlg_8": count_of(ToddlerPassenger),  # 유아
            "txtPsgFlg_3": count_of(SeniorPassenger),  # 경로
            "txtPsgFlg_4": "0",  # 중증 장애인
            "txtPsgFlg_5": "0",  # 경증 장애인
            "txtSeatAttCd_2": "000",
            "txtSeatAttCd_3": "000",
            "txtSeatAttCd_4": "015",
            "txtTrnGpCd": train_type,
            "Version": self._version,
        }

        j = self._get(KORAIL_SEARCH_SCHEDULE, data)
        self._result_check(j)

        trains = [Train(info) for info in j["trn_infos"]["trn_info"]]

        filter_fns = [lambda x: x.has_seat()]
        if include_no_seats:
            filter_fns.append(lambda x: not x.has_seat())
        if include_waiting_list:
            filter_fns.append(lambda x: x.has_waiting_list())

        trains = [t for t in trains if any(f(t) for f in filter_fns)]

        if not trains:
            raise NoResultsError()

        return trains

    def reserve(self, train: Train, passengers=None, option=ReserveOption.GENERAL_FIRST,
                try_waiting=False) -> Reservation | None:
        """Reserve a train.

        :param train: Train 인스턴스
        :param passengers: (optional) Passenger 리스트. None 이면 어른 1명
        :param option: ReserveOption.GENERAL_FIRST / GENERAL_ONLY / SPECIAL_FIRST / SPECIAL_ONLY
        :param try_waiting: 좌석이 없으면 예약대기 신청
        """
        reserving_seat = True
        seat_type = None
        try:
            if not train.has_seat():
                raise SoldOutError()
            elif option == ReserveOption.GENERAL_ONLY:
                if not train.has_general_seat():
                    raise SoldOutError()
                seat_type = "1"
            elif option == ReserveOption.SPECIAL_ONLY:
                if not train.has_special_seat():
                    raise SoldOutError()
                seat_type = "2"
            elif option == ReserveOption.GENERAL_FIRST:
                seat_type = "1" if train.has_general_seat() else "2"
            elif option == ReserveOption.SPECIAL_FIRST:
                seat_type = "2" if train.has_special_seat() else "1"
        except SoldOutError:
            if try_waiting and option != ReserveOption.SPECIAL_ONLY and train.has_general_waiting_list():
                reserving_seat = False
                seat_type = "1"
            else:
                raise

        if passengers is None:
            passengers = [AdultPassenger()]

        passengers = Passenger.reduce(passengers)
        cnt = sum(p.count for p in passengers)
        data = {
            "Device": self._device,
            "Version": self._version,
            "Key": self._key,
            "txtGdNo": "",
            "txtJobId": "1101" if reserving_seat else "1102",
            "txtTotPsgCnt": cnt,
            "txtSeatAttCd1": "000",
            "txtSeatAttCd2": "000",
            "txtSeatAttCd3": "000",
            "txtSeatAttCd4": "015",
            "txtSeatAttCd5": "000",
            "hidFreeFlg": "N",
            "txtStndFlg": "N",
            "txtMenuId": "11",
            "txtSrcarCnt": "0",
            "txtJrnyCnt": "1",

            # 여정정보1
            "txtJrnySqno1": "001",
            "txtJrnyTpCd1": "11",
            "txtDptDt1": train.dep_date,
            "txtDptRsStnCd1": train.dep_code,
            "txtDptTm1": train.dep_time,
            "txtArvRsStnCd1": train.arr_code,
            "txtTrnNo1": train.train_no,
            "txtRunDt1": train.run_date,
            "txtTrnClsfCd1": train.train_type,
            "txtPsrmClCd1": seat_type,
            "txtTrnGpCd1": train.train_group,
            "txtChgFlg1": "",

            # 여정정보2
            "txtJrnySqno2": "",
            "txtJrnyTpCd2": "",
            "txtDptDt2": "",
            "txtDptRsStnCd2": "",
            "txtDptTm2": "",
            "txtArvRsStnCd2": "",
            "txtTrnNo2": "",
            "txtRunDt2": "",
            "txtTrnClsfCd2": "",
            "txtPsrmClCd2": "",
            "txtChgFlg2": "",
        }

        for index, psg in enumerate(passengers, start=1):
            data.update(psg.get_dict(index))

        j = self._get(KORAIL_TICKETRESERVATION, data)
        if self._result_check(j):
            rsv_id = j["h_pnr_no"]
            rsvlist = [x for x in self.reservations() if x.rsv_id == rsv_id]
            if len(rsvlist) == 1:
                return rsvlist[0]
        return None

    def tickets(self) -> list[Ticket]:
        """Get list of tickets"""
        data = {
            "Device": self._device,
            "Version": self._version,
            "Key": self._key,
            "txtIndex": "1",
            "h_page_no": "1",
            "txtDeviceId": "",
            "h_abrd_dt_from": "",
            "h_abrd_dt_to": "",
        }

        j = self._get(KORAIL_MYTICKETLIST, data)
        try:
            self._result_check(j)
        except NoResultsError:
            return []

        tickets = []
        for info in j["reservation_list"]:
            ticket = Ticket(info)
            seat_params = {
                "Device": self._device,
                "Version": self._version,
                "Key": self._key,
                "h_orgtk_wct_no": ticket.sale_info1,
                "h_orgtk_ret_sale_dt": ticket.sale_info2,
                "h_orgtk_sale_sqno": ticket.sale_info3,
                "h_orgtk_ret_pwd": ticket.sale_info4,
            }
            sj = self._get(KORAIL_MYTICKET_SEAT, seat_params)
            if self._result_check(sj):
                seat = sj["ticket_infos"]["ticket_info"][0]["tk_seat_info"][0]
                ticket.seat_no = _get(seat, "h_seat_no")
                ticket.seat_no_end = None
            tickets.append(ticket)
        return tickets

    def reservations(self) -> list[Reservation]:
        """Get My Reservations"""
        data = {
            "Device": self._device,
            "Version": self._version,
            "Key": self._key,
        }
        j = self._get(KORAIL_MYRESERVATIONLIST, data)
        try:
            self._result_check(j)
        except NoResultsError:
            return []

        reserves = []
        for info in j["jrny_infos"]["jrny_info"]:
            for tinfo in info["train_infos"]["train_info"]:
                reserves.append(Reservation(tinfo))
        return reserves

    def cancel(self, rsv: Reservation) -> bool:
        """Cancel Reservation : Canceling is for reservation, for ticket would be Refunding"""
        assert isinstance(rsv, Reservation)
        data = {
            "Device": self._device,
            "Version": self._version,
            "Key": self._key,
            "txtPnrNo": rsv.rsv_id,
            "txtJrnySqno": rsv.journey_no,
            "txtJrnyCnt": rsv.journey_cnt,
            "hidRsvChgNo": rsv.rsv_chg_no,
        }
        # 원본은 GET 요청에 data= 를 넘겨 파라미터가 전송되지 않는 버그가 있었음
        j = self._get(KORAIL_CANCEL, data)
        return self._result_check(j)
