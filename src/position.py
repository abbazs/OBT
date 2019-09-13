# To use this code, make sure you
#
#     import json
#
# and then, to convert JSON from a string, do
#
#     result = position_from_dict(json.loads(json_string))

from typing import Any, Optional, List, TypeVar, Type, cast, Callable


T = TypeVar("T")


def from_float(x: Any) -> float:
    assert isinstance(x, (float, int)) and not isinstance(x, bool)
    return float(x)


def to_float(x: Any) -> float:
    assert isinstance(x, float)
    return x


def from_none(x: Any) -> Any:
    assert x is None
    return x


def from_union(fs, x):
    for f in fs:
        try:
            return f(x)
        except:
            pass
    assert False


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


class EntryAndExit:
    entry: float
    exit: float

    def __init__(self, entry: float, exit: float) -> None:
        self.entry = entry
        self.exit = exit

    @staticmethod
    def from_dict(obj: Any) -> "EntryAndExit":
        assert isinstance(obj, dict)
        entry = from_float(obj.get("ENTRY"))
        exit = from_float(obj.get("EXIT"))
        return EntryAndExit(entry, exit)

    def to_dict(self) -> dict:
        result: dict = {}
        result["ENTRY"] = to_float(self.entry)
        result["EXIT"] = to_float(self.exit)
        return result


class Greek:
    delta: Optional[EntryAndExit]
    gamma: EntryAndExit
    theta: EntryAndExit
    vega: EntryAndExit
    vol: EntryAndExit

    def __init__(
        self,
        delta: EntryAndExit,
        gamma: EntryAndExit,
        theta: EntryAndExit,
        vega: EntryAndExit,
        vol: EntryAndExit,
    ) -> None:
        self.delta = delta
        self.gamma = gamma
        self.theta = theta
        self.vega = vega
        self.vol = vol

    @staticmethod
    def from_dict(obj: Any) -> "Greek":
        assert isinstance(obj, dict)
        delta = from_union([EntryAndExit.from_dict, from_none], obj.get("delta"))
        gamma = EntryAndExit.from_dict(obj.get("gamma"))
        theta = EntryAndExit.from_dict(obj.get("theta"))
        vega = EntryAndExit.from_dict(obj.get("vega"))
        vol = EntryAndExit.from_dict(obj.get("vol"))
        return Greek(delta, gamma, theta, vega, vol)

    def to_dict(self) -> dict:
        result: dict = {}
        result["delta"] = from_union(
            [lambda x: to_class(EntryAndExit, x), from_none], self.delta
        )
        result["gamma"] = to_class(EntryAndExit, self.gamma)
        result["theta"] = to_class(EntryAndExit, self.theta)
        result["vega"] = to_class(EntryAndExit, self.vega)
        result["vol"] = to_class(EntryAndExit, self.vol)
        return result


class LegEntryAndExits:
    greek: Greek
    iv: EntryAndExit
    price: EntryAndExit
    vix: EntryAndExit

    def __init__(
        self, greek: Greek, iv: EntryAndExit, price: EntryAndExit, vix: EntryAndExit
    ) -> None:
        self.greek = greek
        self.iv = iv
        self.price = price
        self.vix = vix

    @staticmethod
    def from_dict(obj: Any) -> "LegEntryAndExits":
        assert isinstance(obj, dict)
        greek = Greek.from_dict(obj.get("greek"))
        iv = EntryAndExit.from_dict(obj.get("iv"))
        price = EntryAndExit.from_dict(obj.get("price"))
        vix = EntryAndExit.from_dict(obj.get("vix"))
        return LegEntryAndExits(greek, iv, price, vix)

    def to_dict(self) -> dict:
        result: dict = {}
        result["greek"] = to_class(Greek, self.greek)
        result["iv"] = to_class(EntryAndExit, self.iv)
        result["price"] = to_class(EntryAndExit, self.price)
        result["vix"] = to_class(EntryAndExit, self.vix)
        return result


class PositionEntryExit:
    iv: EntryAndExit
    spot: EntryAndExit
    vix: EntryAndExit

    def __init__(self, iv: EntryAndExit, spot: EntryAndExit, vix: EntryAndExit) -> None:
        self.iv = iv
        self.spot = spot
        self.vix = vix

    @staticmethod
    def from_dict(obj: Any) -> "PositionEntryExit":
        assert isinstance(obj, dict)
        iv = EntryAndExit.from_dict(obj.get("iv"))
        spot = EntryAndExit.from_dict(obj.get("SPOT"))
        vix = EntryAndExit.from_dict(obj.get("vix"))
        return PositionEntryExit(iv, spot, vix)

    def to_dict(self) -> dict:
        result: dict = {}
        result["iv"] = to_class(EntryAndExit, self.iv)
        result["SPOT"] = to_class(EntryAndExit, self.spot)
        result["vix"] = to_class(EntryAndExit, self.vix)
        return result


class PositionLeg:
    end_date: int
    entry_and_exits: LegEntryAndExits
    expiry_date: int
    instrument: str
    parent: "Position"
    start_date: int
    strike: float
    symbol: str
    trade_type: str

    def __init__(
        self,
        end_date: int,
        entry_and_exits: LegEntryAndExits,
        expiry_date: int,
        instrument: str,
        parent: "Position",
        start_date: int,
        strike: float,
        symbol: str,
        trade_type: str,
    ) -> None:
        self.end_date = end_date
        self.entry_and_exits = entry_and_exits
        self.expiry_date = expiry_date
        self.instrument = instrument
        self.parent = parent
        self.start_date = start_date
        self.strike = strike
        self.symbol = symbol
        self.trade_type = trade_type

    @staticmethod
    def from_dict(obj: Any) -> "PositionLeg":
        assert isinstance(obj, dict)
        end_date = from_int(obj.get("end_date"))
        entry_and_exits = LegEntryAndExits.from_dict(obj.get("entry_and_exits"))
        expiry_date = from_int(obj.get("expiry_date"))
        instrument = from_str(obj.get("instrument"))
        parent = Position.from_dict(obj.get("parent"))
        start_date = from_int(obj.get("start_date"))
        strike = from_float(obj.get("strike"))
        symbol = from_str(obj.get("symbol"))
        trade_type = from_str(obj.get("trade_type"))
        return PositionLeg(
            end_date,
            entry_and_exits,
            expiry_date,
            instrument,
            parent,
            start_date,
            strike,
            symbol,
            trade_type,
        )

    def to_dict(self) -> dict:
        result: dict = {}
        result["end_date"] = from_int(self.end_date)
        result["entry_and_exits"] = to_class(LegEntryAndExits, self.entry_and_exits)
        result["expiry_date"] = from_int(self.expiry_date)
        result["instrument"] = from_str(self.instrument)
        result["parent"] = to_class(Position, self.parent)
        result["start_date"] = from_int(self.start_date)
        result["strike"] = to_float(self.strike)
        result["symbol"] = from_str(self.symbol)
        result["trade_type"] = from_str(self.trade_type)
        return result


class Position:
    end_date: int
    expiry_date: int
    legs: List[PositionLeg]
    name: str
    position_entry_exits: PositionEntryExit
    start_date: int
    symbol: str

    def __init__(
        self,
        end_date: int,
        expiry_date: int,
        legs: List[PositionLeg],
        name: str,
        position_entry_exits: PositionEntryExit,
        start_date: int,
        symbol: str,
    ) -> None:
        self.end_date = end_date
        self.expiry_date = expiry_date
        self.legs = legs
        self.name = name
        self.position_entry_exits = position_entry_exits
        self.start_date = start_date
        self.symbol = symbol

    @staticmethod
    def from_dict(obj: Any) -> "Position":
        assert isinstance(obj, dict)
        end_date = from_int(obj.get("end_date"))
        expiry_date = from_int(obj.get("expiry_date"))
        legs = from_list(PositionLeg.from_dict, obj.get("legs"))
        name = from_str(obj.get("name"))
        position_entry_exits = PositionEntryExit.from_dict(
            obj.get("position_entry_exits")
        )
        start_date = from_int(obj.get("start_date"))
        symbol = from_str(obj.get("symbol"))
        return Position(
            end_date, expiry_date, legs, name, position_entry_exits, start_date, symbol
        )

    def to_dict(self) -> dict:
        result: dict = {}
        result["end_date"] = from_int(self.end_date)
        result["expiry_date"] = from_int(self.expiry_date)
        result["legs"] = from_list(lambda x: to_class(PositionLeg, x), self.legs)
        result["name"] = from_str(self.name)
        result["position_entry_exits"] = to_class(
            PositionEntryExit, self.position_entry_exits
        )
        result["start_date"] = from_int(self.start_date)
        result["symbol"] = from_str(self.symbol)
        return result


def position_from_dict(s: Any) -> Position:
    return Position.from_dict(s)


def position_to_dict(x: Position) -> Any:
    return to_class(Position, x)
