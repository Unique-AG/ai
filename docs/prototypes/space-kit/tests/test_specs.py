from pathlib import Path

import pytest

from space_kit.spec import clone_plan, load_spec

pytestmark = pytest.mark.ai

EXAMPLES = sorted(
    (Path(__file__).resolve().parent.parent / "specs" / "examples").glob("*.yaml")
)


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_example_specs_parse_into_a_clone_plan(path: Path) -> None:
    spec = load_spec(path=path)

    plan = clone_plan(spec=spec, base_dir=path.parent)

    assert plan.name == spec.name


def test_examples_exist() -> None:
    assert len(EXAMPLES) >= 3
