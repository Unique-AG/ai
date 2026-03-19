from urllib.parse import urlparse

from unique_toolkit._common.pydantic_helpers import (
    model_title_generator,
)


def clean_model_title_generator(model: type) -> str:
    title = model_title_generator(model)
    return title.replace("Config", "").strip()


def experimental_model_title_generator(model: type) -> str:
    title = clean_model_title_generator(model)
    return title.replace("Config", "").strip() + " (Experimental)"


def beta_model_title_generator(model: type) -> str:
    title = clean_model_title_generator(model)
    return title.replace("Config", "").strip() + " (Beta)"


def extract_root_domain(url: str) -> str:
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    domain = domain.split(":")[0]
    domain = domain.replace("www.", "")
    return domain


COMMON_SECOND_LEVEL_SUFFIXES = {
    "ac.uk",
    "co.in",
    "co.jp",
    "co.uk",
    "com.au",
    "com.br",
    "com.cn",
    "com.mx",
    "com.tr",
    "com.tw",
    "gov.uk",
    "net.au",
    "org.au",
    "org.uk",
}


def extract_registered_domain(url: str) -> str:
    """Best-effort registrable-domain extraction for diversity grouping.

    This intentionally avoids adding a new dependency. It is highly reliable for
    common domains like `example.com` and for common second-level public suffixes
    such as `co.uk`, while remaining a heuristic for more exotic suffixes.
    """

    domain = extract_root_domain(url)
    parts = domain.split(".")
    if len(parts) <= 2:
        return domain

    last_two = ".".join(parts[-2:])
    if last_two in COMMON_SECOND_LEVEL_SUFFIXES and len(parts) >= 3:
        return ".".join(parts[-3:])

    if len(parts[-1]) == 2 and parts[-2] in {
        "ac",
        "co",
        "com",
        "edu",
        "gov",
        "net",
        "org",
    }:
        return ".".join(parts[-3:])

    return ".".join(parts[-2:])
