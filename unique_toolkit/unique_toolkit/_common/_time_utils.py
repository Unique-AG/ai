from datetime import datetime


def get_datetime_now(format: str = "%Y-%m-%d %H:%M:%S.%f"):
    return datetime.now().strftime(format)
