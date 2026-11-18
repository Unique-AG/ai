DOMAIN_NAME = "language_model"
DEFAULT_COMPLETE_TIMEOUT = 240_000
DEFAULT_COMPLETE_TEMPERATURE = 0.0
DEFAULT_SEED = 42
UNSUPPORTED_SAMPLING_OPTION_KEYS = (
    "temperature",
    "top_p",
    "topP",
    "logprobs",
    "top_logprobs",
    "topLogprobs",
)
UNSUPPORTED_RESPONSES_INCLUDE = "message.output_text.logprobs"
