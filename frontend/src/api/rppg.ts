import type { RppgAnalysisResponse, RoiTrace } from "../types";

export async function analyzeRppg(rois: RoiTrace[]): Promise<RppgAnalysisResponse> {
  const response = await fetch("/api/v1/rppg/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rois }),
  });

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof body.detail === "string"
        ? body.detail
        : `rPPG analysis failed (${response.status})`;
    throw new Error(detail);
  }

  return response.json() as Promise<RppgAnalysisResponse>;
}

