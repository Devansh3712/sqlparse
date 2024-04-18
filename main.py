import re
from dataclasses import dataclass, field
from pprint import pprint

from schemas import *

stop_words = (
    "(",
    ")",
    ",",
    ">",
    "<",
    "=",
    ">=",
    "<=",
    "!=",
    "SELECT",
    "UPDATE",
    "DELETE FROM",
    "INSERT INTO",
    "FROM",
    "SET",
    "WHERE",
    "AS",
)


@dataclass
class Parser:
    sql: str
    query: Query = field(default_factory=Query)
    index: int = 0
    step: Step = Step.INIT

    def __post_init__(self):
        self.length = len(self.sql)

    def parse(self) -> Query:
        while True:
            if self.index >= self.length:
                return self.query

            match self.step:
                case Step.INIT:
                    query = self.peek()
                    match query:
                        case "SELECT":
                            self.query.qtype = Type.SELECT
                            self.step = Step.SELECT_FIELD
                        case "INSERT INTO":
                            self.query.qtype = Type.INSERT
                        case "UPDATE":
                            self.query.qtype = Type.UPDATE
                        case "DELETE FROM":
                            self.query.qtype = Type.DELETE
                            self.step = Step.DELETE_FROM
                        case _:
                            raise ParserError(f"invalid query type '{query}'")
                    self.pop()

                case Step.SELECT_FIELD:
                    identifier = self.peek()
                    if not self.is_identifier_or_asterisk(identifier):
                        raise ParserError(
                            f"at SELECT: expected a field, found '{identifier}'"
                        )
                    self.query.fields.append(identifier)
                    self.pop()
                    # Check if "AS" is used to create an alias for an attribute
                    if (peeked := self.peek().upper()) == "AS":
                        self.pop()
                        alias = self.peek()
                        if not self.is_identifier(alias):
                            raise ParserError(
                                f"at SELECT: expected field alias for '{identifier}', found '{alias}'"
                            )
                        self.query.aliases[identifier] = alias
                        self.pop()
                    if self.peek().upper() == "FROM":
                        self.step = Step.SELECT_FROM
                        continue
                    self.step = Step.SELECT_COMMA

                case Step.SELECT_COMMA:
                    if (peeked := self.peek()) != ",":
                        raise ParserError(
                            f"at SELECT: expected a comma, found '{peeked}'"
                        )
                    self.pop()
                    self.step = Step.SELECT_FIELD

                case Step.SELECT_FROM:
                    if (peeked := self.peek().upper()) != "FROM":
                        raise ParserError(f"at SELECT: expected FROM, found '{peeked}'")
                    self.pop()
                    self.step = Step.SELECT_FROM_TABLE

                case Step.SELECT_FROM_TABLE:
                    table_name = self.peek()
                    if not table_name:
                        raise ParserError("at SELECT: expected a table name")
                    self.query.table = table_name
                    self.pop()
                    self.step = Step.WHERE

                case Step.DELETE_FROM:
                    table_name = self.peek()
                    if not table_name:
                        raise ParserError("at DELETE: expected a table name")
                    self.query.table = table_name
                    self.pop()
                    self.step = Step.WHERE

                case Step.WHERE:
                    if (peeked := self.peek().upper()) != "WHERE":
                        raise ParserError("expected a WHERE clause")
                    self.pop()
                    self.step = Step.WHERE_FIELD

                case Step.WHERE_FIELD:
                    identifier = self.peek()
                    if not self.is_identifier(identifier):
                        raise ParserError(
                            f"at WHERE: expected a field, found '{identifier}'"
                        )
                    self.query.conditions.append(Condition(operand_1=identifier))
                    self.pop()
                    self.step = Step.WHERE_OPERATOR

                case Step.WHERE_OPERATOR:
                    operator = self.peek()
                    condition = self.query.conditions[-1]
                    match operator:
                        case "=":
                            condition.operator = Operator.EQ
                        case "<":
                            condition.operator = Operator.LT
                        case ">":
                            condition.operator = Operator.GT
                        case "<=":
                            condition.operator = Operator.LTE
                        case ">=":
                            condition.operator = Operator.GTE
                        case "!=":
                            condition.operator = Operator.NEQ
                        case _:
                            raise ParserError(
                                f"at WHERE: expected an operator, found '{operator}'"
                            )
                    self.pop()
                    self.step = Step.WHERE_VALUE

                case Step.WHERE_VALUE:
                    condition = self.query.conditions[-1]
                    identifier = self.peek()
                    if self.is_identifier(identifier):
                        condition.operand_2 = identifier
                    else:
                        quoted, length = self.peek_quoted()
                        if not length:
                            raise ParserError("at WHERE: expected a quoted value")
                        condition.operand_2 = quoted
                        condition.operand_2_is_field = False
                    self.pop()
                    self.step = Step.WHERE_CONDITION

                case Step.WHERE_CONDITION:
                    if (peeked := self.peek().upper()) not in ["AND", "OR"]:
                        raise ParserError(
                            f"at WHERE: expected AND/OR, found '{peeked}'"
                        )
                    self.pop()
                    self.step = Step.WHERE_FIELD

    def peek(self) -> str:
        peeked, _ = self._peek()
        return peeked

    def pop(self) -> str:
        peeked, length = self._peek()
        self.index += length
        while self.index < self.length and self.sql[self.index] == " ":
            self.index += 1
        return peeked

    def _peek(self) -> tuple[str, int]:
        if self.index > self.length:
            return str(), 0
        for word in stop_words:
            token = self.sql[self.index : min(self.length, self.index + len(word))]
            if token.upper() == word:
                return word, len(token)
        if self.sql[self.index] == "'":
            return self.peek_quoted()
        return self._peek_identifier()

    def _peek_identifier(self) -> tuple[str, int]:
        for i in range(self.index, self.length):
            regexp = re.compile("[a-zA-Z0-9_*]")
            match = regexp.match(self.sql[i])
            if match is None:
                token = self.sql[self.index : i]
                return token, len(token)
        token = self.sql[self.index :]
        return token, len(token)

    def peek_quoted(self) -> tuple[str, int]:
        if self.index > self.length or self.sql[self.index] != "'":
            return str(), 0
        for i in range(self.index + 1, self.length):
            if self.sql[i] == "'" and self.sql[i - 1] != "\\":
                token = self.sql[self.index + 1 : i]
                return token, len(token) + 2
        return str(), 0

    def is_identifier(self, s: str) -> bool:
        for word in stop_words:
            if s.upper() == word:
                return False
        regexp = re.compile("[a-zA-Z0-9_*]")
        return regexp.match(s) is not None

    def is_identifier_or_asterisk(self, s: str) -> bool:
        return self.is_identifier(s) or s == "*"


if __name__ == "__main__":
    query = Parser(
        sql="SELECT fname AS first_name, lname AS last_name FROM data WHERE age > 20 AND location= 'Delhi'"
    )
    result = query.parse()
    pprint(result)
