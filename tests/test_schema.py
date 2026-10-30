import duckdb
import pytest

from teleownermap.schema import DDL, connect


@pytest.fixture
def con():
    con = connect()
    con.execute(
        "INSERT INTO sources (source_id, source_type, retrieved_at, sha256) "
        "VALUES ('s1', 'court_opinion', now(), 'abc')"
    )
    con.execute(
        "INSERT INTO records (record_id, source_id, locator, parser_version) "
        "VALUES ('r1', 's1', 'p. 4 of 14', 'manual')"
    )
    con.execute(
        "INSERT INTO entities (entity_id, entity_type) VALUES ('a', 'company'), ('b', 'company')"
    )
    return con


def test_connect_is_idempotent(con):
    con.execute(DDL)


def test_ranged_documented_shareholding(con):
    con.execute(
        "INSERT INTO relationships (rel_id, interested_party_id, subject_entity_id, interest_type, "
        "graph, share_min, share_max, basis, assertion_status, record_id) "
        "VALUES ('e1', 'b', 'a', 'shareholding', 'equity', 0.25, 0.5, 'documented', 'stated', 'r1')"
    )
    assert con.execute("SELECT count(*) FROM relationships").fetchone()[0] == 1


@pytest.mark.parametrize(
    "values",
    [
        # share range reversed
        "('e1', 'b', 'a', 'shareholding', 'equity', 0.5, 0.25, 'documented', 'stated', 'r1')",
        # documented link without a source record
        "('e1', 'b', 'a', 'shareholding', 'equity', 0.5, 0.5, 'documented', 'stated', NULL)",
        # unknown assertion status
        "('e1', 'b', 'a', 'shareholding', 'equity', 0.5, 0.5, 'documented', 'rumored', 'r1')",
    ],
)
def test_relationship_constraints(con, values):
    with pytest.raises(duckdb.ConstraintException):
        con.execute(
            "INSERT INTO relationships (rel_id, interested_party_id, subject_entity_id, "
            "interest_type, graph, share_min, share_max, basis, assertion_status, record_id) "
            f"VALUES {values}"
        )


def test_sensitive_attribute_cannot_store_plain_value(con):
    with pytest.raises(duckdb.ConstraintException):
        con.execute(
            "INSERT INTO attributes "
            "(attribute_id, entity_id, name, value, is_sensitive, record_id) "
            "VALUES ('t1', 'a', 'residential_address', '123 Main St', TRUE, 'r1')"
        )


def test_unknown_owner_must_name_its_company(con):
    with pytest.raises(duckdb.ConstraintException):
        con.execute("INSERT INTO entities (entity_id, entity_type) VALUES ('u', 'unknown_owner')")
    con.execute(
        "INSERT INTO entities (entity_id, entity_type, unknown_owner_of) "
        "VALUES ('u', 'unknown_owner', 'a')"
    )
