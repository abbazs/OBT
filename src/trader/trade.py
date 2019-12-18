# To use this code, make sure you
#
#     import json
#
# and then, to convert JSON from a string, do
#
#     result = trade_from_dict(json.loads(json_string))

from dataclasses import dataclass
from typing import Optional, Any, List, TypeVar, Callable, Type, cast


T = TypeVar("T")


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
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


def from_bool(x: Any) -> bool:
    assert isinstance(x, bool)
    return x


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


@dataclass
class Position:
    ed: str
    instrument: str
    opr: int
    st: str
    symbol: str
    tt: str
    type: str
    cpr: Optional[int] = None
    index: Optional[int] = None
    nd: Optional[str] = None
    strike: Optional[int] = None

    @staticmethod
    def from_dict(obj: Any) -> 'Position':
        assert isinstance(obj, dict)
        ed = from_str(obj.get("ED"))
        instrument = from_str(obj.get("instrument"))
        opr = from_int(obj.get("OPR"))
        st = from_str(obj.get("ST"))
        symbol = from_str(obj.get("symbol"))
        tt = from_str(obj.get("TT"))
        type = from_str(obj.get("type"))
        cpr = from_union([from_int, from_none], obj.get("CPR"))
        index = from_union([from_int, from_none], obj.get("index"))
        nd = from_union([from_str, from_none], obj.get("ND"))
        strike = from_union([from_int, from_none], obj.get("strike"))
        return Position(ed, instrument, opr, st, symbol, tt, type, cpr, index, nd, strike)

    def to_dict(self) -> dict:
        result: dict = {}
        result["ED"] = from_str(self.ed)
        result["instrument"] = from_str(self.instrument)
        result["OPR"] = from_int(self.opr)
        result["ST"] = from_str(self.st)
        result["symbol"] = from_str(self.symbol)
        result["TT"] = from_str(self.tt)
        result["type"] = from_str(self.type)
        result["CPR"] = from_union([from_int, from_none], self.cpr)
        result["index"] = from_union([from_int, from_none], self.index)
        result["ND"] = from_union([from_str, from_none], self.nd)
        result["strike"] = from_union([from_int, from_none], self.strike)
        return result


@dataclass
class Trade:
    active: bool
    created_on: str
    id: int
    name: str
    pnl: int
    positions: List[Position]
    user: str

    @staticmethod
    def from_dict(obj: Any) -> 'Trade':
        assert isinstance(obj, dict)
        active = from_bool(obj.get("active"))
        created_on = from_str(obj.get("created_on"))
        id = from_int(obj.get("id"))
        name = from_str(obj.get("name"))
        pnl = from_int(obj.get("PNL"))
        positions = from_list(Position.from_dict, obj.get("positions"))
        user = from_str(obj.get("user"))
        return Trade(active, created_on, id, name, pnl, positions, user)

    def to_dict(self) -> dict:
        result: dict = {}
        result["active"] = from_bool(self.active)
        result["created_on"] = from_str(self.created_on)
        result["id"] = from_int(self.id)
        result["name"] = from_str(self.name)
        result["PNL"] = from_int(self.pnl)
        result["positions"] = from_list(lambda x: to_class(Position, x), self.positions)
        result["user"] = from_str(self.user)
        return result


def trade_from_dict(s: Any) -> Trade:
    return Trade.from_dict(s)


def trade_to_dict(x: Trade) -> Any:
    return to_class(Trade, x)
