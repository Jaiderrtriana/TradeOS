import { flexRender, getCoreRowModel, useReactTable, type ColumnDef } from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useRef } from "react";

/**
 * The virtualized table base — Architecture Readiness Review (before
 * Sprint 4.4): `TRADEOS_TECHNICAL_STACK.md` §6.9 mandates TanStack Table
 * + TanStack Virtual specifically for the Trades table's confirmed
 * 20,000+ row scale (`TRADEOS_FRONTEND_BLUEPRINT.md` §16,
 * `TRADEOS_PRODUCT_BIBLE.md` NFR 10.2) — approved to build this *before*
 * Trades List, not migrate onto it afterward.
 *
 * Deliberately a *second* table component, not a replacement for the
 * existing `DataTable` (Configuration/Catalogs, Sprint 2.3): those
 * tables are small enough today that virtualization is unneeded
 * (Blueprint §16 explicitly names this as the reasoning to avoid
 * premature optimization) — reusing `VirtualizedDataTable` for them
 * would be optimizing a problem they don't have; only Trades List (the
 * first genuinely large dataset in this project) uses this component.
 *
 * Headless: `columns` fully own cell rendering (`flexRender`), matching
 * `TRADEOS_TECHNICAL_STACK.md` §6.5's Radix/Tailwind foundation — this
 * component makes no visual/color decisions of its own.
 */
export interface VirtualizedDataTableProps<T> {
  columns: ColumnDef<T, unknown>[];
  data: T[];
  getRowId: (row: T) => string;
  onRowClick?: (row: T) => void;
  /** Row height in pixels — a fixed estimate, per TanStack Virtual's own
   * fixed-size mode (the simplest correct mode for a table whose rows
   * don't vary in height, which every table in this Blueprint's scope
   * is). */
  rowHeightPx?: number;
  /** Visible viewport height in pixels for the scrolling container. */
  heightPx?: number;
  emptyState?: React.ReactNode;
}

export function VirtualizedDataTable<T>({
  columns,
  data,
  getRowId,
  onRowClick,
  rowHeightPx = 44,
  heightPx = 480,
  emptyState,
}: VirtualizedDataTableProps<T>) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => getRowId(row),
  });

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const rows = table.getRowModel().rows;

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollContainerRef.current,
    estimateSize: () => rowHeightPx,
    overscan: 10,
  });

  if (data.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  const virtualRows = virtualizer.getVirtualItems();

  return (
    <div
      ref={scrollContainerRef}
      style={{ height: heightPx, overflow: "auto" }}
      className="rounded border border-border"
    >
      <table className="w-full border-collapse text-left text-sm" role="table">
        <thead className="sticky top-0 z-10 bg-bg-surface">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className="border-b border-border text-text-muted">
              {headerGroup.headers.map((header) => (
                <th key={header.id} className="px-3 py-2 font-medium" scope="col">
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
          {virtualRows.map((virtualRow) => {
            const row = rows[virtualRow.index];
            return (
              <tr
                key={row.id}
                data-index={virtualRow.index}
                onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                onKeyDown={
                  onRowClick
                    ? (event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onRowClick(row.original);
                        }
                      }
                    : undefined
                }
                tabIndex={onRowClick ? 0 : undefined}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
                className={`border-b border-border ${
                  onRowClick
                    ? "cursor-pointer hover:bg-bg-overlay focus-visible:bg-bg-overlay focus-visible:outline-none"
                    : ""
                }`}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-2 text-text-primary">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
