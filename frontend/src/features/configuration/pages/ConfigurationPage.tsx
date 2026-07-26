import { Tabs } from "../../../components/Tabs";
import { CatalogsManagementTab } from "../components/CatalogsManagementTab";
import { ScoringVersionsTab } from "../components/ScoringVersionsTab";

/**
 * TRADEOS_FRONTEND_BLUEPRINT.md §4.1/§4.2: one sidebar entry
 * ("Configuration: Scoring & Catalogs"), one route (`/configuration`),
 * two tabs — mirroring exactly how Statistics (Overview/By Dimension/
 * Rolling) is specified. Sprint 2.3 replaces Sprint 0.3's placeholder.
 */
export function ConfigurationPage() {
  return (
    <div className="p-6">
      <Tabs
        defaultValue="scoring-versions"
        items={[
          { value: "scoring-versions", label: "Scoring Versions", content: <ScoringVersionsTab /> },
          { value: "catalogs", label: "Catalogs Management", content: <CatalogsManagementTab /> },
        ]}
      />
    </div>
  );
}
