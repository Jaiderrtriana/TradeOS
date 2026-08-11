import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Badge } from "../../../components/Badge";
import { DataTable } from "../../../components/DataTable";
import { Tabs } from "../../../components/Tabs";
import { formatInstant, usePreferencesTimezone } from "../../../shared/timezone";
import { getTradeEvaluation, getTradeEvaluationHistory } from "../api";
import { ScorePanel } from "../components/ScorePanel";
import { tradingKeys } from "../queryKeys";
import type { EvaluationHistoryEntry, EvaluationSnapshot } from "../types";

const ENGINE_LABELS: [key: keyof EvaluationSnapshot, label: string][] = [
  ["confidence", "Confidence"],
  ["quality", "Quality"],
  ["execution", "Execution"],
  ["market_context", "Market Context"],
  ["bias", "Bias"],
];

function SnapshotPanels({ snapshot }: { snapshot: EvaluationSnapshot }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {ENGINE_LABELS.map(([key, label]) => (
        <ScorePanel key={key} label={label} result={snapshot[key]} />
      ))}
    </div>
  );
}

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §5.4/§8.4 — the Rule Explorer. Current
 * tab: `GET /trades/{id}/evaluation`. History tab: `GET /trades/{id}/
 * evaluation/history`, "a Trade with no checklist answers supplied still
 * has *a* snapshot... a legitimate, displayable state, not an error" —
 * `ScorePanel` itself already renders that (empty breakdown message).
 */
export function RuleExplorerPage() {
  const { tradeId } = useParams<{ tradeId: string }>();
  const timezone = usePreferencesTimezone();
  const [selectedHistoryEntry, setSelectedHistoryEntry] = useState<EvaluationHistoryEntry | null>(
    null,
  );

  const { data: current, isLoading: isLoadingCurrent } = useQuery({
    queryKey: tradingKeys.evaluation(tradeId as string),
    queryFn: () => getTradeEvaluation(tradeId as string),
    enabled: tradeId !== undefined,
  });

  const { data: history, isLoading: isLoadingHistory } = useQuery({
    queryKey: tradingKeys.evaluationHistory(tradeId as string),
    queryFn: () => getTradeEvaluationHistory(tradeId as string),
    enabled: tradeId !== undefined,
  });

  return (
    <div className="flex flex-col gap-4 p-6">
      <nav className="text-sm text-text-secondary">
        <Link to="/trades" className="text-accent">
          Trades
        </Link>{" "}
        /{" "}
        <Link to={`/trades/${tradeId}`} className="text-accent">
          #{tradeId}
        </Link>{" "}
        / Evaluation
      </nav>

      <Tabs
        defaultValue="current"
        items={[
          {
            value: "current",
            label: "Current",
            content: isLoadingCurrent ? (
              <div className="text-sm text-text-secondary">Loading…</div>
            ) : current ? (
              <SnapshotPanels snapshot={current} />
            ) : (
              <p className="text-sm text-danger">Couldn&apos;t load the current evaluation.</p>
            ),
          },
          {
            value: "history",
            label: "History",
            content: isLoadingHistory ? (
              <div className="text-sm text-text-secondary">Loading…</div>
            ) : !history || history.length === 0 ? (
              <p className="text-sm text-text-secondary">No history yet.</p>
            ) : (
              <div className="flex flex-col gap-4">
                <DataTable<EvaluationHistoryEntry>
                  columns={[
                    {
                      key: "created_at",
                      header: "Date",
                      render: (entry) => formatInstant(entry.created_at, timezone),
                    },
                    {
                      key: "configuration_version_id",
                      header: "Configuration Version",
                      render: (entry) => entry.configuration_version_id,
                    },
                    {
                      key: "is_current",
                      header: "",
                      render: (entry) =>
                        entry.is_current ? <Badge label="Current" tone="accent" /> : null,
                    },
                    {
                      key: "confidence",
                      header: "Confidence",
                      render: (entry) => entry.confidence.grade ?? "—",
                    },
                    { key: "bias", header: "Bias", render: (entry) => entry.bias.score ?? "—" },
                  ]}
                  rows={history}
                  getRowKey={(entry) => entry.created_at}
                  onRowClick={setSelectedHistoryEntry}
                  isRowSelected={(entry) => entry === selectedHistoryEntry}
                />
                {selectedHistoryEntry && <SnapshotPanels snapshot={selectedHistoryEntry} />}
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
