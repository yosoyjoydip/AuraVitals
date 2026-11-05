export interface BloodPressureAnalysis {
  signal_status: "ok" | "low_quality";
  heart_rate_bpm: number | null;
  systolic_rise_ratio: number | null;
  diastolic_fall_ratio: number | null;
  sw50_sec: number | null;
  mean_rri_ms: number | null;
  rmssd_ms: number | null;
  sdnn_ms: number | null;
  stress_index: number | null;
  stress_level: string | null;
  stress_level_ps?: string | null;
  stress_index_ms?: number | null;
  sns_zone?: number | null;
  pns_zone?: number | null;
  lf_hf_ratio?: number | null;
  systolic_mmhg: number | null;
  diastolic_mmhg: number | null;
  bp_category: string | null;
  calibration_status: "uncalibrated" | "morphology_calibrated";
  disclaimer: string;
}

export interface RoiTrace {
  label: string;
  t: number[];
  r: number[];
  g: number[];
  b: number[];
}

export interface PulseMorphology {
  systolic_rise_ratio: number | null;
  diastolic_fall_ratio: number | null;
  sw50_sec: number | null;
}

export interface HrvMetrics {
  mean_rri_ms: number | null;
  rmssd_ms: number | null;
  sdnn_ms: number | null;
  stress_index: number | null;
  stress_level: string | null;
  stress_level_ps?: string | null;
  stress_index_ms?: number | null;
  sns_zone?: number | null;
  pns_zone?: number | null;
  lf_hf_ratio?: number | null;
}

export interface BloodPressureEstimate {
  systolic_mmhg: number | null;
  diastolic_mmhg: number | null;
  category: string | null;
  calibration_status: string;
}

export interface RppgAnalysisResponse {
  status: "ok" | "low_quality" | "too_short" | "no_signal";
  heart_rate_bpm: number | null;
  hr_sqi: number;
  resp_bpm: number | null;
  resp_sqi: number;
  prq: number | null;
  stress_index: number | null;
  stress_level: string | null;
  stress_level_ps?: string | null;
  stress_index_ms?: number | null;
  sns_zone?: number | null;
  pns_zone?: number | null;
  lf_hf_ratio?: number | null;
  duration_sec: number;
  fps_effective: number;
  samples: number;
  best_roi: string | null;
  bvp: number[] | null;
  morphology: PulseMorphology | null;
  hrv: HrvMetrics | null;
  blood_pressure: BloodPressureEstimate | null;
  spo2_percent: number | null;
  spo2_r_ratio: number | null;
  calibration_status: "uncalibrated" | "morphology_calibrated";
  disclaimer: string;
}
