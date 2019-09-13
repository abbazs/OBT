# To use this code, make sure you
#
#     import json
#
# and then, to convert JSON from a string, do
#
#     result = position_from_dict(json.loads(json_string))

from typing import Optional, Any, List, TypeVar, Type, cast, Callable


T = TypeVar("T")


def from_float(x: Any) -> float:
    assert isinstance(x, (float, int)) and not isinstance(x, bool)
    return float(x)


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


def to_float(x: Any) -> float:
    assert isinstance(x, float)
    return x


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
    entry: Optional[float]
    exit: Optional[float]

    def __init__(self, entry: Optional[float], exit: Optional[float]) -> None:
        self.entry = entry
        self.exit = exit

    @staticmethod
    def from_dict(obj: Any) -> "EntryAndExit":
        assert isinstance(obj, dict)
        entry = from_union([from_float, from_none], obj.get("ENTRY"))
        exit = from_union([from_float, from_none], obj.get("EXIT"))
        return EntryAndExit(entry, exit)

    def to_dict(self) -> dict:
        result: dict = {}
        result["ENTRY"] = from_union([to_float, from_none], self.entry)
        result["EXIT"] = from_union([to_float, from_none], self.exit)
        return result


class Greek:
    delta: Optional[EntryAndExit]
    gamma: Optional[EntryAndExit]
    theta: Optional[EntryAndExit]
    vega: Optional[EntryAndExit]
    vol: Optional[EntryAndExit]

    def __init__(
        self,
        delta: Optional[EntryAndExit],
        gamma: Optional[EntryAndExit],
        theta: Optional[EntryAndExit],
        vega: Optional[EntryAndExit],
        vol: Optional[EntryAndExit],
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
        gamma = from_union([EntryAndExit.from_dict, from_none], obj.get("gamma"))
        theta = from_union([EntryAndExit.from_dict, from_none], obj.get("theta"))
        vega = from_union([EntryAndExit.from_dict, from_none], obj.get("vega"))
        vol = from_union([EntryAndExit.from_dict, from_none], obj.get("vol"))
        return Greek(delta, gamma, theta, vega, vol)

    def to_dict(self) -> dict:
        result: dict = {}
        result["delta"] = from_union(
            [lambda x: to_class(EntryAndExit, x), from_none], self.delta
        )
        result["gamma"] = from_union(
            [lambda x: to_class(EntryAndExit, x), from_none], self.gamma
        )
        result["theta"] = from_union(
            [lambda x: to_class(EntryAndExit, x), from_none], self.theta
        )
        result["vega"] = from_union(
            [lambda x: to_class(EntryAndExit, x), from_none], self.vega
        )
        result["vol"] = from_union(
            [lambda x: to_class(EntryAndExit, x), from_none], self.vol
        )
        return result


class LegEntryAndExits:
    greek: Optional[Greek]
    iv: Optional[EntryAndExit]
    price: EntryAndExit
    vix: EntryAndExit

    def __init__(
        self,
        greek: Optional[Greek],
        iv: Optional[EntryAndExit],
        price: EntryAndExit,
        vix: EntryAndExit,
    ) -> None:
        self.greek = greek
        self.iv = iv
        self.price = price
        self.vix = vix

    @staticmethod
    def from_dict(obj: Any) -> "LegEntryAndExits":
        assert isinstance(obj, dict)
        greek = from_union([Greek.from_dict, from_none], obj.get("greek"))
        iv = from_union([EntryAndExit.from_dict, from_none], obj.get("iv"))
        price = EntryAndExit.from_dict(obj.get("price"))
        vix = EntryAndExit.from_dict(obj.get("vix"))
        return LegEntryAndExits(greek, iv, price, vix)

    def to_dict(self) -> dict:
        result: dict = {}
        result["greek"] = from_union(
            [lambda x: to_class(Greek, x), from_none], self.greek
        )
        result["iv"] = from_union(
            [lambda x: to_class(EntryAndExit, x), from_none], self.iv
        )
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
        spot = EntryAndExit.from_dict(obj.get("spot"))
        vix = EntryAndExit.from_dict(obj.get("vix"))
        return PositionEntryExit(iv, spot, vix)

    def to_dict(self) -> dict:
        result: dict = {}
        result["iv"] = to_class(EntryAndExit, self.iv)
        result["spot"] = to_class(EntryAndExit, self.spot)
        result["vix"] = to_class(EntryAndExit, self.vix)
        return result


class PositionLeg:
    end_date: Optional[int]
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
        end_date: Optional[int],
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
        end_date = from_union([from_int, from_none], obj.get("end_date"))
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
        result["end_date"] = from_union([from_int, from_none], self.end_date)
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
    end_date: Optional[int]
    legs: Optional[List[PositionLeg]]
    name: str
    position_entry_exits: Optional[PositionEntryExit]
    start_date: int
    symbol: str

    def __init__(
        self,
        end_date: Optional[int],
        legs: Optional[List[PositionLeg]],
        name: str,
        position_entry_exits: Optional[PositionEntryExit],
        start_date: int,
        symbol: str,
    ) -> None:
        self.end_date = end_date
        self.legs = legs
        self.name = name
        self.position_entry_exits = position_entry_exits
        self.start_date = start_date
        self.symbol = symbol

    @staticmethod
    def from_dict(obj: Any) -> "Position":
        assert isinstance(obj, dict)
        end_date = from_union([from_int, from_none], obj.get("end_date"))
        legs = from_union(
            [lambda x: from_list(PositionLeg.from_dict, x), from_none], obj.get("legs")
        )
        name = from_str(obj.get("name"))
        position_entry_exits = from_union(
            [PositionEntryExit.from_dict, from_none], obj.get("position_entry_exits")
        )
        start_date = from_int(obj.get("start_date"))
        symbol = from_str(obj.get("symbol"))
        return Position(end_date, legs, name, position_entry_exits, start_date, symbol)

    def to_dict(self) -> dict:
        result: dict = {}
        result["end_date"] = from_union([from_int, from_none], self.end_date)
        result["legs"] = from_union(
            [lambda x: from_list(lambda x: to_class(PositionLeg, x), x), from_none],
            self.legs,
        )
        result["name"] = from_str(self.name)
        result["position_entry_exits"] = from_union(
            [lambda x: to_class(PositionEntryExit, x), from_none],
            self.position_entry_exits,
        )
        result["start_date"] = from_int(self.start_date)
        result["symbol"] = from_str(self.symbol)
        return result


def position_from_dict(s: Any) -> Position:
    return Position.from_dict(s)


def position_to_dict(x: Position) -> Any:
    return to_class(Position, x)
