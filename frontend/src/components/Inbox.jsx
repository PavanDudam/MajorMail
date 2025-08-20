import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronRight } from "lucide-react";

/** Utilities */
function senderName(raw) {
  if (!raw) return "Unknown";
  // "Name <email@x>" -> "Name"
  const match = raw.match(/^(.*?)\s*<.*?>$/);
  if (match && match[1].trim()) return match[1].trim();
  // plain email -> "local" part, capitalized
  if (raw.includes("@")) return raw.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  return raw;
}
function formatDate(s) {
  const d = new Date(s ?? "");
  if (isNaN(d)) return "—";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
function priorityTone(score = 0) {
  if (score >= 70) return "bg-red-100 text-red-700 ring-1 ring-red-200";
  if (score >= 40) return "bg-amber-100 text-amber-700 ring-1 ring-amber-200";
  return "bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200";
}

/** Gmail-like row table with expandable detail */
export default function Inbox({ emails }) {
  const [openId, setOpenId] = useState(null);

  const rows = useMemo(() => (emails ?? []).map(e => ({
    id: e.id,
    name: senderName(e.sender),
    subject: e.subject || "(No subject)",
    action: e.suggested_action || "—",
    priority: e.priority_score ?? 0,
    date: formatDate(e.received_at || e.created_at),
    summary: e.summary || "",
    category: e.category || "General",
    raw: e,
  })), [emails]);

  if (!rows.length) {
    return <p className="text-gray-600">📭 No emails yet. Fetch & process, then refresh.</p>;
  }

  return (
    <div className="rounded-2xl overflow-hidden shadow ring-1 ring-black/5 bg-white">
      {/* Header */}
      <div className="grid grid-cols-[220px_1fr_120px_180px_90px_40px] items-center px-4 py-3 bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
        <div>Sender</div>
        <div>Subject</div>
        <div className="text-center">Priority</div>
        <div>Action</div>
        <div className="text-right">Date</div>
        <div className="sr-only">Expand</div>
      </div>

      {/* Body */}
      <div className="divide-y divide-gray-100">
        {rows.map((r) => (
          <div key={r.id} className="relative">
            {/* Row as button */}
            <button
              className="w-full grid grid-cols-[220px_1fr_120px_180px_90px_40px] items-center gap-3 px-4 py-3 text-left
                         hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500
                         transition"
              onClick={() => setOpenId(openId === r.id ? null : r.id)}
              aria-expanded={openId === r.id}
            >
              {/* Sender */}
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 text-white grid place-items-center shadow">
                  {r.name[0]?.toUpperCase()}
                </div>
                <div className="font-medium text-gray-900 truncate">{r.name}</div>
              </div>

              {/* Subject */}
              <div className="truncate text-gray-700">{r.subject}</div>

              {/* Priority */}
              <div className="flex justify-center">
                <span className={`px-2.5 py-1 text-xs rounded-full ${priorityTone(r.priority)}`}>
                  {r.priority}
                </span>
              </div>

              {/* Action */}
              <div className="truncate text-gray-600">{r.action}</div>

              {/* Date */}
              <div className="text-right text-gray-500">{r.date}</div>

              {/* Chevron */}
              <div className="flex justify-end">
                {openId === r.id ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
              </div>
            </button>

            {/* Expanded panel */}
            <AnimatePresence initial={false}>
              {openId === r.id && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.22 }}
                  className="px-4 pb-4"
                >
                  <div className="mx-1 mt-2 rounded-xl border border-gray-100 bg-gray-50 p-4 shadow-inner">
                    <div className="flex flex-wrap gap-3 text-xs">
                      <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                        Category: {r.category}
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-gray-200 text-gray-700">
                        From: {r.raw.sender}
                      </span>
                    </div>
                    <div className="mt-3 text-sm leading-relaxed text-gray-800">
                      <div className="font-semibold mb-1">Summary</div>
                      <p className="text-gray-700">{r.summary || "No summary available."}</p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </div>
  );
}
