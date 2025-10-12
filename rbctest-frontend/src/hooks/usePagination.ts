import { useState, useCallback } from "react";

interface UsePaginationProps {
  defaultPageSize?: number;
  onPageChange?: (offset: number, limit: number) => void;
}

export const usePagination = ({
  defaultPageSize = 10,
  onPageChange,
}: UsePaginationProps = {}) => {
  const [page, setPage] = useState(0); // MUI uses 0-based page
  const [pageSize, setPageSize] = useState(defaultPageSize);

  const offset = page * pageSize;
  const limit = pageSize;

  const handlePageChange = useCallback(
    (_: unknown, newPage: number) => {
      setPage(newPage);
      const newOffset = newPage * pageSize;
      onPageChange?.(newOffset, pageSize);
    },
    [pageSize, onPageChange]
  );

  const handlePageSizeChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const newPageSize = parseInt(event.target.value, 10);
      setPageSize(newPageSize);
      setPage(0); // Reset to first page
      onPageChange?.(0, newPageSize);
    },
    [onPageChange]
  );

  const resetPagination = useCallback(() => {
    setPage(0);
  }, []);

  return {
    page,
    pageSize,
    offset,
    limit,
    handlePageChange,
    handlePageSizeChange,
    resetPagination,
  };
};
