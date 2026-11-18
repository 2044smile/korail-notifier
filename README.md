korail-notifier
===============

[carpedm20/korail2](https://github.com/carpedm20/korail2) 를 **Python 3.10** 으로 포팅하고,
**일반실 빈자리 / 입석+좌석**이 생기면 **텔레그램으로 알림**을 보내는 감시 기능을 추가한 포크입니다.
자동 예매는 하지 않습니다. 알림을 받으면 코레일톡 앱에서 직접 예매하세요.

> ⚠️ **현재 상태 (2026-11 확인)**: 코레일 서버가 이 라이브러리의 요청에 `MACRO ERROR`
> (앱 버전 업데이트 요구)를 응답하며 차단하고 있습니다. 이 경우 notifier 는 텔레그램으로
> 차단 사실을 알리고 **재시도 없이 종료**합니다. 차단 회피 기능은 제공하지 않습니다.

### 알림 조건 (일반실 기준, 특실 제외)

| `SEAT_MODE` | 알림 조건 |
|---|---|
| `seat` | 일반실 좌석 예약 가능 |
| `seat_or_standing` | 일반실 좌석 **또는** 입석+좌석 구매 가능 |

- 같은 열차는 한 번만 알리고, 매진됐다가 다시 풀리면 다시 알립니다.
- 조회 간격 기본 5분, **최소 3분** (서버 부하 방지를 위해 강제).
- 연속 실패 시 간격을 늘리고(최대 60분), 3회 연속 실패하면 텔레그램으로 알립니다.
- 입석 판별(`Train.has_standing_seat`)은 공식 문서가 없어 실측 검증이 필요합니다.

### 빠른 시작

```bash
python3.10 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # 값 채우기 (.env 는 git 에 올라가지 않음)
python -m notifier --test-telegram   # 텔레그램 연결 확인
python -m notifier                   # 감시 시작
```

Docker:

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f
```

텔레그램 설정: [@BotFather](https://t.me/BotFather) 에서 `/newbot` → 토큰을 `TELEGRAM_BOT_TOKEN` 에,
봇에게 아무 메시지나 보낸 뒤 `https://api.telegram.org/bot<TOKEN>/getUpdates` 의 `chat.id` 를 `TELEGRAM_CHAT_ID` 에 넣습니다.

### 테스트

```bash
python -m unittest test.test_notifier
```

### 원본 대비 변경점 (Python 3.10 포팅)

- Python 2 호환 코드 및 `six` 의존성 제거, f-string/타입힌트 적용
- 클래스 변수로 공유되던 `requests` 세션을 인스턴스별로 분리
- 모든 요청에 timeout 적용, `datetime.utcnow()` → KST timezone-aware
- `cancel()` 이 GET 에 `data=` 를 넘겨 파라미터가 전송되지 않던 버그 수정
- `MACRO ERROR` 응답을 `MacroBlockedError` 로 구분
- 로그인 없이 조회만 할 때는 `pycryptodome` 를 import 하지 않음
- 원본 저장소의 `korail.py`(하드코딩된 계정 정보 포함 예제) 삭제

---

Legal disclaimer
---

**Usage of korail for attacking targets without prior mutual consent is illegal**. It's the end user's responsibility to obey all applicable local, state and federal laws. Developers assume no liability and are not responsible for any misuse or damage caused by this program. Only use for educational purposes.


<br/>

Korail2
=======

[![Build Status](https://travis-ci.org/sng2c/korail2.svg?branch=master)](https://travis-ci.org/sng2c/korail2)

Korail (www.letskorail.com) wrapper for Python.

This project was inspired from [korail](https://github.com/devxoul/korail) of [devxoul](https://github.com/devxoul).


Documentation
-------------

The documentation is available at [here](http://carpedm20.github.io/korail2/)


Installing
----------

To install korail2, simply:

    $ pip install korail2

Or, you can use:

    $ easy_install korail2

Or, you can also install manually:

    $ git clone git://github.com/carpedm20/korail2.git
    $ cd korail2
    $ python setup.py install

Using
-----

### 1. Login ###

First, you need to create a Korail object.

```python
>>> from korail2 import *
>>> korail = Korail("12345678", YOUR_PASSWORD) # with membership number
>>> korail = Korail("carpedm20@gmail.com", YOUR_PASSWORD) # with email
>>> korail = Korail("010-9964-xxxx", YOUR_PASSWORD) # with phone number
```

If you do not want login automatically, 

```python
>>> korail = Korail("12345678", YOUR_PASSWORD, auto_login=False)
>>> korail.login()
True
```

When you want change ID using existing object,

```python
>>> korail.login(ANOTHER_ID, ANOTHER_PASSWORD)
True
```

### 2. Search train ###

You can search train schedules `search_train` and `search_train_allday` methods.

- `search_train` returns 10 results max. Faster than `search_train_allday`.
- `search_train_allday` returns all results after the time.
- `search_train_allday` uses `search_train` repeatedly.

`search_train` and `search_train_allday` methods take these arguments:

- dep : A departure station in Korean  ex) '서울'
- arr : A arrival station in Korean  ex) '부산'
- date : (optional) A departure date in `yyyyMMdd` format
- time : (optional) A departure time in `hhmmss` format
- train_type: (optional) A type of train. You can use constants of TrainType class here.
    default value is TrainType.ALL.
    - 00: TrainType.KTX - KTX 
    - 01: TrainType.SAEMAEUL - 새마을호     
    - 02: TrainType.MUGUNGHWA - 무궁화호
    - 03: TrainType.TONGGEUN - 통근열차
    - 04: TrainType.NURIRO - 누리로
    - 05: TrainType.ALL - 전체 
    - 06: TrainType.AIRPORT - 공항직통
    - 07: TrainType.KTX_SANCHEON - KTX-산천
    - 08: TrainType.ITX_SAEMAEUL - ITX-새마을 
    - 09: TrainType.ITX_CHEONGCHUN - ITX-청춘
- (optional) passengers=None : List of Passenger Objects. None means 1 AdultPassenger.
- (optional) include_no_seats=False : When True, a result includes trains which has no seats.

Below is a sample usage of `search_train`:

```python
>>> dep = '서울'
>>> arr = '동대구'
>>> date = '20140815'
>>> time = '144000'
>>> trains = korail.search_train(dep, arr, date, time)
[[KTX] 8월 3일, 서울~부산(11:00~13:42) 특실,일반실 예약가능,
 [ITX-새마을] 8월 3일, 서울~부산(11:04~16:00) 일반실 예약가능,
 [KTX] 8월 3일, 서울~부산(12:00~14:43) 특실,일반실 예약가능,
 [KTX] 8월 3일, 서울~부산(12:30~15:13) 특실,일반실 예약가능,
 [KTX] 8월 3일, 서울~부산(12:40~15:45) 특실,일반실 예약가능,
 [KTX] 8월 3일, 서울~부산(12:55~15:26) 특실,일반실 예약가능,
 [KTX] 8월 3일, 서울~부산(13:00~15:37) 특실,일반실 예약가능,
 [KTX] 8월 3일, 서울~부산(13:10~15:58) 특실,일반실 예약가능]
```

When you want to see sold-out trains.

```python
>>> trains = korail.search_train(dep, arr, date, time, include_no_seats=True)
[[KTX] 8월 3일, 서울~부산(11:00~13:42) 특실,일반실 예약가능,
 [ITX-새마을] 8월 3일, 서울~부산(11:04~16:00) 일반실 예약가능,
 [무궁화호] 8월 3일, 서울~부산(11:08~16:54) 입석 역발매중,
 [ITX-새마을] 8월 3일, 서울~부산(11:50~16:50) 입석 역발매중,
 [KTX] 8월 3일, 서울~부산(12:00~14:43) 특실,일반실 예약가능,
 [KTX] 8월 3일, 서울~부산(12:30~15:13) 특실,일반실 예약가능,
 [KTX] 8월 3일, 서울~부산(12:40~15:45) 특실,일반실 예약가능,
 [KTX] 8월 3일, 서울~부산(12:55~15:26) 특실,일반실 예약가능,
 [KTX] 8월 3일, 서울~부산(13:00~15:37) 특실,일반실 예약가능,
 [KTX] 8월 3일, 서울~부산(13:10~15:58) 특실,일반실 예약가능]
```

#### 2-1. About `passengers` argument

`passengers` is a list(or tuple) of Passeger Objects.
By this, you can search for multiple passengers.
There are 3 types of Passengers now, AdultPassenger, ChildPassenger and SeniorPassenger.

```python
# for 1 adult, 1 child
>>> psgrs = [AdultPassenger(), ChildPassenger()]

# for 2 adults, 1 child
>>> psgrs = [AdultPassenger(2), ChildPassenger(1)]
# ditto. They are being added each other by same group.
>>> psgrs = [AdultPassenger(), AdultPassenger(), ChildPassenger()]

# for 2 adults, 1 child, 1 senior
>>> psgrs = [AdultPassenger(2), ChildPassenger(), SeniorPassenger()]

# for 1 adult, It supports negative count or zero count. 
# But it uses passengers which the sum is greater than zero.
>>> psgrs = [AdultPassenger(2), AdultPassenger(-1)]
>>> psgrs = [AdultPassenger(), SeniorPassenger(0)]

# Nothing
>>> psgrs = [AdultPassenger(0), SeniorPassenger(0)]

# then search or reserve train
>>> trains = korail.search_train(dep, arr, date, time, passengers=psgrs)
...
>>> korail.reserve(trains[0], psgrs)
...
```

### 3. Make a reservation ####

You can get your tickets with `tickets` method.

```python
>>> trains = korail.search_train(dep, arr, date, time)
>>> seat = korail.reserve(trains[0])
>>> seat
[KTX] 8월 23일, 서울~동대구(15:30~17:19) 42500원(1석), 구입기한 8월 18일 14:05
```

Multiple.

```python
>>> trains = korail.search_train(dep, arr, date, time)
>>> seat = korail.reserve(trains[0], passengers=psgrs)
>>> seat
[KTX] 8월 23일, 서울~동대구(15:30~17:19) 42500원(3석), 구입기한 8월 18일 14:05
```

When tickets are not enough much for passengers, it raises SoldOutError.
    
If you want to select priority of seat grade, general or special,
There are 4 options in ReserveOption class.

- GENERAL_FIRST : Economic than Comfortable.
- GENERAL_ONLY  : Reserve only general seats. You are poorman ;-)
- SPECIAL_FIRST : Comfortable than Economic.
- SPECIAL_ONLY  : Richman.

```python
>>> korail.reserve(trains[0], psgrs, ReserveOption.GENERAL_ONLY)
```

### 4. Show reservations ####

You can get your tickes with `tickets` method.

```python
>>> reservations = korail.reservations()
>>> reservations
[[KTX] 8월 23일, 서울~동대구(14:55~16:45) 42500원(1석), 구입기한 8월 18일 14:03,
 [무궁화호] 8월 23일, 서울~동대구(15:03~18:48) 21100원(1석), 구입기한 8월 18일 14:03,
 [KTX] 8월 23일, 서울~동대구(15:30~17:19) 42500원(1석), 구입기한 8월 18일 14:05]
```

### 5. Cancel reservation ###

You can also cancel your reservation using Reservation Object from reservations() call.

```python
>>> korail.cancel(reservations[0])
```

### 6. Get tickets already paid ###

You can see your ticket list with `tickets` method.
You can get the list of paid tickes with `tickets` method.

```python
>>> korail = Korail("12345678", YOUR_PASSWORD, want_feedback=True)
>>> tickets = korail.tickets()
정상발매처리,정상발권처리  # You can see these feedbacks when `want_feedback` is True.
>>> print tickets
[[KTX] 8월 10일, 동대구~울산(09:26~09:54) => 5호 4A, 13900원]
```

Todo
----

1. Implement payment API


License
-------

Source codes are distributed under BSD license.


Author
------

Taehoon Kim / [@carpedm20](http://carpedm20.github.io/about/)

Hanson Kim / [@sng2c](https://github.com/sng2c)
