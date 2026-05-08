import type { ManagerNoteResponse } from "@/lib/api/planning";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const V1 = `${API_URL}/api/v1`;

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export type CouncilSource =
  | "lightgbm"
  | "optimizer"
  | "rules_based"
  | "llm_rephrased"
  | "judge_synthesized"
  | "fallback"
  | "manager_note";

export interface CandidateQuantity {
  quantity: number;
  source:
    | "expected_demand"
    | "optimizer"
    | "current_plan"
    | "stockout_guardrail"
    | "waste_guardrail"
    | "manager_note_adjusted";
  reason: string;
  evidence: Record<string, unknown>;
  alternate_sources?: string[];
}

export interface AgentTraceItem {
  agent: string;
  role: string;
  claim: string;
  stance?: string | null;
  severity: "info" | "low" | "medium" | "high" | "critical";
  source: CouncilSource;
  evidence: Record<string, unknown>;
}

export interface AgentArgument {
  agent: string;
  stance:
    | "increase_prep"
    | "decrease_prep"
    | "hold"
    | "reorder"
    | "caution"
    | "evidence"
    | "manager_context";
  claim: string;
  evidence: Record<string, unknown>;
  suggested_candidate_source?: string | null;
  severity: "info" | "low" | "medium" | "high" | "critical";
  source: CouncilSource;
}

export interface JudgeRecommendation {
  recommended_prep: number;
  selected_candidate_source: string;
  requires_confirmation: boolean;
  reasoning_summary: string;
  primary_conflict?: string | null;
  agent_consensus: "aligned" | "split" | "contested";
  source: "judge_synthesized" | "fallback";
}

export interface CouncilReviewResponse {
  recommendation_id: string;
  plan_id?: number | null;
  outlet_name: string;
  sku_name: string;
  daypart: string;
  current_recommended_prep: number;
  candidate_quantities: CandidateQuantity[];
  agent_arguments: AgentArgument[];
  agent_trace: AgentTraceItem[];
  judge_recommendation: JudgeRecommendation;
  graph_trace: Record<string, unknown>[];
  source_type: "agent_council";
}

export interface CouncilReviewWithNoteResponse {
  before_review: CouncilReviewResponse;
  after_review: CouncilReviewResponse;
  source_type: "agent_council";
}

export interface CouncilConfirmResponse {
  forecast_run_id: string;
  status: "applied";
  message: string;
  application_mode: "prep_edit_only";
  selected_candidate_source: string;
  audit_event_ids: number[];
  replenishment_plan_id: number | null;
  warnings?: string[];
  line_changes: {
    line_id: number;
    outlet_name: string;
    sku_name: string;
    daypart: string;
    before_prep: number;
    after_prep: number;
  }[];
  council_review: CouncilReviewResponse;
}

export const agenticApi = {
  reviewCouncil: (
    recommendationId: string,
    language: "en" | "ms" | "zh-CN" = "en"
  ): Promise<CouncilReviewResponse> =>
    apiFetch(`${V1}/copilot/council/review`, {
      method: "POST",
      body: JSON.stringify({ recommendation_id: recommendationId, language }),
    }),

  reviewCouncilWithNote: (
    recommendationId: string,
    parsedAdjustment: ManagerNoteResponse["parsed_adjustment"],
    originalNote?: string,
    language: "en" | "ms" | "zh-CN" = "en"
  ): Promise<CouncilReviewWithNoteResponse> =>
    apiFetch(`${V1}/copilot/council/review-with-note`, {
      method: "POST",
      body: JSON.stringify({
        recommendation_id: recommendationId,
        parsed_adjustment: parsedAdjustment,
        original_note: originalNote,
        language,
      }),
    }),

  confirmCouncilRecommendation: (
    payload: {
      recommendation_id: string;
      selected_prep: number;
      manager_adjustment?: ManagerNoteResponse["parsed_adjustment"];
      operator_reason: string;
      language?: "en" | "ms" | "zh-CN";
    }
  ): Promise<CouncilConfirmResponse> =>
    apiFetch(`${V1}/copilot/council/confirm`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

