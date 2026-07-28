import { render, screen } from "@testing-library/react";
import type { ColumnDef } from "@tanstack/react-table";
import { describe, expect, it } from "vitest";

import { VirtualizedDataTable } from "./VirtualizedDataTable";

/**
 * Component-tier scope, deliberately: structure and configuration only
 * (headers render per column, the empty state replaces the table when
 * `data` is empty). Row virtualization itself depends on real browser
 * layout (`getBoundingClientRect`/`ResizeObserver` reporting an actual
 * viewport size) that jsdom does not provide -- verifying that a
 * virtualized row actually renders and responds to a click belongs at
 * the E2E tier (Playwright, a real browser), exercised once Trades List
 * (Sprint 4.4) renders this component against real data, not faked here
 * with jsdom layout stubs that would only prove the stub works.
 */
interface Row {
  id: string;
  label: string;
}

const columns: ColumnDef<Row, unknown>[] = [{ id: "label", header: "Label", accessorKey: "label" }];

describe("VirtualizedDataTable", () => {
  it("renders a header per column", () => {
    render(
      <VirtualizedDataTable
        columns={columns}
        data={[{ id: "1", label: "First" }]}
        getRowId={(row) => row.id}
      />,
    );
    expect(screen.getByRole("columnheader", { name: "Label" })).toBeInTheDocument();
  });

  it("renders the empty state when there are no rows", () => {
    render(
      <VirtualizedDataTable
        columns={columns}
        data={[]}
        getRowId={(row) => row.id}
        emptyState={<p>Nothing here yet</p>}
      />,
    );
    expect(screen.getByText("Nothing here yet")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
