import json
from pathlib import Path

from humps import kebabize, pascalize
from pydantic import BaseModel


def write_module_configuration_schema(
    service_folderpath: Path,
    write_folderpath: Path,
    config: BaseModel,
    sub_name: str = "",
):
    filename_prefix = pascalize(service_folderpath.name)

    filepath = (
        write_folderpath
        / f"{filename_prefix}{f'-{sub_name}' if sub_name else ''}Schema.json"
    )

    with open(filepath, "w") as f:
        json.dump(config.model_json_schema(by_alias=True), f, indent=4)


def write_service_configuration(
    service_folderpath: Path,
    write_folderpath: Path,
    config: BaseModel,
    sub_name: str = "",
):
    filename_prefix = kebabize(service_folderpath.name)

    filepath = (
        write_folderpath
        / f"{filename_prefix}{f'-{sub_name}' if sub_name else ''}-configuration-schema.json"
    )

    with open(filepath, "w") as f:
        json.dump(config.model_json_schema(by_alias=True), f, indent=4)
    filepath = (
        write_folderpath
        / f"{filename_prefix}{f'-{sub_name}' if sub_name else ''}-default-configuration.json"
    )

    # We exclude language_model_info as it is infered from language_model_name
    with open(filepath, "w") as f:
        f.write(
            config.model_dump_json(
                by_alias=True, indent=4, exclude=set(["language_model_info"])
            )
        )
