"""Pytest fixtures for generator tests."""

import sys
from pathlib import Path
from typing import Any, Dict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest


@pytest.fixture
def sample_openapi_spec() -> Dict[str, Any]:
    """Sample OpenAPI specification for testing."""
    return {
        "openapi": "3.1.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/test/endpoint": {
                "get": {
                    "operationId": "findAll",
                    "parameters": [],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"},
                                            "name": {"type": "string"},
                                        },
                                        "required": ["id"],
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "operationId": "create",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                    },
                                    "required": ["name"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/TestResponse"
                                    }
                                }
                            },
                        }
                    },
                },
            },
            "/test/endpoint/{itemId}": {
                "parameters": [
                    {
                        "name": "itemId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "delete": {
                    "operationId": "deleteItem",
                    "responses": {"204": {"description": "No content"}},
                },
            },
        },
        "components": {
            "schemas": {
                "TestResponse": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                    "required": ["id", "name"],
                }
            }
        },
    }


@pytest.fixture
def template_dir(tmp_path: Path) -> Path:
    """Create temporary template directory with mock templates."""
    templates = tmp_path / "templates"
    templates.mkdir()

    # Create minimal mock templates
    (templates / "operation_template.jinja2").write_text(
        "# Operation for {{ path }}\n{% for model in models %}{{ model }}\n{% endfor %}\n{% for op in operations %}{{ op.name }}\n{% endfor %}"
    )

    (templates / "endpoint_init_template.jinja2").write_text(
        "from .operation import {% for op in operations %}{{ op }}{% if not loop.last %}, {% endif %}{% endfor %}\n__all__ = {{ exports }}"
    )

    (templates / "parent_init_template.jinja2").write_text(
        "{% for subdir in subdirs %}from . import {{ subdir }}\n{% endfor %}__all__ = {{ subdirs }}"
    )

    (templates / "components.py.jinja2").write_text(
        "# Components\n{% for model in models %}{{ model }}\n{% endfor %}"
    )

    return templates
