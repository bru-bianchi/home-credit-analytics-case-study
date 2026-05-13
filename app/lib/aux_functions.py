""""Aux functions for the dashboard"""

def format_number(value: float | int | None) -> str:
    if value is None:
        return "-"
    elif value >= 1_000_000_000.0:
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000.0:
        return f"{value / 1_000_000:.1f}M"
    return f"{value:,.0f}"


def format_currency(value: float | int | None) -> str:
    if value is None:
        return "-"
    return "R$ " + format_number(value)


def format_percent(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2%}"