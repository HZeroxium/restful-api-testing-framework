# schemas/core/pagination.py

from typing import List, Tuple, Any
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Pagination parameters for API requests."""

    limit: int = Field(
        default=50, ge=1, le=1000, description="Number of items per page"
    )
    offset: int = Field(default=0, ge=0, description="Number of items to skip")


class PaginationMetadata(BaseModel):
    """Pagination metadata for API responses."""

    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")

    @classmethod
    def create(cls, offset: int, limit: int, total_items: int) -> "PaginationMetadata":
        """
        Create pagination metadata from offset, limit, and total items.

        Args:
            offset: Number of items to skip
            limit: Number of items per page
            total_items: Total number of items

        Returns:
            PaginationMetadata instance
        """
        page = (offset // limit) + 1 if limit > 0 else 1
        total_pages = (total_items + limit - 1) // limit if limit > 0 else 1

        return cls(
            page=page,
            page_size=limit,
            total_items=total_items,
            total_pages=total_pages,
            has_next=offset + limit < total_items,
            has_previous=offset > 0,
        )
