
const API_URL = "http://127.0.0.1:8000";

export function saveToken(token) {
  localStorage.setItem("edupilot_token", token);
}

export function getToken() {
  return localStorage.getItem("edupilot_token");
}

export function logout() {
  localStorage.removeItem("edupilot_token");
}

async function apiRequest(path, options = {}) {
  const token = getToken();

  const headers = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || `Request failed: ${response.status}`);
  }

  return data;
}

export function registerStudent(email, password) {
  return apiRequest("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function loginStudent(email, password) {
  const data = await apiRequest("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  saveToken(data.access_token);
  return data;
}

export function askTutor(question, subject = "Python", conversationId = null) {
  return apiRequest("/api/tutor/chat", {
    method: "POST",
    body: JSON.stringify({
      question,
      subject,
      conversation_id: conversationId,
    }),
  });
}

export function getConversations() {
  return apiRequest("/api/conversations");
}

export function getConversation(conversationId) {
  return apiRequest(
    `/api/conversations/${encodeURIComponent(conversationId)}`
  );
}
