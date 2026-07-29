import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../../../api/errors";
import { JournalEntriesCard } from "../../journal/components/JournalEntriesCard";
import { getTrade } from "../api";
import { ActionBar } from "../components/ActionBar";
import { EvaluationSummaryCard } from "../components/EvaluationSummaryCard";
import { MistakesCard } from "../components/MistakesCard";
import { TradeSummaryCard } from "../components/TradeSummaryCard";
import { tradingKeys } from "../queryKeys";

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §5.3/§8.3 — "the flagship page, per
 * this project's own established design history." Reached only from the
 * Trades List or Dashboard (§5.3: "no direct sidebar entry"). A `404`
 * covers both "doesn't exist" and "not yours" identically, by design
 * (`TRADEOS_API_SPECIFICATION.md` §8) — this page's Not Found state
 * covers both the same way.
 *
 * `JournalEntriesCard` lives in `features/journal/` and is imported
 * directly here (Sprint 5.1) — this page is the one place in this
 * architecture permitted to compose another feature's component
 * (`eslint.config.js`'s `page` element), since a page assembling cards
 * from multiple Bounded Contexts is exactly what this Blueprint's own
 * wireframes already call for.
 */
export function TradeDetailPage() {
  const { tradeId } = useParams<{ tradeId: string }>();

  const { data: trade, isLoading, error } = useQuery({
    queryKey: tradingKeys.detail(tradeId as string),
    queryFn: () => getTrade(tradeId as string),
    enabled: tradeId !== undefined,
    retry: false,
  });

  if (isLoading) {
    return <div className="p-6 text-sm text-text-secondary">Loading…</div>;
  }

  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className="p-6">
        <p className="text-sm text-text-secondary">
          This trade doesn&apos;t exist, or isn&apos;t yours.{" "}
          <Link to="/trades" className="text-accent">
            Back to Trades
          </Link>
        </p>
      </div>
    );
  }

  if (error || !trade) {
    return (
      <div className="p-6">
        <p role="alert" className="text-sm text-danger">
          Couldn&apos;t load this trade.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-6">
      <nav className="text-sm text-text-secondary">
        <Link to="/trades" className="text-accent">
          Trades
        </Link>{" "}
        / {trade.market}
      </nav>

      <TradeSummaryCard trade={trade} />
      <EvaluationSummaryCard tradeId={trade.id} evaluation={trade.evaluation} />
      <MistakesCard tradeId={trade.id} />
      <JournalEntriesCard tradeId={trade.id} />

      <ActionBar trade={trade} />
    </div>
  );
}
