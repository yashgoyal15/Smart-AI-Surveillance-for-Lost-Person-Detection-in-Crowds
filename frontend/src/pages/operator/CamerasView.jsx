import React, { useEffect, useState } from "react";
import { Camera, Play, Square, Settings } from "lucide-react";
import { getCameras, startCamera, stopCamera, updateCamera } from "../../services/cameraService.js";
import { AI_URL, getToken } from "../../services/api.js";

// ------------------------------------------------------------------
// Our team has 4 members, so the system has exactly 4 cameras.
// Each one reads video from a "source" that you can change here:
//   0 or 1                         -> webcam on the computer running the AI service
//   videos/cam3.mp4                -> a video file (good for demos)
//   http://192.168.1.5:8080/video  -> a phone (IP Webcam app)
//   rtsp://user:pass@192.168.1.20/stream1 -> an IP / CCTV camera
// ------------------------------------------------------------------

function CameraCard({ camera, onChange }) {
  const [source, setSource] = useState(camera.source);
  const [showSettings, setShowSettings] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [streamFailed, setStreamFailed] = useState(false);
  // changing this number makes the <img> reconnect to the stream
  const [streamKey, setStreamKey] = useState(0);

  const isOnline = camera.status === "online";

  async function handleStart() {
    setBusy(true);
    setMessage("");
    try {
      await startCamera(camera.id);
      setStreamFailed(false);
      setStreamKey(streamKey + 1);
      setMessage("Connecting...");
      setTimeout(onChange, 2500); // give the camera a moment, then refresh the status
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleStop() {
    setBusy(true);
    setMessage("");
    try {
      await stopCamera(camera.id);
      setTimeout(onChange, 800);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveSource() {
    try {
      await updateCamera(camera.id, { source });
      setMessage(isOnline ? "Saved. Stop and start the camera to use the new source." : "Saved.");
      setShowSettings(false);
      onChange();
    } catch (err) {
      setMessage(err.message);
    }
  }

  // an <img> tag can't send headers, so the login token goes in the URL
  const streamUrl = `${AI_URL}/stream/${camera.id}?token=${getToken()}&k=${streamKey}`;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
      {/* video area */}
      <div className="aspect-video bg-slate-950 flex items-center justify-center relative">
        {isOnline && !streamFailed ? (
          <img
            key={streamKey}
            src={streamUrl}
            alt={`${camera.id} live`}
            className="w-full h-full object-contain"
            onError={() => setStreamFailed(true)}
          />
        ) : (
          <div className="text-center">
            <Camera className="text-slate-700 mx-auto" size={36} />
            <p className="text-slate-600 text-xs mt-2">
              {isOnline ? "Stream not available - press Stop, then Start" : "Camera is off"}
            </p>
          </div>
        )}
        <span
          className={
            "absolute top-2 right-2 w-2.5 h-2.5 rounded-full " + (isOnline ? "bg-emerald-400" : "bg-slate-600")
          }
        />
      </div>

      <div className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">{camera.id}</div>
            <div className="text-xs text-slate-400">{camera.location}</div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
              title="Camera settings"
            >
              <Settings size={14} />
            </button>
            {isOnline ? (
              <button
                onClick={handleStop}
                disabled={busy}
                className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium bg-red-500/10 text-red-400 hover:bg-red-500/20 disabled:opacity-60"
              >
                <Square size={12} /> Stop
              </button>
            ) : (
              <button
                onClick={handleStart}
                disabled={busy}
                className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium bg-emerald-500 text-slate-950 hover:bg-emerald-400 disabled:opacity-60"
              >
                <Play size={12} /> Start
              </button>
            )}
          </div>
        </div>

        {showSettings && (
          <div className="mt-3">
            <label className="text-xs text-slate-400">Video source</label>
            <input
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="w-full mt-1 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-xs outline-none focus:border-emerald-500"
              placeholder="0, videos/cam3.mp4, http://phone-ip:8080/video, rtsp://..."
            />
            <button
              onClick={handleSaveSource}
              className="mt-2 px-3 py-1.5 rounded text-xs font-medium bg-slate-700 hover:bg-slate-600"
            >
              Save source
            </button>
          </div>
        )}

        {!showSettings && <div className="text-xs text-slate-500 mt-2 truncate">Source: {camera.source}</div>}
        {message && <div className="text-xs text-amber-400 mt-2">{message}</div>}
      </div>
    </div>
  );
}

export default function CamerasView() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  async function loadCameras() {
    try {
      setCameras(await getCameras());
      setErrorMsg("");
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  }

  // load once, then refresh every few seconds so Start/Stop is reflected
  useEffect(() => {
    loadCameras();
    const timer = setInterval(loadCameras, 5000);
    return () => clearInterval(timer);
  }, []);

  if (loading) return <p className="text-slate-400 text-sm">Loading cameras...</p>;

  return (
    <div>
      {errorMsg && <p className="text-red-400 text-sm mb-4">{errorMsg}</p>}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        {cameras.map((c) => (
          <CameraCard key={c.id} camera={c} onChange={loadCameras} />
        ))}
      </div>
    </div>
  );
}
