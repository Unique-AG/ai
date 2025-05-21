import datetime
from pydantic import BaseModel, Field, create_model
from unique_toolkit.language_model import (
    LanguageModelToolDescription,
)

"""
# `LanguageModelToolDescription` usage

`LanguageModelToolDescription` is the preferred way to use tool with the toolkit services (ChatService and LanguageModelService).

`LanguageModelTool` is deprecated in favor of `LanguageModelToolDescription` for two reasons; the latter allows:
- Parameters to be passed as a pydantic model. This is simpler and directly opens more possibilities than the previous approach.
- Using "strict" tool calling, in which case it is guaranteed that the model always will always follow the input schema above.
"""


# Simple case
class WeatherParameters(BaseModel):
    city: str = Field(description="description")


tool_description = LanguageModelToolDescription(
    name="get_weather",
    description="Get the weather for a given city",
    parameters=WeatherParameters,
)

# Strict case
"""
Using strict tool calling add the following constraints:
- All BaseModel in the input must not allow `additionalProperties`
- All fields must be required
"""


class TimeSpecificationStrict(BaseModel):
    model_config = {"extra": "forbid"}
    time: datetime.datetime
    timezone: datetime.timezone


class WeatherParametersStrict(BaseModel):
    model_config = {"extra": "forbid"}
    city: str = Field(description="description")
    time_specification: TimeSpecificationStrict


tool_description_strict = LanguageModelToolDescription(
    name="get_weather",
    description="Get the weather for a given city",
    parameters=WeatherParametersStrict,
    strict=True,
)


# Dynamically defining tool descriptions
"""
Often we would like the tool parameter descriptions to be configurable.
This can be achieved by either:
- Defining the tool parameters inside the config scope
- Using pydantic's `create_model` to create the model dynamically
"""


## Defining the tool parameters inside the config scope
class WeatherTool:
    def __init__(self, config):
        self.config = config

    def tool_description(self) -> LanguageModelToolDescription:
        class WeatherParameters(BaseModel):
            city: str = Field(description=self.config.param_city_description)

        return LanguageModelToolDescription(
            name="my_tool",
            description="My tool description",
            parameters=WeatherParameters,
        )


## Using pydantic's `create_model` to create the model dynamically
class WeatherToolDynamic:
    def __init__(self, config):
        self.config = config

    def tool_description(self) -> LanguageModelToolDescription:
        WeatherParameters = create_model(
            "WeatherParameters",
            city=Field(description=self.config.param_city_description),
            __config__={"extra": "forbid"},  # Optional
        )

        return LanguageModelToolDescription(
            name="my_tool",
            description="My tool description",
            parameters=WeatherParameters,
        )
