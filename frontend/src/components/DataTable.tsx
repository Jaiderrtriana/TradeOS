import type { ReactNode } from "react";

/**
 * Shared DataTable — TRADEOS_FRONTEND_BLUEPRINT.md §7: "Render any list
 * endpoint's paginated result... Trades, Catalogs, Journal, Configuration
 * Criteria/Weights, Mistakes ranking." First consumers are Configuration's
 * two tabs (Sprint 2.3). No pagination/virtualization here — neither the
 * real `/configuration/versions`/`/catalogs` endpoints (Sprints 2.1-2.2)
 * nor TRADEOS_FRONTEND_BLUEPRINT.md §16 call for it at Catalogs/
 * Configuration's data volume; sort/filter live in each feature's own
 * query params (e.g., `?kind=`), not inside this generic shell.
 */
export interface DataTableColumn<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  isRowSelected?: (row: T) => boolean;
}

export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  onRowClick,
  isRowSelected,
}: DataTableProps<T>) {
  return (
    <table className="w-full border-collapse text-left text-sm">
      <thead>
        <tr className="border-b border-border text-text-muted">
          {columns.map((column) => (
            <th key={column.key} className="px-3 py-2 font-medium">
              {column.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const key = getRowKey(row);
          const selected = isRowSelected?.(row) ?? false;
          return (
            <tr
              key={key}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              onKeyDown={
                onRowClick
                  ? (event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        onRowClick(row);
                      }
                    }
                  : undefined
              }
              tabIndex={onRowClick ? 0 : undefined}
              aria-selected={onRowClick ? selected : undefined}
              className={`border-b border-border last:border-0 ${
                onRowClick
                  ? "cursor-pointer hover:bg-bg-overlay focus-visible:bg-bg-overlay focus-visible:outline-none"
                  : ""
              } ${selected ? "bg-bg-overlay" : ""}`}
            >
              {columns.map((column) => (
                <td key={column.key} className="px-3 py-2 text-text-primary">
                  {column.render(row)}
                </td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
