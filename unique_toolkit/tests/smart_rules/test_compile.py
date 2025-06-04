from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from unique_toolkit.smart_rules.compile import (
    AndStatement,
    Operator,
    OrStatement,
    Statement,
    parse_uniqueql,
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
def user_metadata():
    """Fixture to provide user metadata."""
    return {
        "age": "25",
        "name": "John",
        "isActive": "true",
        "score": "100",
    }


@pytest.fixture
def tool_parameters():
    """Fixture to provide tool parameters."""
    return {
        "threshold": "50",
        "category": "premium",
        "limit": "10",
    }


def test_basic_equals_operator(user_metadata, tool_parameters):
    """Test basic equals operator with string."""
    query = Statement(
        operator=Operator.EQUALS, value="<userMetadata.name>", path=["name"]
    )
    enriched = query.with_variables(user_metadata, tool_parameters)
    assert isinstance(enriched, Statement)
    assert enriched.value == "John"
    assert enriched.path == ["name"]


def test_numeric_comparison(user_metadata, tool_parameters):
    """Test greater than operator with numeric values."""
    query = Statement(
        operator=Operator.GREATER_THAN,
        value="<userMetadata.score>",
        path=["score"],
    )
    enriched = query.with_variables(user_metadata, tool_parameters)
    assert isinstance(enriched, Statement)
    assert enriched.value == 100
    assert enriched.path == ["score"]


def test_boolean_conversion(user_metadata, tool_parameters):
    """Test boolean value conversion."""
    query = Statement(
        operator=Operator.EQUALS,
        value="<userMetadata.isActive>",
        path=["isActive"],
    )

    enriched = query.with_variables(user_metadata, tool_parameters)
    assert isinstance(enriched, Statement)
    assert enriched.value is True
    assert enriched.path == ["isActive"]


def test_and_statement(user_metadata, tool_parameters):
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
    enriched = query.with_variables(user_metadata, tool_parameters)
    assert isinstance(enriched, AndStatement)
    assert isinstance(enriched.and_list[0], Statement)
    assert isinstance(enriched.and_list[1], Statement)
    assert enriched.and_list[0].value == "John"
    assert enriched.and_list[0].path == ["name"]
    assert enriched.and_list[1].value == 100
    assert enriched.and_list[1].path == ["score"]


def test_or_statement(user_metadata, tool_parameters):
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
    enriched = query.with_variables(user_metadata, tool_parameters)
    assert isinstance(enriched, OrStatement)
    assert isinstance(enriched.or_list[0], Statement)
    assert isinstance(enriched.or_list[1], Statement)
    assert enriched.or_list[0].value == "John"
    assert enriched.or_list[0].path == ["name"]
    assert enriched.or_list[1].value == "premium"
    assert enriched.or_list[1].path == ["category"]


def test_fallback_values(user_metadata, tool_parameters):
    """Test fallback values with ||."""
    query = Statement(
        operator=Operator.EQUALS,
        value="<userMetadata.missing>||<userMetadata.name>",
        path=["name"],
    )
    enriched = query.with_variables(user_metadata, tool_parameters)
    assert isinstance(enriched, Statement)
    assert enriched.value == "John"


def test_earlier_date_calculation(mock_datetime):
    """Test calculation of dates in the past."""
    with patch("unique_toolkit.smart_rules.compile.datetime", mock_datetime):
        query = Statement(
            operator=Operator.GREATER_THAN_OR_EQUAL,
            value="<T-1>",  # 1 day ago
            path=["date"],
        )
        enriched = query.with_variables({}, {})
        assert isinstance(enriched, Statement)
        expected = (mock_datetime.fixed_time - timedelta(days=1)).isoformat(
            timespec="seconds"
        )
        assert enriched.value == expected


def test_later_date_calculation(mock_datetime):
    """Test calculation of dates in the future."""
    with patch("unique_toolkit.smart_rules.compile.datetime", mock_datetime):
        query = Statement(
            operator=Operator.LESS_THAN_OR_EQUAL,
            value="<T+2>",  # 2 days later
            path=["date"],
        )
        enriched = query.with_variables({}, {})
        assert isinstance(enriched, Statement)
        expected = (mock_datetime.fixed_time + timedelta(days=2)).isoformat(
            timespec="seconds"
        )
        assert enriched.value == expected


def test_current_date_calculation(mock_datetime):
    """Test handling of current date."""
    with patch("unique_toolkit.smart_rules.compile.datetime", mock_datetime):
        query = Statement(
            operator=Operator.EQUALS,
            value="<T>",  # current date
            path=["date"],
        )
        enriched = query.with_variables({}, {})
        assert isinstance(enriched, Statement)
        expected = mock_datetime.fixed_time.isoformat(timespec="seconds")
        assert enriched.value == expected


def test_multiple_days_calculation(mock_datetime):
    """Test calculation with multiple days."""
    with patch("unique_toolkit.smart_rules.compile.datetime", mock_datetime):
        query = Statement(
            operator=Operator.GREATER_THAN_OR_EQUAL,
            value="<T-7>",  # 7 days ago
            path=["date"],
        )
        enriched = query.with_variables({}, {})
        assert isinstance(enriched, Statement)
        expected = (mock_datetime.fixed_time - timedelta(days=7)).isoformat(
            timespec="seconds"
        )
        assert enriched.value == expected


def test_nested_operators(user_metadata, tool_parameters):
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
    enriched = query.with_variables(user_metadata, tool_parameters)
    assert isinstance(enriched, AndStatement)
    assert isinstance(enriched.and_list[0], OrStatement)
    assert isinstance(enriched.and_list[1], Statement)

    or_statement = enriched.and_list[0]
    assert isinstance(or_statement.or_list[0], Statement)
    assert isinstance(or_statement.or_list[1], Statement)
    assert or_statement.or_list[0].value == "John"
    assert or_statement.or_list[1].value == 25
    assert enriched.and_list[1].value == 100


def test_tool_parameters(user_metadata, tool_parameters):
    """Test tool parameters replacement."""
    query = Statement(
        operator=Operator.EQUALS,
        value="<toolParameters.category>",
        path=["category"],
    )
    enriched = query.with_variables(user_metadata, tool_parameters)
    assert isinstance(enriched, Statement)
    assert enriched.value == "premium"


def test_empty_values(user_metadata, tool_parameters):
    """Test handling of empty values."""
    query = Statement(
        operator=Operator.IS_EMPTY,
        value="<userMetadata.missing>",
        path=["missing"],
    )
    enriched = query.with_variables(user_metadata, tool_parameters)
    assert isinstance(enriched, Statement)
    assert enriched.value == ""


def test_multiple_fallbacks(user_metadata, tool_parameters):
    """Test multiple fallback values."""
    query = Statement(
        operator=Operator.EQUALS,
        value="<userMetadata.missing>||<toolParameters.missing>||<userMetadata.name>",
        path=["name"],
    )
    enriched = query.with_variables(user_metadata, tool_parameters)
    assert isinstance(enriched, Statement)
    assert enriched.value == "John"


def test_plain_dict_json_robustness(user_metadata, tool_parameters):
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
    stmt = stmt.with_variables(user_metadata, tool_parameters)
    assert stmt.value == "UNKNOWN"
    assert stmt.path == ["location"]


def test_complex_nested_rules(user_metadata, tool_parameters):
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

    enriched = query.with_variables(user_metadata, tool_parameters)

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
    user_metadata1 = {
        "name": "John",
    }

    user_metadata2 = {
        "name": "Jane",
    }

    # Create two distinct filters
    filter1 = base_statement.with_variables(user_metadata1, {})
    filter2 = base_statement.with_variables(user_metadata2, {})

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
    user_metadata1 = {"name": "John", "score": "100"}
    user_metadata2 = {"name": "Jane", "score": "200"}

    # Create two distinct complex filters
    complex_filter1 = base_complex.with_variables(user_metadata1, {})
    complex_filter2 = base_complex.with_variables(user_metadata2, {})

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


def test_parse_uniqueql_simple_statement():
    """Test parsing a simple statement."""
    json_data = {"operator": "equals", "value": "test", "path": ["name"]}
    result = parse_uniqueql(json_data)
    assert isinstance(result, Statement)
    assert result.operator == Operator.EQUALS
    assert result.value == "test"
    assert result.path == ["name"]


def test_parse_uniqueql_and_statement():
    """Test parsing an AND statement."""
    json_data = {
        "and": [
            {"operator": "equals", "value": "test1", "path": ["name"]},
            {"operator": "greaterThan", "value": "100", "path": ["score"]},
        ]
    }
    result = parse_uniqueql(json_data)
    assert isinstance(result, AndStatement)
    assert len(result.and_list) == 2
    assert isinstance(result.and_list[0], Statement)
    assert isinstance(result.and_list[1], Statement)
    assert result.and_list[0].operator == Operator.EQUALS
    assert result.and_list[1].operator == Operator.GREATER_THAN


def test_parse_uniqueql_or_statement():
    """Test parsing an OR statement."""
    json_data = {
        "or": [
            {"operator": "equals", "value": "test1", "path": ["name"]},
            {"operator": "equals", "value": "test2", "path": ["name"]},
        ]
    }
    result = parse_uniqueql(json_data)
    assert isinstance(result, OrStatement)
    assert len(result.or_list) == 2
    assert isinstance(result.or_list[0], Statement)
    assert isinstance(result.or_list[1], Statement)
    assert result.or_list[0].operator == Operator.EQUALS
    assert result.or_list[1].operator == Operator.EQUALS


def test_parse_uniqueql_nested_statement():
    """Test parsing a nested statement with AND and OR."""
    json_data = {
        "and": [
            {"operator": "equals", "value": "test1", "path": ["name"]},
            {
                "or": [
                    {"operator": "greaterThan", "value": "100", "path": ["score"]},
                    {"operator": "lessThan", "value": "50", "path": ["score"]},
                ]
            },
        ]
    }
    result = parse_uniqueql(json_data)
    assert isinstance(result, AndStatement)
    assert len(result.and_list) == 2
    assert isinstance(result.and_list[0], Statement)
    assert isinstance(result.and_list[1], OrStatement)
    assert result.and_list[0].operator == Operator.EQUALS
    assert len(result.and_list[1].or_list) == 2
    assert result.and_list[1].or_list[0].operator == Operator.GREATER_THAN
    assert result.and_list[1].or_list[1].operator == Operator.LESS_THAN


def test_parse_uniqueql_invalid_format():
    """Test parsing an invalid format raises ValueError."""
    json_data = {"invalid": "format"}
    with pytest.raises(ValueError, match="Invalid UniqueQL format"):
        parse_uniqueql(json_data)


def test_is_compiled_simple_statement():
    """Test is_compiled with a simple statement."""
    # Uncompiled statement with variables
    uncompiled = Statement(
        operator=Operator.EQUALS, value="<userMetadata.name>", path=["name"]
    )
    assert uncompiled.is_compiled() is True

    # Compiled statement with concrete values
    compiled = Statement(operator=Operator.EQUALS, value="John", path=["name"])
    assert compiled.is_compiled() is False


def test_is_compiled_date_variables():
    """Test is_compiled with date-related variables."""
    # Test current date variable
    current_date = Statement(operator=Operator.EQUALS, value="<T>", path=["date"])
    assert current_date.is_compiled() is True

    # Test future date variable
    future_date = Statement(operator=Operator.EQUALS, value="<T+7>", path=["date"])
    assert future_date.is_compiled() is True

    # Test past date variable
    past_date = Statement(operator=Operator.EQUALS, value="<T-7>", path=["date"])
    assert past_date.is_compiled() is True


def test_is_compiled_fallback_values():
    """Test is_compiled with fallback values."""
    # Test fallback values with variables
    fallback = Statement(
        operator=Operator.EQUALS,
        value="<userMetadata.missing>||<toolParameters.missing>||default",
        path=["name"],
    )
    assert fallback.is_compiled() is True

    # Test fallback values with concrete values
    concrete_fallback = Statement(
        operator=Operator.EQUALS, value="value1||value2||value3", path=["name"]
    )
    assert concrete_fallback.is_compiled() is False


def test_is_compiled_nested_statements():
    """Test is_compiled with nested statements."""
    # Test nested AND statement with variables
    nested_and = AndStatement(
        and_list=[
            Statement(
                operator=Operator.EQUALS, value="<userMetadata.name>", path=["name"]
            ),
            Statement(
                operator=Operator.EQUALS,
                value="<toolParameters.category>",
                path=["category"],
            ),
        ]
    )
    assert nested_and.is_compiled() is True

    # Test nested OR statement with variables
    nested_or = OrStatement(
        or_list=[
            Statement(
                operator=Operator.EQUALS, value="<userMetadata.name>", path=["name"]
            ),
            Statement(
                operator=Operator.EQUALS,
                value="<toolParameters.category>",
                path=["category"],
            ),
        ]
    )
    assert nested_or.is_compiled() is True

    # Test nested statements with concrete values
    concrete_nested = AndStatement(
        and_list=[
            Statement(operator=Operator.EQUALS, value="John", path=["name"]),
            Statement(operator=Operator.EQUALS, value="premium", path=["category"]),
        ]
    )
    assert concrete_nested.is_compiled() is False


def test_is_compiled_complex_nested():
    """Test is_compiled with complex nested statements."""
    # Create a complex nested structure with mixed compiled and uncompiled values
    complex_nested = AndStatement(
        and_list=[
            OrStatement(
                or_list=[
                    Statement(
                        operator=Operator.EQUALS,
                        value="<userMetadata.name>",  # compiled
                        path=["name"],
                    ),
                    Statement(
                        operator=Operator.EQUALS,
                        value="John",  # uncompiled
                        path=["name"],
                    ),
                ]
            ),
            Statement(
                operator=Operator.EQUALS,
                value="<toolParameters.category>",  # compiled
                path=["category"],
            ),
        ]
    )
    assert complex_nested.is_compiled() is True

    # Test with all concrete values
    concrete_complex = AndStatement(
        and_list=[
            OrStatement(
                or_list=[
                    Statement(operator=Operator.EQUALS, value="John", path=["name"]),
                    Statement(operator=Operator.EQUALS, value="Jane", path=["name"]),
                ]
            ),
            Statement(operator=Operator.EQUALS, value="premium", path=["category"]),
        ]
    )
    assert concrete_complex.is_compiled() is False


def test_round_trip_json_conversion():
    """Test round-trip conversion between JSON and objects."""
    # Original JSON with nested structure
    original_json = {
        "and": [
            {"operator": "equals", "value": "<userMetadata.name>", "path": ["name"]},
            {
                "or": [
                    {
                        "operator": "greaterThan",
                        "value": "<userMetadata.score>",
                        "path": ["score"],
                    },
                    {
                        "operator": "lessThan",
                        "value": "<toolParameters.threshold>",
                        "path": ["score"],
                    },
                ]
            },
        ]
    }

    # Parse JSON into object
    parsed_obj = parse_uniqueql(original_json)
    assert isinstance(parsed_obj, AndStatement)
    assert len(parsed_obj.and_list) == 2
    assert isinstance(parsed_obj.and_list[0], Statement)
    assert isinstance(parsed_obj.and_list[1], OrStatement)

    # Convert object back to JSON
    result_json = parsed_obj.model_dump()

    # Verify the structure is equivalent
    assert "and" in result_json
    assert len(result_json["and"]) == 2

    # Check first statement
    first_stmt = result_json["and"][0]
    assert first_stmt["operator"] == "equals"
    assert first_stmt["value"] == "<userMetadata.name>"
    assert first_stmt["path"] == ["name"]

    # Check nested OR statement
    nested_or = result_json["and"][1]
    assert "or" in nested_or
    assert len(nested_or["or"]) == 2

    # Check first OR condition
    first_or = nested_or["or"][0]
    assert first_or["operator"] == "greaterThan"
    assert first_or["value"] == "<userMetadata.score>"
    assert first_or["path"] == ["score"]

    # Check second OR condition
    second_or = nested_or["or"][1]
    assert second_or["operator"] == "lessThan"
    assert second_or["value"] == "<toolParameters.threshold>"
    assert second_or["path"] == ["score"]
