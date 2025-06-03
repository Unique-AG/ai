from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from .compile import (
    AndStatement,
    Operator,
    OrStatement,
    SmartRuleVariables,
    Statement,
)


class MockDatetime:
    def __init__(self, fixed_time: datetime):
        self.fixed_time = fixed_time

    def now(self, tz=None):
        return self.fixed_time

    @staticmethod
    def __call__(*args, **kwargs):
        return datetime(*args, **kwargs)


@pytest.fixture
def mock_datetime():
    """Fixture to provide a mocked datetime with a fixed time."""
    fixed_time = datetime(2024, 3, 20, 12, 0, 0, tzinfo=timezone.utc)
    return MockDatetime(fixed_time)


@pytest.fixture
def variables() -> SmartRuleVariables:
    return {
        "user_metadata": {
            "age": "25",
            "name": "John",
            "isActive": "true",
            "score": "100",
        },
        "tool_parameters": {
            "threshold": "50",
            "category": "premium",
            "limit": "10",
        },
    }


def test_basic_equals_operator(variables: SmartRuleVariables):
    """Test basic equals operator with string."""
    query = Statement(
        operator=Operator.EQUALS, value="<userMetadata.name>", path=["name"]
    )
    enriched = query.with_variables(variables)
    assert isinstance(enriched, Statement)
    assert enriched.value == "John"
    assert enriched.path == ["name"]


def test_numeric_comparison(variables: SmartRuleVariables):
    """Test greater than operator with numeric values."""
    query = Statement(
        operator=Operator.GREATER_THAN,
        value="<userMetadata.score>",
        path=["score"],
    )
    enriched = query.with_variables(variables)
    assert isinstance(enriched, Statement)
    assert enriched.value == 100
    assert enriched.path == ["score"]


def test_boolean_conversion(variables: SmartRuleVariables):
    """Test boolean value conversion."""
    query = Statement(
        operator=Operator.EQUALS,
        value="<userMetadata.isActive>",
        path=["isActive"],
    )

    enriched = query.with_variables(variables)
    assert isinstance(enriched, Statement)
    assert enriched.value is True
    assert enriched.path == ["isActive"]


def test_and_statement(variables: SmartRuleVariables):
    """Test AND statement with multiple conditions."""
    query = AndStatement(
        and_list=[
            Statement(
                operator=Operator.EQUALS,
                value="<userMetadata.name>",
                path=["name"],
            ),
            Statement(
                operator=Operator.GREATER_THAN,
                value="<userMetadata.score>",
                path=["score"],
            ),
        ]
    )
    enriched = query.with_variables(variables)
    assert isinstance(enriched, AndStatement)
    assert isinstance(enriched.and_list[0], Statement)
    assert isinstance(enriched.and_list[1], Statement)
    assert enriched.and_list[0].value == "John"
    assert enriched.and_list[0].path == ["name"]
    assert enriched.and_list[1].value == 100
    assert enriched.and_list[1].path == ["score"]


def test_or_statement(variables: SmartRuleVariables):
    """Test OR statement with multiple conditions."""
    query = OrStatement(
        or_list=[
            Statement(
                operator=Operator.EQUALS,
                value="<userMetadata.name>",
                path=["name"],
            ),
            Statement(
                operator=Operator.EQUALS,
                value="<toolParameters.category>",
                path=["category"],
            ),
        ]
    )
    enriched = query.with_variables(variables)
    assert isinstance(enriched, OrStatement)
    assert isinstance(enriched.or_list[0], Statement)
    assert isinstance(enriched.or_list[1], Statement)
    assert enriched.or_list[0].value == "John"
    assert enriched.or_list[0].path == ["name"]
    assert enriched.or_list[1].value == "premium"
    assert enriched.or_list[1].path == ["category"]


def test_fallback_values(variables: SmartRuleVariables):
    """Test fallback values with ||."""
    query = Statement(
        operator=Operator.EQUALS,
        value="<userMetadata.missing>||<userMetadata.name>",
        path=["name"],
    )
    enriched = query.with_variables(variables)
    assert isinstance(enriched, Statement)
    assert enriched.value == "John"


def test_earlier_date_calculation(mock_datetime):
    """Test calculation of dates in the past."""
    with patch("_common.smart_rules.compile.datetime", mock_datetime):
        query = Statement(
            operator=Operator.GREATER_THAN_OR_EQUAL,
            value="<T-1>",  # 1 day ago
            path=["date"],
        )
        enriched = query.with_variables({})
        assert isinstance(enriched, Statement)
        expected = (mock_datetime.fixed_time - timedelta(days=1)).isoformat(
            timespec="seconds"
        )
        assert enriched.value == expected


def test_later_date_calculation(mock_datetime):
    """Test calculation of dates in the future."""
    with patch("_common.smart_rules.compile.datetime", mock_datetime):
        query = Statement(
            operator=Operator.LESS_THAN_OR_EQUAL,
            value="<T+2>",  # 2 days later
            path=["date"],
        )
        enriched = query.with_variables({})
        assert isinstance(enriched, Statement)
        expected = (mock_datetime.fixed_time + timedelta(days=2)).isoformat(
            timespec="seconds"
        )
        assert enriched.value == expected


def test_current_date_calculation(mock_datetime):
    """Test handling of current date."""
    with patch("_common.smart_rules.compile.datetime", mock_datetime):
        query = Statement(
            operator=Operator.EQUALS,
            value="<T>",  # current date
            path=["date"],
        )
        enriched = query.with_variables({})
        assert isinstance(enriched, Statement)
        expected = mock_datetime.fixed_time.isoformat(timespec="seconds")
        assert enriched.value == expected


def test_multiple_days_calculation(mock_datetime):
    """Test calculation with multiple days."""
    with patch("_common.smart_rules.compile.datetime", mock_datetime):
        query = Statement(
            operator=Operator.GREATER_THAN_OR_EQUAL,
            value="<T-7>",  # 7 days ago
            path=["date"],
        )
        enriched = query.with_variables({})
        assert isinstance(enriched, Statement)
        expected = (mock_datetime.fixed_time - timedelta(days=7)).isoformat(
            timespec="seconds"
        )
        assert enriched.value == expected


def test_nested_operators(variables: SmartRuleVariables):
    """Test nested operators."""
    query = AndStatement(
        and_list=[
            OrStatement(
                or_list=[
                    Statement(
                        operator=Operator.EQUALS,
                        value="<userMetadata.name>",
                        path=["name"],
                    ),
                    Statement(
                        operator=Operator.EQUALS,
                        value="<userMetadata.age>",
                        path=["age"],
                    ),
                ]
            ),
            Statement(
                operator=Operator.GREATER_THAN,
                value="<userMetadata.score>",
                path=["score"],
            ),
        ]
    )
    enriched = query.with_variables(variables)
    assert isinstance(enriched, AndStatement)
    assert isinstance(enriched.and_list[0], OrStatement)
    assert isinstance(enriched.and_list[1], Statement)

    or_statement = enriched.and_list[0]
    assert isinstance(or_statement.or_list[0], Statement)
    assert isinstance(or_statement.or_list[1], Statement)
    assert or_statement.or_list[0].value == "John"
    assert or_statement.or_list[1].value == 25
    assert enriched.and_list[1].value == 100


def test_tool_parameters(variables: SmartRuleVariables):
    """Test tool parameters replacement."""
    query = Statement(
        operator=Operator.EQUALS,
        value="<toolParameters.category>",
        path=["category"],
    )
    enriched = query.with_variables(variables)
    assert isinstance(enriched, Statement)
    assert enriched.value == "premium"


def test_empty_values(variables: SmartRuleVariables):
    """Test handling of empty values."""
    query = Statement(
        operator=Operator.IS_EMPTY,
        value="<userMetadata.missing>",
        path=["missing"],
    )
    enriched = query.with_variables(variables)
    assert isinstance(enriched, Statement)
    assert enriched.value == ""


def test_multiple_fallbacks(variables: SmartRuleVariables):
    """Test multiple fallback values."""
    query = Statement(
        operator=Operator.EQUALS,
        value="<userMetadata.missing>||<toolParameters.missing>||<userMetadata.name>",
        path=["name"],
    )
    enriched = query.with_variables(variables)
    assert isinstance(enriched, Statement)
    assert enriched.value == "John"


def test_plain_dict_json_robustness(variables: SmartRuleVariables):
    """Test robustness with plain dict (JSON-like) input and string operator."""
    # No location in toolParameters or userMetadata, so should fallback to 'UNKNOWN'
    rule = {
        "path": ["location"],
        "value": "<toolParameters.location>||<userMetadata.location>||UNKNOWN",
        "operator": "equals",
    }
    # Convert string operator to enum if possible
    op = rule["operator"]
    if isinstance(op, str):
        op_str = op.upper()
        if op_str in Operator.__members__:
            op = Operator[op_str]
        else:
            op = Operator.EQUALS  # fallback for test robustness
    stmt = Statement(operator=op, value=rule["value"], path=rule["path"])
    stmt = stmt.with_variables(variables)
    assert stmt.value == "UNKNOWN"
    assert stmt.path == ["location"]


def test_complex_nested_rules(variables: SmartRuleVariables):
    """Test complex nested rules with multiple levels of AND/OR statements."""
    # Create a complex nested rule structure:
    # (name == "John" OR (age > 20 AND score >= 100)) AND (category == "premium" OR isActive == true)
    query = AndStatement(
        and_list=[
            OrStatement(
                or_list=[
                    Statement(
                        operator=Operator.EQUALS,
                        value="<userMetadata.name>",
                        path=["name"],
                    ),
                    AndStatement(
                        and_list=[
                            Statement(
                                operator=Operator.GREATER_THAN,
                                value="<userMetadata.age>",
                                path=["age"],
                            ),
                            Statement(
                                operator=Operator.GREATER_THAN_OR_EQUAL,
                                value="<userMetadata.score>",
                                path=["score"],
                            ),
                        ]
                    ),
                ]
            ),
            OrStatement(
                or_list=[
                    Statement(
                        operator=Operator.EQUALS,
                        value="<toolParameters.category>",
                        path=["category"],
                    ),
                    Statement(
                        operator=Operator.EQUALS,
                        value="<userMetadata.isActive>",
                        path=["isActive"],
                    ),
                ]
            ),
        ]
    )

    enriched = query.with_variables(variables)

    # Verify the structure and values
    assert isinstance(enriched, AndStatement)
    assert len(enriched.and_list) == 2

    # Check first OR statement
    first_or = enriched.and_list[0]
    assert isinstance(first_or, OrStatement)
    assert len(first_or.or_list) == 2

    # Check name condition
    name_stmt = first_or.or_list[0]
    assert isinstance(name_stmt, Statement)
    assert name_stmt.value == "John"
    assert name_stmt.path == ["name"]

    # Check nested AND statement
    nested_and = first_or.or_list[1]
    assert isinstance(nested_and, AndStatement)
    assert len(nested_and.and_list) == 2

    age_stmt = nested_and.and_list[0]
    score_stmt = nested_and.and_list[1]
    assert isinstance(age_stmt, Statement)
    assert isinstance(score_stmt, Statement)
    assert age_stmt.value == 25  # age
    assert age_stmt.path == ["age"]
    assert score_stmt.value == 100  # score
    assert score_stmt.path == ["score"]

    # Check second OR statement
    second_or = enriched.and_list[1]
    assert isinstance(second_or, OrStatement)
    assert len(second_or.or_list) == 2

    category_stmt = second_or.or_list[0]
    is_active_stmt = second_or.or_list[1]
    assert isinstance(category_stmt, Statement)
    assert isinstance(is_active_stmt, Statement)
    assert category_stmt.value == "premium"  # category
    assert category_stmt.path == ["category"]
    assert is_active_stmt.value is True  # isActive
    assert is_active_stmt.path == ["isActive"]


def test_immutable_simple_statements():
    """Test that we can create multiple distinct filters from the same base statement."""
    # Create a base statement
    base_statement = Statement(
        operator=Operator.EQUALS, value="<userMetadata.name>", path=["name"]
    )

    # Create two different variable sets
    variables1 = {
        "user_metadata": {
            "name": "John",
        },
        "tool_parameters": {},
    }

    variables2 = {
        "user_metadata": {
            "name": "Jane",
        },
        "tool_parameters": {},
    }

    # Create two distinct filters
    filter1 = base_statement.with_variables(variables1)
    filter2 = base_statement.with_variables(variables2)

    # Verify they are distinct objects
    assert filter1 is not filter2
    assert filter1 is not base_statement
    assert filter2 is not base_statement

    # Verify they have different values
    assert filter1.value == "John"
    assert filter2.value == "Jane"

    # Verify the original statement is unchanged
    assert base_statement.value == "<userMetadata.name>"


def test_immutable_complex_statements():
    """Test that we can create multiple distinct complex filters from the same base statement."""
    # Create a more complex example with nested statements
    base_complex = AndStatement(
        and_list=[
            Statement(
                operator=Operator.EQUALS,
                value="<userMetadata.name>",
                path=["name"],
            ),
            Statement(
                operator=Operator.GREATER_THAN,
                value="<userMetadata.score>",
                path=["score"],
            ),
        ]
    )

    # Create two different variable sets for the complex statement
    complex_vars1 = {
        "user_metadata": {"name": "John", "score": "100"},
        "tool_parameters": {},
    }

    complex_vars2 = {
        "user_metadata": {"name": "Jane", "score": "200"},
        "tool_parameters": {},
    }

    # Create two distinct complex filters
    complex_filter1 = base_complex.with_variables(complex_vars1)
    complex_filter2 = base_complex.with_variables(complex_vars2)

    # Verify they are distinct objects
    assert complex_filter1 is not complex_filter2
    assert complex_filter1 is not base_complex
    assert complex_filter2 is not base_complex

    # Verify they have different values
    assert complex_filter1.and_list[0].value == "John"
    assert complex_filter1.and_list[1].value == 100
    assert complex_filter2.and_list[0].value == "Jane"
    assert complex_filter2.and_list[1].value == 200

    # Verify the original complex statement is unchanged
    assert base_complex.and_list[0].value == "<userMetadata.name>"
    assert base_complex.and_list[1].value == "<userMetadata.score>"
