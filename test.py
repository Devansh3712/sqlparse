from schemas import Type
from sqlparse import Parser


def test_select_asterisk():
    query = Parser(sql="SELECT * FROM users")
    result = query.parse()

    assert result.qtype == Type.SELECT
    assert result.fields == ["*"]
    assert result.table == "users"

def test_delete():
    query = Parser(sql="DELETE FROM users WHERE id = 1")
    result = query.parse()

    assert result.qtype == Type.DELETE
    assert result.table == "users"


def test_update_single_field():
    query = Parser(sql="UPDATE users SET name = 'devansh' WHERE id = 1")
    result = query.parse()

    assert result.qtype == Type.UPDATE
    assert result.updates == {"name": "devansh"}
    assert result.table == "users"