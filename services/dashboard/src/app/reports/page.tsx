"use client";
import { useState } from "react";

const LGA_ID = process.env.NEXT_PUBLIC_LGA_ID || "Abeokuta South";

export default function ReportsPage() {
  const [downloading, setDownloading] = useState<string | null>(null);

  const download = async (type: "pdf" | "ocds") => {
    setDownloading(type);
    try {
      const token = localStorage.getItem("access_token");
      const url = type === "pdf"
        ? `/api/v1/audit/lga/${LGA_ID}/report.pdf`
        : `/api/v1/multilateral/export/ocds?lga_id=${LGA_ID}`;
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = type === "pdf" ? `srave-gap-report-${LGA_ID}.pdf` : `srave-ocds-${LGA_ID}.json`;
      a.click();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-semibold">Reports</h1>
      <div className="bg-white rounded-xl shadow-sm divide-y">
        <div className="p-6 flex items-center justify-between">
          <div>
            <p className="font-medium">Gap Analysis Report</p>
            <p className="text-sm text-gray-500 mt-0.5">Signed PDF — revenue gap, compliance %, audit hash</p>
          </div>
          <button onClick={() => download("pdf")} disabled={downloading === "pdf"}
            className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700 disabled:opacity-50">
            {downloading === "pdf" ? "…" : "Download PDF"}
          </button>
        </div>
        <div className="p-6 flex items-center justify-between">
          <div>
            <p className="font-medium">OCDS Export</p>
            <p className="text-sm text-gray-500 mt-0.5">Open Contracting Data Standard JSON for multilateral submission</p>
          </div>
          <button onClick={() => download("ocds")} disabled={downloading === "ocds"}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50">
            {downloading === "ocds" ? "…" : "Download JSON"}
          </button>
        </div>
      </div>
    </div>
  );
}
