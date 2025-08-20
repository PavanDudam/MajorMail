import { useState, useEffect } from "react";
import axios from "axios";
import Inbox from "./components/Inbox";

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [userEmail, setUserEmail] = useState(localStorage.getItem("userEmail") || null);
  const [emails, setEmails] = useState([]);
  const [senderEmail, setSenderEmail] = useState("");
  const [dossier, setDossier] = useState(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  // Capture ?email= from backend redirect after Google OAuth
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const emailFromCallback = params.get("email");
    if (emailFromCallback) {
      localStorage.setItem("userEmail", emailFromCallback);
      setUserEmail(emailFromCallback);
      // Clean URL
      window.history.replaceState({}, document.title, "/");
    }
  }, []);

  // ---- Auth ----
  const loginWithGoogle = () => {
    window.location.href = `${API_BASE}/auth/login`;
  };
  const logout = () => {
    localStorage.removeItem("userEmail");
    setUserEmail(null);
    setEmails([]);
    setSenderEmail("");
    setDossier(null);
    setMsg("Logged out.");
  };

  // ---- Core flow ----
  const fetchFromGmail = async () => {
    if (!userEmail) return setMsg("Please login first.");
    setLoading(true);
    setMsg("Fetching emails from Gmail...");
    try {
      const res = await axios.get(`${API_BASE}/emails/fetch/${encodeURIComponent(userEmail)}`);
      setMsg(res.data?.message || "Fetched from Gmail.");
    } catch (e) {
      console.error(e);
      setMsg("Failed to fetch from Gmail. Check backend logs & Google scope/consent.");
    } finally {
      setLoading(false);
    }
  };

  const processEmails = async () => {
    if (!userEmail) return setMsg("Please login first.");
    setLoading(true);
    setMsg("Processing emails (summaries, categories, priorities)...");
    try {
      const res = await axios.post(`${API_BASE}/emails/process/${encodeURIComponent(userEmail)}`);
      setMsg(res.data?.message || "Processing started.");
    } catch (e) {
      console.error(e);
      setMsg("Failed to start processing. Make sure emails are fetched first.");
    } finally {
      setLoading(false);
    }
  };

  const refreshInbox = async (category = null) => {
    if (!userEmail) return setMsg("Please login first.");
    setLoading(true);
    setMsg("Loading inbox...");
    try {
      const url = category
        ? `${API_BASE}/emails/${encodeURIComponent(userEmail)}?category=${encodeURIComponent(category)}`
        : `${API_BASE}/emails/${encodeURIComponent(userEmail)}`;
      const res = await axios.get(url);
      setEmails(res.data || []);
      setMsg(`Loaded ${res.data?.length ?? 0} emails.`);
    } catch (e) {
      console.error(e);
      setMsg("Failed to load inbox.");
    } finally {
      setLoading(false);
    }
  };

  const loadDossier = async () => {
    if (!userEmail) return setMsg("Please login first.");
    if (!senderEmail) return setMsg("Enter a sender email or substring.");
    setLoading(true);
    setMsg("Loading sender dossier...");
    try {
      const res = await axios.get(
        `${API_BASE}/dossier/${encodeURIComponent(userEmail)}?sender_email=${encodeURIComponent(senderEmail)}`
      );
      setDossier(res.data);
      setMsg("Dossier loaded.");
    } catch (e) {
      console.error(e);
      setDossier(null);
      setMsg("No emails found for that sender. Make sure you've fetched & processed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">📩 MailMate AI</h1>

      {!userEmail ? (
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded"
          onClick={loginWithGoogle}
        >
          Login with Google
        </button>
      ) : (
        <div className="flex items-center gap-3 mb-4">
          <span>✅ Logged in as <b>{userEmail}</b></span>
          <button className="bg-red-500 text-white px-3 py-1 rounded" onClick={logout}>
            Logout
          </button>
        </div>
      )}

      <div className="flex flex-wrap gap-3 mb-4">
        <button className="bg-indigo-600 text-white px-4 py-2 rounded" onClick={fetchFromGmail}>
          1) Fetch from Gmail
        </button>
        <button className="bg-green-600 text-white px-4 py-2 rounded" onClick={processEmails}>
          2) Process Emails
        </button>
        <button className="bg-gray-700 text-white px-4 py-2 rounded" onClick={() => refreshInbox()}>
          3) Refresh Inbox
        </button>
      </div>

      {loading && <p>⏳ Working...</p>}
      {msg && <p className="mb-4 text-sm text-gray-700">{msg}</p>}

      {/* ---- Inbox Component ---- */}
      <h2 className="text-xl font-semibold mt-6 mb-2">Inbox</h2>
      <Inbox emails={emails} />

      {/* ---- Sender Dossier ---- */}
      <h2 className="text-xl font-semibold mt-8 mb-2">Sender Dossier</h2>
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          placeholder="Sender email or substring (e.g., boss@ or github.com)"
          value={senderEmail}
          onChange={(e) => setSenderEmail(e.target.value)}
          className="border p-2 rounded flex-grow"
        />
        <button className="bg-purple-600 text-white px-4 py-2 rounded" onClick={loadDossier}>
          Get Dossier
        </button>
      </div>

      {dossier && (
        <div className="border p-4 rounded shadow bg-gray-50">
          <p><b>Total Emails:</b> {dossier.total_emails}</p>
          <p><b>Average Priority:</b> {dossier.average_priority_score}</p>
          <p><b>Latest Email Summary:</b> {dossier.latest_email_summary || "N/A"}</p>
          <p><b>Most Common Action:</b> {dossier.most_common_action}</p>
          <div className="mt-2">
            <b>Category Distribution:</b>
            <ul className="list-disc list-inside">
              {Object.entries(dossier.category_counts).map(([k, v]) => (
                <li key={k}>{k}: {v}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
