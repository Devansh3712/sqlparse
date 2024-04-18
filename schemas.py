from dataclasses import dataclass, field
from enum import Enum


class Type(str, Enum):
    SELECT = "SELECT"
    INSERT = "INSERT INTO"
    UPDATE = "UPDATE"
    DELETE = "DELETE FROM"
    UNKNOWN = "UNKNOWN"


class Step(int, Enum):
    INIT = 0
    SELECT_FIELD = 1
    SELECT_COMMA = 2
    SELECT_FROM = 3
    SELECT_FROM_TABLE = 4
    DELETE_FROM = 5
    WHERE = 6
    WHERE_FIELD = 7
    WHERE_OPERATOR = 8
    WHERE_VALUE = 9
    WHERE_CONDITION = 10
    UPDATE = 11
    UPDATE_SET = 12
    UPDATE_FIELD = 13
    UPDATE_EQUALS = 14
    UPDATE_VALUE = 15
    UPDATE_COMMA = 16


class Operator(str, Enum):
    EQ = "="
    LT = "<"
    GT = ">"
    LTE = "<="
    GTE = ">="
    NEQ = "!="
    UNKNOWN = "UNKNOWN"


class ParserError(Exception):
    pass


@dataclass
class Condition:
    operand_1: str = field(default_factory=str)
    operand_1_is_field: bool = True
    operator: Operator = Operator.UNKNOWN
    operand_2: str = field(default_factory=str)
    operand_2_is_field: bool = True


@dataclass
class Query:
    qtype: Type = Type.UNKNOWN
    table: str = field(default_factory=str)
    fields: list[str] = field(default_factory=list)
    conditions: list[Condition] = field(default_factory=list)
    updates: dict[str, str] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
