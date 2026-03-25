import random

from fake_useragent import UserAgent

FIRST_NAMES = [
    "james",
    "mary",
    "robert",
    "patricia",
    "john",
    "jennifer",
    "michael",
    "linda",
    "david",
    "elizabeth",
    "william",
    "barbara",
    "richard",
    "susan",
    "joseph",
    "jessica",
    "thomas",
    "sarah",
    "christopher",
    "karen",
    "charles",
    "lisa",
    "daniel",
    "nancy",
    "matthew",
    "betty",
    "anthony",
    "margaret",
    "mark",
    "sandra",
    "donald",
    "ashley",
    "steven",
    "dorothy",
    "paul",
    "kimberly",
    "andrew",
    "emily",
    "joshua",
    "donna",
]

LAST_NAMES = [
    "smith",
    "johnson",
    "williams",
    "brown",
    "jones",
    "garcia",
    "miller",
    "davis",
    "rodriguez",
    "martinez",
    "hernandez",
    "lopez",
    "gonzalez",
    "wilson",
    "anderson",
    "thomas",
    "taylor",
    "moore",
    "jackson",
    "martin",
    "lee",
    "perez",
    "thompson",
    "white",
    "harris",
    "sanchez",
    "clark",
    "ramirez",
    "lewis",
    "robinson",
    "walker",
    "young",
    "allen",
    "king",
    "wright",
    "scott",
    "torres",
    "nguyen",
    "hill",
    "flores",
]

EMAIL_DOMAINS = [
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "protonmail.com",
    "aol.com",
    "mail.com",
    "zoho.com",
    "fastmail.com",
    "yandex.com",
    "gmx.com",
    "tutanota.com",
    "live.com",
    "msn.com",
]

SEPARATORS = [".", "_", ""]


def generate_random_email() -> str:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    sep = random.choice(SEPARATORS)
    domain = random.choice(EMAIL_DOMAINS)
    suffix = random.randint(1, 999) if random.random() < 0.5 else ""
    return f"{first}{sep}{last}{suffix}@{domain}"


def get_random_user_agent() -> str:
    random_chrome = UserAgent().chrome
    random_email = generate_random_email()

    return random_chrome + f"({random_email})"
