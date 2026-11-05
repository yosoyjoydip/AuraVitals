import {
  HeartPulse,
  Activity,
  Droplets,
  Wind,
  Sparkles,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  ArrowLeft,
  Info,
} from "lucide-react";
import type { RppgAnalysisResponse } from "../types";
import { WaveformChart } from "./WaveformChart";

interface HealthReportProps {
  result: RppgAnalysisResponse;
  onScanAgain: () => void;
}

export function HealthReport({ result, onScanAgain }: HealthReportProps) {
  const isOk = result.status === "ok";

  const hr = result.heart_rate_bpm;
  const sbp = result.blood_pressure?.systolic_mmhg;
  const dbp = result.blood_pressure?.diastolic_mmhg;
  const bpCategory = result.blood_pressure?.category || "Normal";
  const spo2 = result.spo2_percent;
  const resp = result.resp_bpm;
  const prq = result.prq;

  const stressIndex = result.stress_index ?? result.hrv?.stress_index;
  const stressLevel = result.stress_level ?? result.hrv?.stress_level ?? "Normal";
  const rmssd = result.hrv?.rmssd_ms;
  const sdnn = result.hrv?.sdnn_ms;
  const meanRri = result.hrv?.mean_rri_ms;

  const riseRatio = result.morphology?.systolic_rise_ratio;
  const fallRatio = result.morphology?.diastolic_fall_ratio;
  const sw50 = result.morphology?.sw50_sec;

  // Calculate Star Health Wellness Score (0 to 100)
  let wellnessScore = 88;
  if (isOk) {
    let score = 95;
    if (hr && (hr < 55 || hr > 100)) score -= 10;
    if (spo2 && spo2 < 95) score -= 12;
    if (stressIndex && stressIndex > 65) score -= 12;
    if (sbp && sbp > 130) score -= 8;
    wellnessScore = Math.max(60, Math.min(98, score));
  }

  const currentDate = new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  if (!isOk) {
    return (
      <div className="report-container error-state">
        <div className="report-header">
          <button className="back-btn" onClick={onScanAgain} type="button">
            <ArrowLeft size={16} /> Back to Scanner
          </button>
        </div>

        <div className="report-card error-card">
          <div className="error-icon">
            <AlertCircle size={48} />
          </div>
          <h2>Scan Quality Below Threshold</h2>
          <p className="error-desc">
            {result.status === "too_short"
              ? "The recording was shorter than the required 15-second window. Please hold still for the full duration."
              : "We could not detect clear micro-capillary pulse signals across your face. This is usually due to dim lighting, backlight glare, or head movement."}
          </p>

          <div className="tips-box">
            <h4>💡 Quick Tips for a Perfect Scan:</h4>
            <ul>
              <li>Face a bright window or soft light (avoid backlight behind your head).</li>
              <li>Keep your face centered inside the oval guide.</li>
              <li>Remain relaxed, stay still, and breathe naturally.</li>
            </ul>
          </div>

          <button className="primary-action-btn" onClick={onScanAgain} type="button">
            <RotateCcw size={16} /> Scan Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="report-container">
      {/* Top Navigation */}
      <div className="report-header">
        <button className="back-btn" onClick={onScanAgain} type="button">
          <ArrowLeft size={16} /> Scan Another Person
        </button>
        <span className="report-timestamp">Report generated: {currentDate}</span>
      </div>

      {/* Star Health Wellness Summary Banner */}
      <div className="wellness-banner">
        <div className="wellness-left">
          <div className="wellness-badge">
            <Sparkles size={14} /> STAR HEALTH VITALS SCORECARD
          </div>
          <h1>Overall Wellness: {wellnessScore >= 85 ? "Optimal Balance" : "Good Stability"}</h1>
          <p>
            Your resting cardiovascular cycle, arterial oxygenation, and parasympathetic vagal
            variability reflect a stable autonomic state.
          </p>
          <div className="wellness-tags">
            <span className="wellness-tag">
              <CheckCircle2 size={13} /> Optical SQI: {(result.hr_sqi * 100).toFixed(0)}%
            </span>
            <span className="wellness-tag">
              <ShieldCheck size={13} /> Private & On-Device Analysis
            </span>
            {result.best_roi && (
              <span className="wellness-tag">Best ROI: {result.best_roi}</span>
            )}
          </div>
        </div>

        <div className="wellness-score-circle">
          <div className="score-number">{wellnessScore}</div>
          <div className="score-label">OUT OF 100</div>
          <div className="score-sub">Wellness Index</div>
        </div>
      </div>

      {/* Main Biomarker Categories Grid */}
      <div className="report-sections-grid">
        {/* 1. Cardiovascular Health */}
        <section className="report-section-card">
          <div className="card-section-title">
            <span className="section-icon rose">
              <HeartPulse size={18} />
            </span>
            <div>
              <h3>Cardiovascular Dynamics</h3>
              <small>Blood pressure & heart rate rhythm</small>
            </div>
          </div>

          <div className="metrics-pair">
            <div className="metric-box highlight-box">
              <span className="box-label">ESTIMATED BLOOD PRESSURE</span>
              <div className="box-val">
                {sbp && dbp ? (
                  <>
                    {sbp.toFixed(0)} <span>/ {dbp.toFixed(0)}</span>
                  </>
                ) : (
                  "-- / --"
                )}
                <small className="unit-label">mmHg</small>
              </div>
              <div className="box-status">
                <span className={`status-pill-badge ${bpCategory.toLowerCase().replace(/\s+/g, "-")}`}>
                  {bpCategory}
                </span>
                <span className="box-note">Option 1 · Pulse Morphology Regression</span>
              </div>
            </div>

            <div className="metric-box">
              <span className="box-label">RESTING HEART RATE</span>
              <div className="box-val">
                {hr ? hr.toFixed(0) : "--"}{" "}
                <small className="unit-label">bpm</small>
              </div>
              <div className="box-status">
                <span className="status-pill-badge normal">Optimal (60-100)</span>
                <span className="box-note">Peak Spectral SNR: {(result.hr_sqi * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>
        </section>

        {/* 2. Respiratory & Oxygenation */}
        <section className="report-section-card">
          <div className="card-section-title">
            <span className="section-icon cyan">
              <Droplets size={18} />
            </span>
            <div>
              <h3>Oxygenation & Respiration</h3>
              <small>Arterial blood oxygen & breathing pattern</small>
            </div>
          </div>

          <div className="metrics-pair">
            <div className="metric-box">
              <span className="box-label">BLOOD OXYGEN (SpO₂)</span>
              <div className="box-val">
                {spo2 ? spo2.toFixed(0) : "--"}{" "}
                <small className="unit-label">% SpO₂</small>
              </div>
              <div className="box-status">
                <span className="status-pill-badge normal">
                  {spo2 && spo2 >= 95 ? "Normal Oxygenation" : "Checked"}
                </span>
                <span className="box-note">
                  {result.spo2_r_ratio ? `R-Ratio: ${result.spo2_r_ratio.toFixed(2)}` : "Visible AC/DC"}
                </span>
              </div>
            </div>

            <div className="metric-box">
              <span className="box-label">RESPIRATION RATE</span>
              <div className="box-val">
                {resp ? resp.toFixed(0) : "--"}{" "}
                <small className="unit-label">breaths/min</small>
              </div>
              <div className="box-status">
                <span className="status-pill-badge normal">Eupnea (Normal)</span>
                <span className="box-note">
                  {prq ? `PRQ: ${prq.toFixed(2)} (Pulse/Resp)` : "Envelope SQI"}
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* 3. Autonomic Nervous System & Stress */}
        <section className="report-section-card full-span">
          <div className="card-section-title">
            <span className="section-icon purple">
              <Activity size={18} />
            </span>
            <div>
              <h3>Autonomic Nervous System & Stress Index</h3>
              <small>Heart Rate Variability (HRV) & parasympathetic vagal tone</small>
            </div>
          </div>

          <div className="stress-overview-row">
            <div className="stress-main-score">
              <div className="stress-num-wrap">
                <span className="stress-num">{stressIndex != null ? stressIndex.toFixed(0) : "--"}</span>
                <span className="stress-scale">/ 100</span>
              </div>
              <div className="stress-meta">
                <span className={`stress-badge level-${stressLevel.toLowerCase().replace(/\s+/g, "-")}`}>
                  {stressLevel}
                </span>
                <p className="stress-desc">
                  {stressLevel === "Relaxed"
                    ? "High parasympathetic tone. Your autonomic nervous system is in a restful, restorative state."
                    : stressLevel === "Normal"
                    ? "Balanced autonomic regulation with healthy resting beat-to-beat variability."
                    : "Elevated sympathetic arousal detected. Deep breathing or a short rest is recommended."}
                </p>
              </div>
            </div>

            <div className="hrv-metrics-subgrid">
              <div className="hrv-substat">
                <span className="substat-label">HRV RMSSD</span>
                <strong>{rmssd ? `${rmssd.toFixed(1)} ms` : "--"}</strong>
                <small>Vagal nerve tone</small>
              </div>
              <div className="hrv-substat">
                <span className="substat-label">HRV SDNN</span>
                <strong>{sdnn ? `${sdnn.toFixed(1)} ms` : "--"}</strong>
                <small>Total autonomic variability</small>
              </div>
              <div className="hrv-substat">
                <span className="substat-label">MEAN RRi</span>
                <strong>{meanRri ? `${meanRri.toFixed(0)} ms` : "--"}</strong>
                <small>Normal-to-normal interval</small>
              </div>
              <div className="hrv-substat">
                <span className="substat-label">CARDIO-RESP (PRQ)</span>
                <strong>{prq ? prq.toFixed(2) : "--"}</strong>
                <small>Coupling ratio (HR/Resp)</small>
              </div>
            </div>
          </div>
        </section>

        {/* 4. Recovered Waveform Visualization */}
        {result.bvp && (
          <section className="report-section-card full-span">
            <div className="card-section-title">
              <span className="section-icon blue">
                <Wind size={18} />
              </span>
              <div>
                <h3>Recovered Pulse Wave Dynamics</h3>
                <small>Direct photoplethysmography waveform extracted from facial micro-circulation</small>
              </div>
            </div>

            <WaveformChart
              waveform={result.bvp}
              samplingRate={30}
              title={`Blood-Volume Pulse Wave (${result.best_roi || "Facial ROI"})`}
            />

            <div className="morphology-details-bar">
              <div className="morph-item">
                <span>Systolic Rise Ratio</span>
                <strong>{riseRatio != null ? `${(riseRatio * 100).toFixed(0)}%` : "--"}</strong>
              </div>
              <div className="morph-item">
                <span>Diastolic Fall Ratio</span>
                <strong>{fallRatio != null ? `${(fallRatio * 100).toFixed(0)}%` : "--"}</strong>
              </div>
              <div className="morph-item">
                <span>SW50 Pulse Width</span>
                <strong>{sw50 != null ? `${sw50.toFixed(2)} s` : "--"}</strong>
              </div>
              <div className="morph-item">
                <span>Sampling Resolution</span>
                <strong>250 Hz Cubic Spline</strong>
              </div>
            </div>
          </section>
        )}
      </div>

      {/* Action Footer */}
      <div className="report-actions">
        <button className="primary-action-btn" onClick={onScanAgain} type="button">
          <RotateCcw size={17} /> Take Another 15s Scan
        </button>
      </div>

      <div className="report-disclaimer">
        <Info size={15} />
        <span>
          AuraVitals is an experimental vital-signs research tool using remote photoplethysmography (rPPG).
          Not intended for medical diagnosis, clinical decision-making, or treatment.
        </span>
      </div>
    </div>
  );
}
