import { useEffect, useRef, useState, useCallback } from "react";
import {
  Camera,
  Video,
  VideoOff,
  AlertTriangle,
  Play,
  Square,
  Activity,
  SwitchCamera,
} from "lucide-react";
import type { RoiTrace } from "../types";

interface CameraCaptureProps {
  onCaptureComplete: (rois: RoiTrace[]) => void;
  isAnalyzing: boolean;
}

interface RoiBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

const TARGET_DURATION_SEC = 15;

export function CameraCapture({ onCaptureComplete, isAnalyzing }: CameraCaptureProps) {
  const [streamActive, setStreamActive] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [lightingState, setLightingState] = useState<"optimal" | "dim" | "glare">("optimal");
  const [currentFps, setCurrentFps] = useState(30);
  const [facingMode, setFacingMode] = useState<"user" | "environment">("user");

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const miniGraphRef = useRef<HTMLCanvasElement | null>(null);

  const streamRef = useRef<MediaStream | null>(null);
  const animFrameIdRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);

  // Buffer holding sampled ROI color traces
  const bufferRef = useRef<{
    forehead: { t: number[]; r: number[]; g: number[]; b: number[] };
    leftCheek: { t: number[]; r: number[]; g: number[]; b: number[] };
    rightCheek: { t: number[]; r: number[]; g: number[]; b: number[] };
  }>({
    forehead: { t: [], r: [], g: [], b: [] },
    leftCheek: { t: [], r: [], g: [], b: [] },
    rightCheek: { t: [], r: [], g: [], b: [] },
  });

  // Rolling buffer for live green channel visualization
  const rollingGreenRef = useRef<number[]>([]);

  // Stop media stream
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (animFrameIdRef.current) {
      cancelAnimationFrame(animFrameIdRef.current);
      animFrameIdRef.current = null;
    }
    setStreamActive(false);
    setIsRecording(false);
    setElapsedSec(0);
  }, []);

  // Start media stream with specified facingMode
  const startCamera = async (targetFacing: "user" | "environment" = facingMode) => {
    setErrorMsg(null);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: targetFacing,
          width: { ideal: 640 },
          height: { ideal: 480 },
        },
        audio: false,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setFacingMode(targetFacing);
      setStreamActive(true);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to access camera. Check browser permissions.";
      setErrorMsg(message);
      setStreamActive(false);
    }
  };

  const toggleFacingMode = async () => {
    const nextMode = facingMode === "user" ? "environment" : "user";
    await startCamera(nextMode);
  };

  // Helper to calculate mean RGB from a bounding box
  const getMeanRgb = (
    ctx: CanvasRenderingContext2D,
    box: RoiBox,
    canvasW: number,
    canvasH: number,
  ): { r: number; g: number; b: number } => {
    const rx = Math.max(0, Math.floor(box.x * canvasW));
    const ry = Math.max(0, Math.floor(box.y * canvasH));
    const rw = Math.min(canvasW - rx, Math.floor(box.w * canvasW));
    const rh = Math.min(canvasH - ry, Math.floor(box.h * canvasH));

    if (rw <= 0 || rh <= 0) return { r: 0, g: 0, b: 0 };

    const imgData = ctx.getImageData(rx, ry, rw, rh);
    const data = imgData.data;
    let sumR = 0;
    let sumG = 0;
    let sumB = 0;
    const pixelCount = data.length / 4;

    for (let i = 0; i < data.length; i += 4) {
      sumR += data[i];
      sumG += data[i + 1];
      sumB += data[i + 2];
    }

    return {
      r: sumR / pixelCount,
      g: sumG / pixelCount,
      b: sumB / pixelCount,
    };
  };

  // Draw live rolling trace
  const drawMiniGraph = (values: number[]) => {
    const canvas = miniGraphRef.current;
    if (!canvas || values.length < 2) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1e-4;

    ctx.beginPath();
    ctx.strokeStyle = "#10b981";
    ctx.lineWidth = 1.8;
    ctx.lineCap = "round";

    values.forEach((v, idx) => {
      const x = (idx / (values.length - 1)) * canvas.width;
      const normalized = (v - min) / range;
      const y = canvas.height - 4 - normalized * (canvas.height - 8);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    ctx.stroke();
  };

  // Frame processing loop
  useEffect(() => {
    if (!streamActive) return;

    // Define ROI zones (relative to 640x480 frame)
    const rois: { forehead: RoiBox; leftCheek: RoiBox; rightCheek: RoiBox } = {
      forehead: { x: 0.38, y: 0.20, w: 0.24, h: 0.14 },
      leftCheek: { x: 0.28, y: 0.46, w: 0.16, h: 0.15 },
      rightCheek: { x: 0.56, y: 0.46, w: 0.16, h: 0.15 },
    };

    let frameCount = 0;
    let lastFpsCalc = performance.now();

    const processFrame = () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.readyState < 2) {
        animFrameIdRef.current = requestAnimationFrame(processFrame);
        return;
      }

      const now = performance.now();

      // FPS tracking
      frameCount++;
      if (now - lastFpsCalc >= 1000) {
        setCurrentFps(Math.round((frameCount * 1000) / (now - lastFpsCalc)));
        frameCount = 0;
        lastFpsCalc = now;
      }

      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (ctx) {
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Sample ROIs
        const fhRgb = getMeanRgb(ctx, rois.forehead, canvas.width, canvas.height);
        const lcRgb = getMeanRgb(ctx, rois.leftCheek, canvas.width, canvas.height);
        const rcRgb = getMeanRgb(ctx, rois.rightCheek, canvas.width, canvas.height);

        // Lighting check based on forehead
        const luma = 0.299 * fhRgb.r + 0.587 * fhRgb.g + 0.114 * fhRgb.b;
        if (luma < 45) setLightingState("dim");
        else if (luma > 215) setLightingState("glare");
        else setLightingState("optimal");

        // If recording, append to buffers
        if (isRecording) {
          if (startTimeRef.current === null) {
            startTimeRef.current = now;
          }
          const elapsed = (now - startTimeRef.current) / 1000;
          setElapsedSec(Math.min(elapsed, TARGET_DURATION_SEC));

          // Save timestamp & color channels
          bufferRef.current.forehead.t.push(now);
          bufferRef.current.forehead.r.push(fhRgb.r);
          bufferRef.current.forehead.g.push(fhRgb.g);
          bufferRef.current.forehead.b.push(fhRgb.b);

          bufferRef.current.leftCheek.t.push(now);
          bufferRef.current.leftCheek.r.push(lcRgb.r);
          bufferRef.current.leftCheek.g.push(lcRgb.g);
          bufferRef.current.leftCheek.b.push(lcRgb.b);

          bufferRef.current.rightCheek.t.push(now);
          bufferRef.current.rightCheek.r.push(rcRgb.r);
          bufferRef.current.rightCheek.g.push(rcRgb.g);
          bufferRef.current.rightCheek.b.push(rcRgb.b);

          // Update rolling live green graph
          rollingGreenRef.current.push(fhRgb.g);
          if (rollingGreenRef.current.length > 90) rollingGreenRef.current.shift();
          drawMiniGraph(rollingGreenRef.current);

          // Finish recording condition
          if (elapsed >= TARGET_DURATION_SEC) {
            setIsRecording(false);
            startTimeRef.current = null;

            const finalRois: RoiTrace[] = [
              {
                label: "forehead",
                t: [...bufferRef.current.forehead.t],
                r: [...bufferRef.current.forehead.r],
                g: [...bufferRef.current.forehead.g],
                b: [...bufferRef.current.forehead.b],
              },
              {
                label: "left_cheek",
                t: [...bufferRef.current.leftCheek.t],
                r: [...bufferRef.current.leftCheek.r],
                g: [...bufferRef.current.leftCheek.g],
                b: [...bufferRef.current.leftCheek.b],
              },
              {
                label: "right_cheek",
                t: [...bufferRef.current.rightCheek.t],
                r: [...bufferRef.current.rightCheek.r],
                g: [...bufferRef.current.rightCheek.g],
                b: [...bufferRef.current.rightCheek.b],
              },
            ];

            onCaptureComplete(finalRois);
          }
        }
      }

      animFrameIdRef.current = requestAnimationFrame(processFrame);
    };

    animFrameIdRef.current = requestAnimationFrame(processFrame);

    return () => {
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
    };
  }, [streamActive, isRecording, onCaptureComplete]);

  // Clean up stream on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  const handleStartRecording = () => {
    // Reset buffers
    bufferRef.current = {
      forehead: { t: [], r: [], g: [], b: [] },
      leftCheek: { t: [], r: [], g: [], b: [] },
      rightCheek: { t: [], r: [], g: [], b: [] },
    };
    rollingGreenRef.current = [];
    startTimeRef.current = null;
    setElapsedSec(0);
    setIsRecording(true);
  };

  const handleCancelRecording = () => {
    setIsRecording(false);
    startTimeRef.current = null;
    setElapsedSec(0);
  };

  const progressPercent = Math.min(100, (elapsedSec / TARGET_DURATION_SEC) * 100);

  return (
    <div className="camera-card">
      <div className="camera-header">
        <div>
          <span className="section-kicker">CONTACTLESS OPTICAL SENSOR</span>
          <h3>Live Facial rPPG</h3>
        </div>
        <div className="camera-badges">
          {streamActive && (
            <>
              <button
                className="pill-badge flip-badge"
                type="button"
                onClick={toggleFacingMode}
                disabled={isRecording}
                title="Switch Front/Rear Camera"
              >
                <SwitchCamera size={12} />
                <span>{facingMode === "user" ? "Front" : "Rear"}</span>
              </button>
              <span className="pill-badge fps-badge">{currentFps} FPS</span>
              <span className={`pill-badge light-badge ${lightingState}`}>
                <span className="dot" />
                {lightingState === "optimal"
                  ? "Good Light"
                  : lightingState === "dim"
                  ? "Dim Light"
                  : "Glare"}
              </span>
            </>
          )}
        </div>
      </div>

      <p className="camera-help">
        Center your face inside the oval guide under even lighting and breathe naturally. Our
        algorithm recovers your blood-volume pulse from micro-color variations across your skin.
      </p>

      {/* Viewfinder Container */}
      <div className={`viewfinder-wrapper ${streamActive ? "has-stream" : "is-dormant"} ${isRecording ? "is-recording" : ""}`}>
        <video
          ref={videoRef}
          playsInline
          muted
          autoPlay
          className={`camera-video ${streamActive ? "active" : "dormant"} ${facingMode === "user" ? "mirror-cam" : "normal-cam"}`}
        />

        {/* Hidden processing canvas */}
        <canvas ref={canvasRef} style={{ display: "none" }} />

        {/* Guides overlay when stream is on */}
        {streamActive && (
          <div className="viewfinder-overlay" aria-hidden="true">
            {/* Center Face Alignment Oval with Scanning Pulse */}
            <div className={`face-oval-guide ${isRecording ? "scanning" : ""}`} />

            {/* Futuristic scan sweep bar */}
            {isRecording && <div className="scan-laser-line" />}

            {/* Target ROI Boxes */}
            <div className="roi-box roi-forehead">
              <span className="roi-tag">Forehead</span>
            </div>
            <div className="roi-box roi-left-cheek">
              <span className="roi-tag">Left Cheek</span>
            </div>
            <div className="roi-box roi-right-cheek">
              <span className="roi-tag">Right Cheek</span>
            </div>

            {/* Recording indicator */}
            {isRecording && (
              <div className="recording-beacon">
                <span className="rec-dot" />
                <span>SCANNING {elapsedSec.toFixed(1)}s / {TARGET_DURATION_SEC}s</span>
              </div>
            )}
          </div>
        )}

        {/* Dormant / Inactive placeholder */}
        {!streamActive && (
          <div className="viewfinder-dormant">
            <div className="dormant-icon">
              <Camera size={44} strokeWidth={1.5} />
            </div>
            <p>Camera is currently off</p>
            <span className="dormant-sub">
              Privacy guaranteed: raw video never leaves your device. Only mean RGB color traces are computed locally.
            </span>
            <button className="start-cam-btn" type="button" onClick={() => startCamera(facingMode)}>
              <Video size={16} /> Enable Camera
            </button>
          </div>
        )}
      </div>

      {/* Progress & Live Pulsation Graph when recording */}
      {isRecording && (
        <div className="recording-progress-panel">
          <div className="progress-labels">
            <span>Sampling photoplethysmography traces...</span>
            <strong>{progressPercent.toFixed(0)}% · {(TARGET_DURATION_SEC - elapsedSec).toFixed(0)}s left</strong>
          </div>
          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className="live-signal-row">
            <span className="signal-label">
              <Activity size={14} className="pulse-color" /> Live optical pulsation
            </span>
            <div className="mini-graph-container">
              <canvas ref={miniGraphRef} width={320} height={38} className="mini-live-graph" />
            </div>
          </div>
        </div>
      )}

      {errorMsg && (
        <div className="camera-error-banner" role="alert">
          <AlertTriangle size={16} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Camera Toolbar */}
      <div className="camera-controls">
        {streamActive && (
          <>
            {!isRecording ? (
              <button
                className="btn-record"
                type="button"
                onClick={handleStartRecording}
                disabled={isAnalyzing}
              >
                <Play size={18} fill="currentColor" /> Record 15s Vitals
              </button>
            ) : (
              <button
                className="btn-cancel-rec"
                type="button"
                onClick={handleCancelRecording}
              >
                <Square size={16} fill="currentColor" /> Cancel Capture
              </button>
            )}

            <button
              className="btn-flip-cam"
              type="button"
              onClick={toggleFacingMode}
              disabled={isRecording}
              title="Switch Front/Rear Camera"
            >
              <SwitchCamera size={16} />
              <span>Flip</span>
            </button>

            <button
              className="btn-stop-cam"
              type="button"
              onClick={stopCamera}
              disabled={isRecording}
              title="Turn off camera"
            >
              <VideoOff size={16} />
              <span>Stop</span>
            </button>
          </>
        )}
      </div>
    </div>
  );
}
