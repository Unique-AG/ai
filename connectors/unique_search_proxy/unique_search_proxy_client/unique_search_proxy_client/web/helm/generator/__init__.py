from __future__ import annotations

from pathlib import Path

from unique_search_proxy_client.web.helm.generator.schema import (
    render_additional_schema,
)
from unique_search_proxy_client.web.helm.generator.template import (
    render_providers_template,
)
from unique_search_proxy_client.web.helm.generator.values_yaml import (
    patch_values_yaml,
)
from unique_search_proxy_client.web.helm.registry import (
    HelmSettingsGroup,
    helm_generated_groups,
)


def chart_paths(chart_dir: Path) -> dict[str, Path]:
    return {
        "additional_schema": chart_dir / "values.additional.schema.json",
        "providers_tpl": chart_dir / "templates" / "_providers.tpl",
        "values_yaml": chart_dir / "values.yaml",
    }


def generated_groups_tuple() -> tuple[HelmSettingsGroup, ...]:
    return tuple(helm_generated_groups())


def generate_artifacts(chart_dir: Path) -> dict[str, str]:
    groups = generated_groups_tuple()
    paths = chart_paths(chart_dir)
    values_text = paths["values_yaml"].read_text(encoding="utf-8")

    outputs = {
        str(paths["additional_schema"]): render_additional_schema(groups),
        str(paths["providers_tpl"]): render_providers_template(groups),
        str(paths["values_yaml"]): patch_values_yaml(values_text, groups),
    }
    return outputs


def write_artifacts(chart_dir: Path) -> dict[str, Path]:
    outputs = generate_artifacts(chart_dir)
    written: dict[str, Path] = {}
    for path_str, content in outputs.items():
        path = Path(path_str)
        path.write_text(content, encoding="utf-8")
        written[path.name] = path
    return written


def check_artifacts(chart_dir: Path) -> list[str]:
    drift: list[str] = []
    outputs = generate_artifacts(chart_dir)
    for path_str, expected in outputs.items():
        path = Path(path_str)
        if not path.exists():
            drift.append(f"missing -> {path}")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            drift.append(f"drift -> {path}")
    google_tpl = chart_dir / "templates" / "_google.tpl"
    if google_tpl.exists():
        drift.append(f"stale file should be removed -> {google_tpl}")
    return drift
