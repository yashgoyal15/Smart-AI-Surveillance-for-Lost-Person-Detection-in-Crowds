import React, { useEffect, useState } from "react";
import { Search, Download } from "lucide-react";
import { getAlerts, exportAuditLog } from "../../services/alertService.js";
import { formatTime, formatPercent } from "../../utils/format.js";

export default function AuditView() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [searchText, setSearchText] = useState("");

  useEffect(() => {
    getAlerts({ limit: 500 })
      .then(setAlerts)
      .catch((err) => setErrorMsg(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleExport() {
    try {
      await exportAuditLog();
    } catch (err) {
      setErrorMsg(err.message);
    }
  }

  const filteredLog = alerts.filter((a) => {
    const text = (a.personName + a.camId + a.method + a.status).toLowerCase();
    return text.includes(searchText.toLowerCase());
  });

  if (loading) return <p className="text-slate-400 text-sm">Loading audit log...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="relative w-72">
          <Search className="absolute left-3 top-2.5 text-slate-500" size={16} />
          <input
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search by name or camera ID"
            className="w-full bg-slate-900 border border-slate-800 rounded pl-9 pr-3 py-2 text-sm outline-none focus:border-emerald-500"
          />
        </div>
        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-3 py-2 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700"
        >
          <Download size={14} /> Export CSV
        </button>
      </div>

      {errorMsg && <p className="text-red-400 text-sm mb-3">{errorMsg}</p>}

      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-left text-slate-400 border-b border-slate-800">
            <th className="py-2 font-medium">Person</th>
            <th className="py-2 font-medium">Camera</th>
            <th className="py-2 font-medium">Result</th>
            <th className="py-2 font-medium">How</th>
            <th className="py-2 font-medium">Confidence</th>
            <th className="py-2 font-medium">Time</th>
          </tr>
        </thead>
        <tbody>
          {filteredLog.map((a) => (
            <tr key={a.id} className="border-b border-slate-900">
              <td className="py-3">{a.personName}</td>
              <td className="py-3 text-slate-400">{a.camId}</td>
              <td className={"py-3 " + (a.status === "POSSIBLE" ? "text-amber-400" : "text-emerald-400")}>
                {a.status === "POSSIBLE" ? "Possible" : "Confirmed"}
              </td>
              <td className="py-3 text-slate-400">{a.method}</td>
              <td className="py-3">{formatPercent(a.confidence)}</td>
              <td className="py-3 text-slate-400">{formatTime(a.timestamp)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {filteredLog.length === 0 && <p className="text-slate-500 text-sm mt-4">No records found.</p>}
    </div>
  );
}
