"""This module contains the Unique SDK Query Language (QL) related classes and functions."""


class UQLOperator:
    """
    Unique QL operators as describe in the Unique API documentation here: https://unique-ch.atlassian.net/wiki/x/coAXHQ

    The operators can be used as follows:

    ```python
    metadata_filter = {
        "path": ['diet', '*'],
        "operator": UQLOperator.NESTED,
        "value": {
            UQLCombinator.OR : [
                {
                    UQLCombinator.OR: [
                        {
                            "path": ['food'],
                            "operator": UQLOperator.EQUALS,
                            "value": "meat",
                        },
                        {
                            "path": ['food'],
                            "operator": UQLOperator.EQUALS,
                            "value": 'vegis',
                        },
                    ],
                },
                {
                    "path": ['likes'],
                    "operator": UQLOperator.EQUALS,
                    "value": true,
                },
            ],
        },
    }
    ```
    """

    EQUALS = "equals"
    NOT_EQUALS = "notEquals"
    GREATER_THAN = "greaterThan"
    GREATER_THAN_OR_EQUAL = "greaterThanOrEqual"
    LESS_THAN = "lessThan"
    LESS_THAN_OR_EQUAL = "lessThanOrEqual"
    IN = "in"
    NOT_IN = "notIn"
    CONTAINS = "contains"
    NOT_CONTAINS = "notContains"
    IS_NULL = "isNull"
    IS_NOT_NULL = "isNotNull"
    IS_EMPTY = "isEmpty"
    IS_NOT_EMPTY = "isNotEmpty"
    NESTED = "nested"


class UQLCombinator:
    """And and Or combinators for Unique QL queries."""

    OR = "or"
    AND = "and"
