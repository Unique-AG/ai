from pathlib import Path

import yaml

from core.malicious.schema import ThreatSkillDefinition, ThreatSkillType

_THREATS_DIR = Path(__file__).parent


def load_threats(
    enabled: list[ThreatSkillType] | None = None,
) -> list[ThreatSkillDefinition]:
    """Load predefined threat skills from YAML files.

    If enabled is None, loads all predefined threats.
    Otherwise loads only the specified enum values.
    """
    types_to_load = enabled if enabled is not None else list(ThreatSkillType)
    results: list[ThreatSkillDefinition] = []
    for threat_type in types_to_load:
        yaml_path = _THREATS_DIR / f"{threat_type.value}.yaml"
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        results.append(ThreatSkillDefinition(**data))
    return results


def load_benign_skill() -> ThreatSkillDefinition:
    """Load the benign (non-threatening) content generation skill."""
    yaml_path = _THREATS_DIR / "_benign.yaml"
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    return ThreatSkillDefinition(**data)
