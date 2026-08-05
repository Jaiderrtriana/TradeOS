import { apiRequest } from "../../api/client";
import type {
  AmendTradePayload,
  CloseTradePayload,
  EvaluationHistoryEntry,
  EvaluationSnapshot,
  ListTradesFilters,
  OpenTradePayload,
  PaginatedTrades,
  RegisterTradePayload,
  ReevaluateTradePayload,
  TagMistakePayload,
  Trade,
  TradeDetail,
  TradeMistake,
} from "./types";

/**
 * Trading API wrappers — TRADEOS_API_SPECIFICATION.md §6.4/§6.5, every
 * endpoint shipped through Sprints 4.1-4.4 (verified against
 * backend/app/modules/trading/presentation/router.py).
 */

export function registerTrade(payload: RegisterTradePayload): Promise<Trade> {
  return apiRequest<Trade>("/trades", { method: "POST", body: payload });
}

function buildTradesQuery(filters: ListTradesFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function listTrades(filters: ListTradesFilters = {}): Promise<PaginatedTrades> {
  return apiRequest<PaginatedTrades>(`/trades${buildTradesQuery(filters)}`);
}

export function getTrade(tradeId: string): Promise<TradeDetail> {
  return apiRequest<TradeDetail>(`/trades/${tradeId}`);
}

export function getTradeEvaluation(tradeId: string): Promise<EvaluationSnapshot> {
  return apiRequest<EvaluationSnapshot>(`/trades/${tradeId}/evaluation`);
}

export function getTradeEvaluationHistory(tradeId: string): Promise<EvaluationHistoryEntry[]> {
  return apiRequest<EvaluationHistoryEntry[]>(`/trades/${tradeId}/evaluation/history`);
}

export function amendTrade(tradeId: string, payload: AmendTradePayload): Promise<Trade> {
  return apiRequest<Trade>(`/trades/${tradeId}`, { method: "PATCH", body: payload });
}

/** `POST /trades/{id}/open` (new in v2.0) — transitions a `Planned` Trade
 * to `Open`, triggering Evaluation for the first time. */
export function openTrade(tradeId: string, payload: OpenTradePayload): Promise<Trade> {
  return apiRequest<Trade>(`/trades/${tradeId}/open`, { method: "POST", body: payload });
}

export function closeTrade(tradeId: string, payload: CloseTradePayload): Promise<Trade> {
  return apiRequest<Trade>(`/trades/${tradeId}/close`, { method: "POST", body: payload });
}

export function reevaluateTrade(
  tradeId: string,
  payload: ReevaluateTradePayload,
): Promise<EvaluationSnapshot> {
  return apiRequest<EvaluationSnapshot>(`/trades/${tradeId}/reevaluate`, {
    method: "POST",
    body: payload,
  });
}

export function deleteTrade(tradeId: string): Promise<void> {
  return apiRequest<void>(`/trades/${tradeId}`, { method: "DELETE" });
}

export function listTradeMistakes(tradeId: string): Promise<TradeMistake[]> {
  return apiRequest<TradeMistake[]>(`/trades/${tradeId}/mistakes`);
}

export function tagMistake(tradeId: string, payload: TagMistakePayload): Promise<TradeMistake> {
  return apiRequest<TradeMistake>(`/trades/${tradeId}/mistakes`, {
    method: "POST",
    body: payload,
  });
}
