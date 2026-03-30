from pydantic import AnyHttpUrl, ValidationError


def validate_url(url: str) -> str | None:
    """Returns error message if URL is invalid, None if valid."""
    try:
        AnyHttpUrl(url)
    except ValidationError:
        return "Invalid URL"
    return None
