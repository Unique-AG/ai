from unique_toolkit._common.pydantic_helpers import (
    model_title_generator,
)


def clean_model_title_generator(model: type) -> str:
    title = model_title_generator(model)
    return title.replace("Config", "").strip()


def experimental_model_title_generator(model: type) -> str:
    title = clean_model_title_generator(model)
    return title.replace("Config", "").strip() + " (Experimental)"
