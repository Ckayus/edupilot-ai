
import { useEffect, useState } from "react";
import {
  askTutor,
  getConversations,
  getConversation,
  getToken,
  logout,
} from "./services/api";
import AuthForm from "./components/AuthForm";
import "./App.css";

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    Boolean(getToken())
  );
  const [question, setQuestion] = useState("");
  const [subject, setSubject] = useState("Auto-detect");
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState("");

  function handleLogout() {
    logout();
    setIsAuthenticated(false);
    setConversations([]);
    setMessages([]);
    setConversationId(null);
    setQuestion("");
    setError("");
  }

  async function refreshConversations() {
    const data = await getConversations();
    setConversations(data);
  }

  useEffect(() => {
    if (!isAuthenticated) return;
  
    refreshConversations().catch(() => {
      setError("Could not load saved conversations.");
    });
  }, [isAuthenticated]);

  function startNewChat() {
    setConversationId(null);
    setMessages([]);
    setQuestion("");
    setError("");
  }

  async function openConversation(id) {
    setSubject(data.conversation.subject || "Auto-detect");
    if (loading || historyLoading) return;

    setHistoryLoading(true);
    setError("");

    try {
      const data = await getConversation(id);

      setConversationId(data.conversation.id);
      setMessages(
        data.messages.map((message) => ({
          role: message.role === "user" ? "student" : "tutor",
          content: message.content,
        }))
      );
      setQuestion("");
    } catch {
      setError("Could not open this conversation.");
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const text = question.trim();

    if (!text || loading || historyLoading) return;

    setMessages((previous) => [
      ...previous,
      { role: "student", content: text },
    ]);

    setQuestion("");
    setLoading(true);
    setError("");

    try {
      const data = await askTutor(
        text,
        "Python",
        conversationId
      );

      setConversationId(data.conversation_id);

      setMessages((previous) => [
        ...previous,
        { role: "tutor", content: data.answer },
      ]);

      await refreshConversations();
    } catch {
      setError(
        "Could not reach the tutor. Check that FastAPI and Ollama are running."
      );
    } finally {
      setLoading(false);
    }
  }

  if (!isAuthenticated) {
    return (
      <AuthForm
        onLogin={() => setIsAuthenticated(true)}
      />
    );
  }
  
  return (
      <main className="app">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-icon">E</div>
          <h2>EduPilot AI</h2>
        </div>

        <button
          className="new-chat-button"
          type="button"
          onClick={startNewChat}
          disabled={loading || historyLoading}
        >
          + New conversation
        </button>

        <h3 className="history-heading">Your conversations</h3>

        <div className="conversation-list">
          {conversations.length === 0 && (
            <p className="history-empty">
              Your saved chats will appear here.
            </p>
          )}

          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              type="button"
              className={`conversation-item ${
                conversation.id === conversationId
                  ? "active"
                  : ""
              }`}
              onClick={() => openConversation(conversation.id)}
              disabled={loading || historyLoading}
            >
              <span>{conversation.title}</span>
              {/* <small>{conversation.subject}</small> */}
            </button>
          ))}
        </div>
      </aside>

      <section className="tutor">
      
<header className="header">
  <div>
    <h1>EduPilot AI</h1>
    <p>Your personal learning companion</p>
  </div>

  <button
    type="button"
    onClick={handleLogout}
    disabled={loading || historyLoading}
  >
    Log out
  </button>
</header>


        <div className="welcome">
          <span className="subject">SUBJECT TUTOR</span>
          <h2>What would you like to learn today?</h2>
          <p>
            Ask questions, explore concepts, and practise
            your difficult subject.
          </p>
        </div>

        <div className="messages">
          {historyLoading && (
            <p className="loading">Loading conversation...</p>
          )}

          {messages.length === 0 && !historyLoading && (
            <div className="empty-state">
              <h3>Start learning</h3>
              <p>
                Try asking: What is a Python iterator?
              </p>
              <button
                type="button"
                onClick={() =>
                  setQuestion("What is a Python iterator?")
                }
              >
                Try an example
              </button>
            </div>
          )}

          {messages.map((message, index) => (
            <div
              key={index}
              className={`message ${message.role}`}
            >
              <strong>
                {message.role === "student"
                  ? "You"
                  : "EduPilot AI"}
              </strong>
              <p>{message.content}</p>
            </div>
          ))}

          {loading && (
            <p className="loading">Tutor is thinking...</p>
          )}

          {error && <p className="error">{error}</p>}
        </div>

        <form className="chat-form" onSubmit={handleSubmit}>
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask your Python tutor..."
            rows={2}
            maxLength={2000}
            required
          />

          <button
            type="submit"
            disabled={
              loading || historyLoading || !question.trim()
            }
          >
            {loading ? "Sending..." : "Ask tutor"}
          </button>
        </form>

        <p className="disclaimer">
          Conversations are saved locally in your database.
        </p>
      </section>
    </main>
  );
}

export default App;
