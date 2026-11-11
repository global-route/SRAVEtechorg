"use client";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

const LGA_ID = process.env.NEXT_PUBLIC_LGA_ID || "Abeokuta South";

interface JobStatus { job_id: string; status: string; buildings_detected?: number; error?: string; }

export default function IngestPage() {
  const [bbox, setBbox] = useState("3.3000, 6.8800, 3.4500, 7.0500");
  const [job, setJob] = useState<JobStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trigger = async () => {
    setLoading(true); setError(null); setJob(null);
    try {
      const coords = bbox.split(",").map((s) => parseFloat(s.trim()));
      if (coords.length !== 4 || coords.some(isNaN)) throw new Error("Enter 4 comma-separated numbers");
      const res = await apiFetch("/spatial/ingest", {
        method: "POST",
        body: JSON.stringify({ lga_id: LGA_ID, bounding_box: coords }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setJob(data);
      poll(data.job_id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const poll = (jobId: string) => {
    const iv = setInterval(async () => {
      const res = await apiFetch(`/spatial/ingest/${jobId}`);
      const data: JobStatus = await res.json();
      setJob(data);
      if (["complete", "failed"].includes(data.status)) clearInterval(iv);
    }, 4000);
  };

  const STATUS_COLOR: Record<string, string> = {
    queued: "text-gray-500", processing: "text-blue-600", imagery_ready: "text-blue-600",
    extracting: "text-yellow-600", complete: "text-green-600", failed: "text-red-600",
  };

  return (
    <div className="max-w-xl space-y-6">
      <h1 className="text-2xl font-semibold">Trigger Satellite Ingest</h1>
      <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">LGA</label>
          <input value={LGA_ID} readOnly className="w-full border rounded px-3 py-2 text-sm bg-gray-50" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">
            Bounding Box <span className="text-gray-400 font-normal">(min_lon, min_lat, max_lon, max_lat)</span>
          </label>
          <input value={bbox} onChange={(e) => setBbox(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm font-mono" />
        </div>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <button onClick={trigger} disabled={loading}
          className="w-full bg-green-600 text-white py-2 rounded hover:bg-green-700 disabled:opacity-50 text-sm font-medium">
          {loading ? "Queuing…" : "Start Ingest"}
        </button>
      </div>

      {job && (
        <div className="bg-white rounded-xl shadow-sm p-6 space-y-2">
          <p className="text-xs text-gray-400 font-mono">{job.job_id}</p>
          <p className={`text-lg font-semibold ${STATUS_COLOR[job.status] ?? "text-gray-700"}`}>
            {job.status.replace("_", " ")}
          </p>
          {job.buildings_detected !== undefined && (
            <p className="text-sm text-gray-600">{job.buildings_detected.toLocaleString()} buildings detected</p>
          )}
          {job.error && <p className="text-sm text-red-500">{job.error}</p>}
          {!["complete","failed"].includes(job.status) && (
            <p className="text-xs text-gray-400 animate-pulse">Polling every 4s…</p>
          )}
        </div>
      )}
    </div>
  );
}
