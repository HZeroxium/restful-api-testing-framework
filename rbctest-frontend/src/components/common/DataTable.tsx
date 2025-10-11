import React, { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Box,
  Typography,
  TablePagination,
  TableSortLabel,
  Checkbox,
  IconButton,
  Tooltip,
  Skeleton,
} from "@mui/material";
import type { TableColumn, SortConfig } from "@/types";

interface DataTableProps<T = any> {
  data: T[];
  columns: TableColumn<T>[];
  loading?: boolean;
  onRowClick?: (row: T, index: number) => void;
  onSort?: (sortConfig: SortConfig) => void;
  onSelectionChange?: (selectedRows: T[]) => void;
  sortConfig?: SortConfig;
  selectable?: boolean;
  page?: number;
  pageSize?: number;
  totalCount?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  actions?: Array<{
    label: string;
    icon: React.ReactNode;
    onClick: (row: T) => void;
    disabled?: (row: T) => boolean;
  }>;
  emptyMessage?: string;
}

const DataTable = <T extends Record<string, any>>({
  data,
  columns,
  loading = false,
  onRowClick,
  onSort,
  onSelectionChange,
  sortConfig,
  selectable = false,
  page = 0,
  pageSize = 10,
  totalCount = 0,
  onPageChange,
  onPageSizeChange,
  actions = [],
  emptyMessage = "No data available",
}: DataTableProps<T>) => {
  const [selectedRows, setSelectedRows] = useState<T[]>([]);

  const handleSort = (columnKey: string) => {
    if (!onSort) return;

    const newDirection =
      sortConfig?.key === columnKey && sortConfig?.direction === "asc"
        ? "desc"
        : "asc";

    onSort({ key: columnKey, direction: newDirection });
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedRows([...data]);
      onSelectionChange?.(data);
    } else {
      setSelectedRows([]);
      onSelectionChange?.([]);
    }
  };

  const handleSelectRow = (row: T, checked: boolean) => {
    let newSelectedRows;
    if (checked) {
      newSelectedRows = [...selectedRows, row];
    } else {
      newSelectedRows = selectedRows.filter((r) => r !== row);
    }
    setSelectedRows(newSelectedRows);
    onSelectionChange?.(newSelectedRows);
  };

  const isRowSelected = (row: T) => selectedRows.includes(row);

  const renderCellContent = (column: TableColumn<T>, row: T, value: any) => {
    if (column.render) {
      return column.render(value, row);
    }
    return value;
  };

  const renderLoadingSkeleton = () => (
    <>
      {Array.from({ length: pageSize }).map((_, index) => (
        <TableRow key={index}>
          {selectable && (
            <TableCell padding="checkbox">
              <Skeleton variant="rectangular" width={20} height={20} />
            </TableCell>
          )}
          {columns.map((column) => (
            <TableCell key={column.key as string}>
              <Skeleton variant="text" />
            </TableCell>
          ))}
          {actions.length > 0 && (
            <TableCell padding="none">
              <Skeleton variant="rectangular" width={40} height={40} />
            </TableCell>
          )}
        </TableRow>
      ))}
    </>
  );

  return (
    <Paper sx={{ width: "100%", overflow: "hidden" }}>
      <TableContainer>
        <Table stickyHeader>
          <TableHead>
            <TableRow>
              {selectable && (
                <TableCell padding="checkbox">
                  <Checkbox
                    indeterminate={
                      selectedRows.length > 0 &&
                      selectedRows.length < data.length
                    }
                    checked={
                      data.length > 0 && selectedRows.length === data.length
                    }
                    onChange={(e) => handleSelectAll(e.target.checked)}
                  />
                </TableCell>
              )}
              {columns.map((column) => (
                <TableCell
                  key={column.key as string}
                  align={column.align || "left"}
                  sx={{
                    fontWeight: 600,
                    backgroundColor: "grey.50",
                    minWidth: column.width || "auto",
                  }}
                >
                  {column.sortable && onSort ? (
                    <TableSortLabel
                      active={sortConfig?.key === column.key}
                      direction={
                        sortConfig?.key === column.key
                          ? sortConfig.direction
                          : "asc"
                      }
                      onClick={() => handleSort(column.key as string)}
                    >
                      {column.label}
                    </TableSortLabel>
                  ) : (
                    column.label
                  )}
                </TableCell>
              ))}
              {actions.length > 0 && (
                <TableCell
                  padding="none"
                  sx={{ fontWeight: 600, backgroundColor: "grey.50" }}
                >
                  Actions
                </TableCell>
              )}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              renderLoadingSkeleton()
            ) : data.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={
                    columns.length +
                    (selectable ? 1 : 0) +
                    (actions.length > 0 ? 1 : 0)
                  }
                  align="center"
                  sx={{ py: 4 }}
                >
                  <Typography variant="body2" color="text.secondary">
                    {emptyMessage}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              data.map((row, index) => (
                <TableRow
                  key={index}
                  hover
                  onClick={() => onRowClick?.(row, index)}
                  selected={isRowSelected(row)}
                  sx={{
                    cursor: onRowClick ? "pointer" : "default",
                    "&:hover": {
                      backgroundColor: "action.hover",
                    },
                  }}
                >
                  {selectable && (
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={isRowSelected(row)}
                        onChange={(e) => {
                          e.stopPropagation();
                          handleSelectRow(row, e.target.checked);
                        }}
                      />
                    </TableCell>
                  )}
                  {columns.map((column) => (
                    <TableCell
                      key={column.key as string}
                      align={column.align || "left"}
                      sx={{ minWidth: column.width || "auto" }}
                    >
                      {renderCellContent(column, row, row[column.key])}
                    </TableCell>
                  ))}
                  {actions.length > 0 && (
                    <TableCell padding="none">
                      <Box sx={{ display: "flex", gap: 0.5 }}>
                        {actions.map((action, actionIndex) => (
                          <Tooltip key={actionIndex} title={action.label}>
                            <IconButton
                              size="small"
                              onClick={(
                                e: React.MouseEvent<HTMLButtonElement>
                              ) => {
                                e.stopPropagation();
                                action.onClick(row);
                              }}
                              disabled={action.disabled?.(row) || false}
                            >
                              {action.icon}
                            </IconButton>
                          </Tooltip>
                        ))}
                      </Box>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      {totalCount > 0 && onPageChange && onPageSizeChange && (
        <TablePagination
          component="div"
          count={totalCount}
          page={page}
          onPageChange={(_, newPage) => onPageChange(newPage)}
          rowsPerPage={pageSize}
          onRowsPerPageChange={(e) => onPageSizeChange(Number(e.target.value))}
          rowsPerPageOptions={[5, 10, 25, 50]}
          labelRowsPerPage="Rows per page:"
          labelDisplayedRows={({ from, to, count }) =>
            `${from}-${to} of ${count !== -1 ? count : `more than ${to}`}`
          }
        />
      )}
    </Paper>
  );
};

export default DataTable;
export { DataTable };
