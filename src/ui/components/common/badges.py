"""Badge components for the API Testing Platform."""


def render_method_badge(method):
    """Render an HTML badge for HTTP methods.

    Args:
        method: The HTTP method (GET, POST, etc.)

    Returns:
        HTML string for the method badge
    """
    method = method.lower()
    return f"""<span class="method-badge {method}-badge">{method.upper()}</span>"""


def render_status_badge(status):
    """Render an HTML badge for test status.

    Args:
        status: The test status (pass, fail, etc.)

    Returns:
        HTML string for the status badge
    """
    status_lower = status.lower()
    return (
        f"""<span class="status-badge status-{status_lower}">{status.upper()}</span>"""
    )


def render_tag(tag):
    """Render an HTML tag.

    Args:
        tag: The tag text

    Returns:
        HTML string for the tag
    """
    return f"""<span class="tag">{tag}</span>"""
