import { Tabs } from "../../../components/Tabs";
import { ByDimensionTab } from "../components/ByDimensionTab";
import { OverviewTab } from "../components/OverviewTab";
import { RollingTab } from "../components/RollingTab";

/**
 * Statistics page — `TRADEOS_FRONTEND_BLUEPRINT.md` §5.6: three tabs,
 * one per confirmed endpoint (§4.2: "never a tab with no backing
 * endpoint"). Sprint 6.2.
 */
export function StatisticsPage() {
  return (
    <div className="p-6">
      <h1 className="text-lg font-semibold text-text-primary">Statistics</h1>
      <div className="mt-4">
        <Tabs
          defaultValue="overview"
          items={[
            { value: "overview", label: "Overview", content: <OverviewTab /> },
            { value: "by-dimension", label: "By Dimension", content: <ByDimensionTab /> },
            { value: "rolling", label: "Rolling", content: <RollingTab /> },
          ]}
        />
      </div>
    </div>
  );
}
