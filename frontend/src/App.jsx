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
  
  // NEW: States for direct conversations
  const [directConvos, setDirectConvos] = useState(null);
  const [rawSenderEmail, setRawSenderEmail] = useState("");

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
    setDirectConvos(null);
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
    if (!senderEmail) return setMsg("Enter a sender name or email.");
    setLoading(true);
    setMsg("Loading sender dossier...");
    try {
      const res = await axios.get(
        `${API_BASE}/dossier/${encodeURIComponent(userEmail)}?search_query=${encodeURIComponent(senderEmail)}`
      );
      setDossier(res.data);
      setMsg("Dossier loaded.");
    } catch (e) {
      console.error(e);
      setDossier(null);
      setMsg("No emails found. Make sure you've fetched & processed emails first.");
    } finally {
      setLoading(false);
    }
  };

  // NEW: Direct conversations function - FIXED PARAMETER
  const fetchDirectConversations = async () => {
    if (!userEmail) return setMsg("Please login first.");
    if (!rawSenderEmail) return setMsg("Enter sender name or email.");
    
    setLoading(true);
    setMsg("Fetching direct conversations from Gmail...");
    try {
      const res = await axios.get(
        `${API_BASE}/gmail/direct-conversations/${encodeURIComponent(userEmail)}?search_query=${encodeURIComponent(rawSenderEmail)}&max_results=30`
      );
      setDirectConvos(res.data);
      setMsg(`Fetched ${res.data.total_conversations} direct conversations.`);
    } catch (e) {
      console.error(e);
      setDirectConvos(null);
      setMsg("Failed to fetch direct conversations.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
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
          placeholder="Search by name or email (e.g., 'Pavan' or 'pavan@gmail.com')"
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <p><b>Total Emails:</b> {dossier.total_emails}</p>
              <p><b>Period Covered:</b> {dossier.period_covered || "Last 6 months"}</p>
              <p><b>Average Priority:</b> {dossier.average_priority_score}</p>
            </div>
            <div>
              <p><b>Latest Email Summary:</b> {dossier.latest_email_summary || "N/A"}</p>
              <p><b>Most Common Action:</b> {dossier.most_common_action}</p>
            </div>
          </div>
          
          <div className="mt-2">
            <b>Category Distribution:</b>
            <ul className="list-disc list-inside">
              {Object.entries(dossier.category_counts || {}).map(([k, v]) => (
                <li key={k}>{k}: {v}</li>
              ))}
            </ul>
          </div>

          {/* Conversation History */}
          <div className="mt-6">
            <b>Conversation History (Last 6 months):</b>
            <div className="mt-2 space-y-3 max-h-96 overflow-y-auto">
              {dossier.conversation_history && dossier.conversation_history.length > 0 ? (
                dossier.conversation_history.map((message, index) => (
                  <div key={index} className="border-l-4 border-blue-400 pl-3 py-2 bg-white rounded">
                    <div className="flex justify-between items-start">
                      <span className="font-medium text-sm">{message.subject || "No Subject"}</span>
                      <span className="text-xs text-gray-500">
                        {message.received_at ? new Date(message.received_at).toLocaleDateString() : 'No date'}
                      </span>
                    </div>
                    {message.summary && (
                      <p className="text-sm text-gray-700 mt-1">{message.summary}</p>
                    )}
                    {message.suggested_action && message.suggested_action !== "None" && (
                      <span className="inline-block mt-1 px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded">
                        {message.suggested_action}
                      </span>
                    )}
                  </div>
                ))
              ) : (
                <p className="text-gray-500">No conversation history found</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* NEW: Direct Gmail Conversations Section */}
      <div className="mt-8 p-4 border rounded-lg bg-blue-50">
        <h2 className="text-xl font-semibold mb-3">🚀 Direct Gmail Conversations</h2>
        <p className="text-sm text-gray-600 mb-3">Fetch RAW email threads directly from Gmail (includes your replies)</p>
        
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            placeholder="Search by name or email (e.g., 'Pavan' or 'pavan@gmail.com')"
            value={rawSenderEmail}
            onChange={(e) => setRawSenderEmail(e.target.value)}
            className="border p-2 rounded flex-grow"
          />
          <button 
            className="bg-blue-600 text-white px-4 py-2 rounded"
            onClick={fetchDirectConversations}
          >
            Fetch Direct
          </button>
        </div>

        {directConvos && (
          <div className="mt-4">
            <h3 className="font-semibold">Conversations with {directConvos.search_query}</h3>
            <p>Found {directConvos.total_conversations} emails in last 6 months</p>
            
            <div className="mt-3 space-y-3 max-h-96 overflow-y-auto">
              {directConvos.conversations.map((email, index) => (
                <div key={index} className={`p-3 rounded border-l-4 ${
                  email.direction === 'outgoing' ? 'border-green-400 bg-green-50' : 'border-blue-400 bg-white'
                }`}>
                  <div className="flex justify-between items-start">
                    <span className="font-medium">{email.subject || "No Subject"}</span>
                    <span className="text-xs text-gray-500">
                      {email.received_at ? new Date(email.received_at).toLocaleDateString() : 'No date'}
                      {email.direction === 'outgoing' && ' (You)'}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 mt-1">
                    {email.body?.substring(0, 200)}...
                  </p>
                  <span className="text-xs text-gray-500 block mt-1">
                    From: {email.sender}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;