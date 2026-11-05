import { useMemo } from "react";

interface WaveformChartProps {
  waveform: number[] | null | undefined;
  samplingRate?: number;
  height?: number;
  title?: string;
  badge?: string;
}

export function WaveformChart({
  waveform,
  samplingRate = 30,
  height = 130,
  title = "Recovered BVP Pulse Wave",
  badge = "POS Wang · 30 Hz",
}: WaveformChartProps) {
  const { pathD, durationSec } = useMemo(() => {
    if (!waveform || waveform.length < 2) {
      return { pathD: "", durationSec: "0.0" };
    }

    // Display up to 10 seconds or full waveform
    const displaySamples = waveform.slice(-samplingRate * 12);
    const min = Math.min(...displaySamples);
    const max = Math.max(...displaySamples);
    const range = max - min || 1e-6;

    const width = 640;
    const paddingY = 16;
    const innerHeight = height - paddingY * 2;

    const coords: [number, number][] = displaySamples.map((val, idx) => {
      const x = (idx / (displaySamples.length - 1)) * width;
      const normalized = (val - min) / range;
      const y = height - paddingY - normalized * innerHeight;
      return [x, y];
    });

    const d = coords.reduce((acc, [x, y], idx) => {
      return idx === 0 ? `M ${x.toFixed(1)} ${y.toFixed(1)}` : `${acc} L ${x.toFixed(1)} ${y.toFixed(1)}`;
    }, "");

    return {
      pathD: d,
      durationSec: (displaySamples.length / samplingRate).toFixed(1),
    };
  }, [waveform, samplingRate, height]);

  if (!waveform || waveform.length === 0) {
    return (
      <div className="wave-visual empty-state" aria-hidden="true">
        <div className="wave-grid" />
        <svg viewBox="0 0 640 100" preserveAspectRatio="none">
          <path d="M0 50 H640" stroke="rgba(255,255,255,0.2)" strokeDasharray="4 4" />
        </svg>
        <span className="wave-caption">Awaiting pulse recording or demo input</span>
      </div>
    );
  }

  return (
    <div className="waveform-container">
      <div className="waveform-header">
        <span className="waveform-title">{title}</span>
        <span className="waveform-badge">{badge} ({durationSec}s window)</span>
      </div>
      <div className="wave-visual active-wave">
        <div className="wave-grid" />
        <svg viewBox={`0 0 640 ${height}`} preserveAspectRatio="none" className="pulse-svg">
          <defs>
            <linearGradient id="waveGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#818cf8" stopOpacity="0.1" />
            </linearGradient>
            <linearGradient id="strokeGradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="50%" stopColor="#818cf8" />
              <stop offset="100%" stopColor="#f43f5e" />
            </linearGradient>
          </defs>

          {/* Baseline reference */}
          <line
            x1="0"
            y1={height / 2}
            x2="640"
            y2={height / 2}
            stroke="rgba(255, 255, 255, 0.1)"
            strokeDasharray="3 3"
          />

          {/* Area fill */}
          {pathD && (
            <path
              d={`${pathD} L 640 ${height} L 0 ${height} Z`}
              fill="url(#waveGradient)"
              opacity="0.3"
            />
          )}

          {/* Pulse stroke */}
          {pathD && (
            <path
              d={pathD}
              fill="none"
              stroke="url(#strokeGradient)"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}
        </svg>
        <span className="wave-caption">
          rPPG Blood-Volume Pulse (BVP) Waveform · {waveform.length} samples
        </span>
      </div>
    </div>
  );
}
