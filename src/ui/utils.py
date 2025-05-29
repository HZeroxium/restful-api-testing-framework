"""Common utility functions for the UI components."""


def get_summary_value(summary, key, default=0):
    """Safely get a value from summary object whether it's a dict or a Pydantic model.

    Args:
        summary: The summary object (can be a dict or a Pydantic model)
        key: The key/attribute to access
        default: Default value if key doesn't exist

    Returns:
        The value of the key/attribute or the default
    """
    if hasattr(summary, key):
        return getattr(summary, key)
    elif isinstance(summary, dict) and key in summary:
        return summary[key]
    return default
