# utils/pagination_utils.py

from typing import List, Tuple, Any
from schemas.core.pagination import PaginationMetadata


def calculate_pagination_metadata(
    offset: int, limit: int, total_items: int
) -> PaginationMetadata:
    """
    Calculate pagination metadata from offset, limit, and total items.

    Args:
        offset: Number of items to skip
        limit: Number of items per page
        total_items: Total number of items

    Returns:
        PaginationMetadata instance
    """
    return PaginationMetadata.create(offset, limit, total_items)


def paginate_list(items: List[Any], offset: int, limit: int) -> Tuple[List[Any], int]:
    """
    Paginate a list of items in memory.

    Args:
        items: List of items to paginate
        offset: Number of items to skip
        limit: Number of items to return

    Returns:
        Tuple of (paginated_items, total_count)
    """
    total_count = len(items)

    # Apply pagination
    start_index = offset
    end_index = offset + limit

    paginated_items = items[start_index:end_index]

    return paginated_items, total_count


def validate_pagination_params(limit: int, offset: int) -> None:
    """
    Validate pagination parameters and raise ValueError if invalid.

    Args:
        limit: Number of items per page
        offset: Number of items to skip

    Raises:
        ValueError: If parameters are invalid
    """
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if limit > 1000:
        raise ValueError("limit must be <= 1000")
    if offset < 0:
        raise ValueError("offset must be >= 0")
