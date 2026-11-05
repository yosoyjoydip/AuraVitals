import type { BloodPressureAnalysis } from "../types";

export async function analyzeBloodPressure(
  waveform: number[],
  samplingRateHz: number,
): Promise<BloodPressureAnalysis> {
  const response = await fetch("/api/v1/blood-pressure/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      waveform,
      sampling_rate_hz: samplingRateHz,
    }),
  });

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof body.detail === "string"
        ? body.detail
        : `Analysis failed (${response.status})`;
    throw new Error(detail);
  }

  return response.json() as Promise<BloodPressureAnalysis>;
}
