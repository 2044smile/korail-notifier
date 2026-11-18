"""
    korail2
    ~~~~~~~

    Korail (www.letskorail.com) wrapper for Python 3.10+.

    :copyright: (c) 2014 by Taehoon Kim.
    :license: BSD, see LICENSE for more details.
"""
from .korail2 import (
    Korail, Train, Passenger, AdultPassenger, ChildPassenger, ToddlerPassenger, SeniorPassenger,
    TrainType, ReserveOption,
    KorailError, NeedToLoginError, SoldOutError, NoResultsError, MacroBlockedError,
)

__all__ = [
    "Korail", "Train", "Passenger", "AdultPassenger", "ChildPassenger", "ToddlerPassenger", "SeniorPassenger",
    "TrainType", "ReserveOption",
    "KorailError", "NeedToLoginError", "SoldOutError", "NoResultsError", "MacroBlockedError",
]
