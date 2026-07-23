from urllib.parse import quote


def toast_url(url: str, message: str, type: str = "success") -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}toast_msg={quote(message)}&toast_type={type}"
