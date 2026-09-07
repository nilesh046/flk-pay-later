from datetime import datetime, date


def parse_date(value):
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%d-%b-%Y").date()
        except ValueError:
            return datetime.strptime(value, "%Y-%m-%d").date()
    raise ValueError(f"Unsupported date format: {value}")
