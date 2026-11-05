import { useState } from "react";
import {
  HeartPulse,
  Sparkles,
  ShieldCheck,
  Sun,
  ScanFace,
  Smile,
  LoaderCircle,
  AlertTriangle,
} from "lucide-react";

import { analyzeRppg } from "./api/rppg";
import { CameraCapture } from "./components/CameraCapture";
import { HealthReport } from "./components/HealthReport";
import type { RppgAnalysisResponse, RoiTrace } from "./types";

function App() {
  const [rppgResult, setRppgResult] = useState<RppgAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCameraCapture = async (rois: RoiTrace[]) => {
    setError("");
    setLoading(true);

    try {
      const response = await analyzeRppg(rois);
      setRppgResult(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to connect to the analysis engine. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setRppgResult(null);
    setError("");
    setLoading(false);
  };

  return (
    <main className="app-shell">
      {/* Top Navbar */}
      <header className="topbar">
        <button
          className="brand"
          onClick={handleReset}
          type="button"
          style={{ background: "none", border: "none", padding: 0 }}
        >
          <span className="brand-mark">
            <HeartPulse size={21} strokeWidth={2.2} />
          </span>
          <span>
            Aura<span className="brand-light">Vitals</span>
          </span>
        </button>
        <div className="topbar-note">
          <span className="live-dot" />
          On-Device Optical AI
        </div>
      </header>

      {/* If scan result exists, show the Star Health Report Page! */}
      {rppgResult ? (
        <HealthReport result={rppgResult} onScanAgain={handleReset} />
      ) : (
        /* Otherwise show the clean Gen-Z Scan Home Page (No statistical tables!) */
        <div className="home-scan-flow">
          {/* Catchy Hero Header */}
          <section className="scan-hero">
            <div className="scan-pill">
              <Sparkles size={14} /> 15-SECOND BIOMETRIC SCAN
            </div>
            <h1>
              Scan your face.<br />
              <span className="gradient-text">Know your health status.</span>
            </h1>
            <p className="hero-subtext">
              No smartwatch. No finger clips. Just look into the camera — our optical AI
              reads your pulse wave, blood pressure, oxygenation & autonomic stress in 15 seconds.
            </p>
          </section>

          {/* Guide: How & Where to Put Your Face */}
          <section className="face-guide-section" aria-label="Face alignment instructions">
            <div className="guide-heading">
              <span className="section-kicker">3 QUICK TIPS FOR A PERFECT SCAN</span>
              <h3>How to position yourself</h3>
            </div>

            <div className="guide-steps-grid">
              <div className="guide-step-card">
                <div className="step-icon-wrap amber">
                  <Sun size={20} />
                </div>
                <div className="step-content">
                  <h4>1. Face the Light</h4>
                  <p>Sit facing a window or warm room light. Avoid backlights or heavy shadows.</p>
                </div>
              </div>

              <div className="guide-step-card">
                <div className="step-icon-wrap green">
                  <ScanFace size={20} />
                </div>
                <div className="step-content">
                  <h4>2. Align in the Oval</h4>
                  <p>Center your face inside the dashed guide. Keep your forehead and cheeks visible.</p>
                </div>
              </div>

              <div className="guide-step-card">
                <div className="step-icon-wrap teal">
                  <Smile size={20} />
                </div>
                <div className="step-content">
                  <h4>3. Hold Chill & Steady</h4>
                  <p>Breathe naturally and stay relaxed for the 15-second scan. Don’t move or talk.</p>
                </div>
              </div>
            </div>
          </section>

          {/* Central Camera Scan Viewport */}
          <section className="scanner-container">
            <CameraCapture
              onCaptureComplete={handleCameraCapture}
              isAnalyzing={loading}
            />

            {/* Loading State Overlay / Feedback */}
            {loading && (
              <div className="analyzing-card" role="status">
                <LoaderCircle className="spin" size={24} />
                <div>
                  <h4>Analyzing micro-capillary pulse waves...</h4>
                  <p>Extracting heart rhythm, SpO₂, blood pressure & autonomic stress index.</p>
                </div>
              </div>
            )}

            {/* Error Message if API fails */}
            {error && (
              <div className="error-alert-banner" role="alert">
                <AlertTriangle size={18} />
                <span>{error}</span>
              </div>
            )}

            <div className="scanner-trust-bar">
              <ShieldCheck size={16} />
              <span>100% Private: Video is processed locally in your browser. Raw footage is never saved.</span>
            </div>
          </section>
        </div>
      )}

      {/* Clean Footer */}
      <footer className="footer">
        <span>© 2026 AuraVitals · FaceOff Architecture</span>
        <span>Research preview · Not for clinical diagnosis or treatment</span>
      </footer>
    </main>
  );
}

export default App;
