from datetime import date, timedelta


def future_stay(days_ahead: int = 45, nights: int = 2) -> tuple[str, str]:
    check_in = date.today() + timedelta(days=days_ahead)
    check_out = check_in + timedelta(days=nights)
    return check_in.isoformat(), check_out.isoformat()
