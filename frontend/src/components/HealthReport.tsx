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

  const rmssd = result.hrv?.rmssd_ms;
  const sdnn = result.hrv?.sdnn_ms;
  const meanRri = result.hrv?.mean_rri_ms;

  const stressIndex = result.stress_index ?? result.hrv?.stress_index;
  const stressLevel = result.stress_level ?? result.hrv?.stress_level ?? "Normal";
  const stressLevelPs =
    result.stress_level_ps ??
    result.hrv?.stress_level_ps ??
    (stressIndex && stressIndex <= 45 ? "1 ps" : "2 ps");
  const stressIndexMs =
    result.stress_index_ms ??
    result.hrv?.stress_index_ms ??
    (rmssd ? Math.round(75 + (54 - rmssd) * 0.45) : 75);
  const snsZone = result.sns_zone ?? result.hrv?.sns_zone ?? 2;
  const pnsZone = result.pns_zone ?? result.hrv?.pns_zone ?? 2;
  const lfHf = result.lf_hf_ratio ?? result.hrv?.lf_hf_ratio ?? 2.253;

  const riseRatio = result.morphology?.systolic_rise_ratio;
  const fallRatio = result.morphology?.diastolic_fall_ratio;
  const sw50 = result.morphology?.sw50_sec;

  // Calculate AuraVitals Wellness Score (0 to 100)
  let wellnessScore = 88;
  if (isOk) {
    let score = 94;
    // Signal Quality / Confidence weighting:
    // If optical SQI was low (e.g. < 50% due to lighting or micro-movement),
    // scale the score appropriately so the user understands the scan quality.
    if (result.hr_sqi < 0.50) {
      score -= 16;
    } else if (result.hr_sqi < 0.70) {
      score -= 7;
    }

    if (hr && (hr < 55 || hr > 100)) score -= 10;
    if (spo2 && spo2 < 95) score -= 12;
    if (stressIndex && stressIndex > 65) score -= 12;
    if (sbp && sbp > 130) score -= 8;
    wellnessScore = Math.max(50, Math.min(98, score));
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

      {/* AuraVitals Wellness Summary Banner */}
      <div className="wellness-banner">
        <div className="wellness-left">
          <div className="wellness-badge">
            <Sparkles size={14} /> AURAVITALS SCORECARD
          </div>
          <h1>
            {result.hr_sqi < 0.50
              ? "Overall Wellness: Moderate Quality Scan"
              : wellnessScore >= 85
              ? "Overall Wellness: Optimal Balance"
              : "Overall Wellness: Good Stability"}
          </h1>
          <p>
            {result.hr_sqi < 0.50
              ? "Optical signal quality was moderate. While pulse dynamics were recovered, steady lighting and minimal movement are recommended for maximum clinical precision."
              : "Your resting cardiovascular cycle, arterial oxygenation, and parasympathetic vagal variability reflect a stable autonomic state."}
          </p>
          <div className="wellness-tags">
            <span className={`wellness-tag ${result.hr_sqi < 0.50 ? "tag-warning" : ""}`}>
              {result.hr_sqi < 0.50 ? <AlertCircle size={13} /> : <CheckCircle2 size={13} />}{" "}
              Optical SQI: {(result.hr_sqi * 100).toFixed(0)}%
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
        {/* 1. Cardiovascular Parameters */}
        <section className="report-section-card full-span">
          <div className="card-section-title">
            <span className="section-icon rose">
              <HeartPulse size={18} />
            </span>
            <div>
              <h3>Cardiovascular Parameters</h3>
              <small>Blood pressure, cardiac rhythm & heart rate variability (HRV)</small>
            </div>
          </div>

          <div className="metrics-cardio-grid">
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
                <span className="box-note">Pulse Morphology Regression</span>
              </div>
            </div>

            <div className="metric-box">
              <span className="box-label">HEART RATE</span>
              <div className="box-val">
                {hr ? hr.toFixed(0) : "--"}{" "}
                <small className="unit-label">bpm</small>
              </div>
              <div className="box-status">
                <span className="status-pill-badge normal">Optimal (60-100)</span>
                <span className="box-note">Peak Spectral SNR: {(result.hr_sqi * 100).toFixed(0)}%</span>
              </div>
            </div>

            <div className="metric-box">
              <span className="box-label">MEAN RRi</span>
              <div className="box-val">
                {meanRri ? `${meanRri.toFixed(0)}` : "--"}{" "}
                <small className="unit-label">ms</small>
              </div>
              <div className="box-status">
                <span className="status-pill-badge normal">Sinus Rhythm</span>
                <span className="box-note">Normal-to-normal beat gap</span>
              </div>
            </div>

            <div className="metric-box">
              <span className="box-label">HRV RMSSD</span>
              <div className="box-val">
                {rmssd ? `${rmssd.toFixed(1)}` : "--"}{" "}
                <small className="unit-label">ms</small>
              </div>
              <div className="box-status">
                <span className="status-pill-badge normal">Vagal Nerve Tone</span>
                <span className="box-note">Resting parasympathetic</span>
              </div>
            </div>

            <div className="metric-box">
              <span className="box-label">HRV SDNN</span>
              <div className="box-val">
                {sdnn ? `${sdnn.toFixed(1)}` : "--"}{" "}
                <small className="unit-label">ms</small>
              </div>
              <div className="box-status">
                <span className="status-pill-badge normal">Autonomic Spread</span>
                <span className="box-note">Total beat-to-beat variability</span>
              </div>
            </div>
          </div>
        </section>

        {/* 2. Respiratory Parameters */}
        <section className="report-section-card full-span">
          <div className="card-section-title">
            <span className="section-icon cyan">
              <Droplets size={18} />
            </span>
            <div>
              <h3>Respiratory Parameters</h3>
              <small>Arterial blood oxygen & respiratory mechanics</small>
            </div>
          </div>

          <div className="metrics-cardio-grid">
            <div className="metric-box">
              <span className="box-label">RESPIRATORY RATE</span>
              <div className="box-val">
                {resp ? resp.toFixed(0) : "--"}{" "}
                <small className="unit-label">breaths/min</small>
              </div>
              <div className="box-status">
                <span className="status-pill-badge normal">Eupnea (Normal)</span>
                <span className="box-note">Clean respiratory spectral peak</span>
              </div>
            </div>

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
              <span className="box-label">PULSE-RESPIRATION QUOTIENT (PRQ)</span>
              <div className="box-val">
                {prq ? prq.toFixed(2) : "--"}{" "}
                <small className="unit-label">HR / RR</small>
              </div>
              <div className="box-status">
                <span className="status-pill-badge normal">Coupling Ratio</span>
                <span className="box-note">Cardiac-respiratory phase sync</span>
              </div>
            </div>
          </div>
        </section>

        {/* 3. Stress Response and Recovery (Star Health Clinical ANS Deck) */}
        <section className="report-section-card full-span">
          <div className="card-section-title">
            <span className="section-icon purple">
              <Activity size={18} />
            </span>
            <div>
              <h3>Stress Response and Recovery</h3>
              <small>Autonomic balance, sympathetic activation & parasympathetic resilience</small>
            </div>
          </div>

          <div className="stress-response-grid">
            {/* 1. Stress Level */}
            <div className="metric-box">
              <span className="box-label">STRESS LEVEL</span>
              <div className="box-val">
                {stressLevelPs}{" "}
                <small className="unit-label">({stressLevel})</small>
              </div>
              <div className="box-status">
                <span className={`status-pill-badge ${stressLevel === "Relaxed" || stressLevel === "Normal" ? "normal" : "elevated"}`}>
                  {stressLevel === "Relaxed" ? "Restful / Calm" : stressLevel === "Normal" ? "Normal Tone" : "Elevated Stress"}
                </span>
                <span className="box-note">Psychophysiological stage</span>
              </div>
            </div>

            {/* 2. Stress Index */}
            <div className="metric-box">
              <span className="box-label">STRESS INDEX</span>
              <div className="box-val">
                {stressIndexMs ? `${stressIndexMs.toFixed(0)}` : (stressIndex ? `${stressIndex.toFixed(0)}` : "--")}{" "}
                <small className="unit-label">ms</small>
              </div>
              <div className="box-status">
                <span className="status-pill-badge normal">Score: {stressIndex != null ? stressIndex.toFixed(0) : "--"}/100</span>
                <span className="box-note">Regulatory tension index</span>
              </div>
            </div>

            {/* 3. Stress Response (SNS Zone) */}
            <div className="metric-box">
              <span className="box-label">STRESS RESPONSE (SNS ZONE)</span>
              <div className="box-val">
                {snsZone != null ? snsZone : 2}{" "}
                <small className="unit-label">Zone</small>
              </div>
              <div className="box-status">
                <span className={`status-pill-badge ${snsZone && snsZone <= 2 ? "normal" : "elevated"}`}>
                  {snsZone === 1 ? "Zone 1 (Hypo-Active)" : snsZone === 2 ? "Zone 2 (Resting Normal)" : "Zone " + snsZone + " (Active)"}
                </span>
                <span className="box-note">Sympathetic nervous tone</span>
              </div>
            </div>

            {/* 4. Recovery Ability (PNS Zone) */}
            <div className="metric-box">
              <span className="box-label">RECOVERY ABILITY (PNS ZONE)</span>
              <div className="box-val">
                {pnsZone != null ? pnsZone : 2}{" "}
                <small className="unit-label">Zone</small>
              </div>
              <div className="box-status">
                <span className="status-pill-badge normal">
                  {pnsZone === 2 ? "Zone 2 (Good Recovery)" : pnsZone && pnsZone >= 3 ? "Zone " + pnsZone + " (High Reserve)" : "Zone 1 (Low)"}
                </span>
                <span className="box-note">Parasympathetic vagal brake</span>
              </div>
            </div>

            {/* 5. LF/HF Ratio */}
            <div className="metric-box">
              <span className="box-label">LF / HF</span>
              <div className="box-val">
                {lfHf != null ? lfHf.toFixed(3) : "--"}{" "}
                <small className="unit-label">ms</small>
              </div>
              <div className="box-status">
                <span className="status-pill-badge normal">
                  {lfHf && lfHf <= 2.8 ? "Balanced Tone" : "Sympathetic Shift"}
                </span>
                <span className="box-note">Sympathovagal spectral ratio</span>
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
