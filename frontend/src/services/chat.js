/**
 * Chat service — handles conversations, messages, and chat API calls.
 */
import API_BASE, { apiFetch, getAuthToken } from "./api.js";

function buildChatBody(question, conversationId, history) {
  const body = { question };
  if (conversationId) body.conversation_id = conversationId;
  if (history && history.length) {
    body.history = history.slice(-20).map(({ role, content }) => ({ role, content }));
  }
  return body;
}

/**
 * Send a chat message through the enhanced API endpoint.
 * Works for both guests (no conversationId) and authenticated users.
 * `history` is the recent local message list used for smarter suggestions.
 */
export async function sendMessage(question, conversationId = null, history = null) {
  return apiFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify(buildChatBody(question, conversationId, history)),
  });
}

/**
 * Stream a chat reply over Server-Sent Events.
 * Calls onThinking(message) while the backend is working and onChunk(text)
 * for every progressive piece of the answer. Resolves with the final payload.
 */
export async function streamMessage(
  question,
  conversationId = null,
  history = null,
  { onThinking, onChunk, signal } = {}
) {
  const headers = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  };
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify(buildChatBody(question, conversationId, history)),
      signal,
    });
  } catch (netErr) {
    const error = new Error("Unable to connect to the server. Please verify your connection.");
    error.isNetworkError = true;
    error.originalError = netErr;
    throw error;
  }

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* keep default */
    }
    const error = new Error(message);
    error.status = res.status;
    throw error;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    return sendMessage(question, conversationId, history);
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let finalPayload = null;

  const handleBlock = (block) => {
    const dataLines = block
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart());
    if (!dataLines.length) return;

    let event;
    try {
      event = JSON.parse(dataLines.join("\n"));
    } catch {
      return;
    }

    if (event.type === "chunk" && event.content) {
      onChunk?.(event.content);
    } else if (event.type === "typing") {
      onThinking?.(event.message || "Thinking…");
    } else if (event.type === "error") {
      const error = new Error(event.message || "Failed to generate answer");
      error.isStreamError = true;
      throw error;
    } else if (event.type === "done") {
      finalPayload = event;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      handleBlock(block);
      boundary = buffer.indexOf("\n\n");
    }
  }
  if (buffer.trim()) handleBlock(buffer);

  if (!finalPayload) {
    throw new Error("The assistant stopped before finishing. Please try again.");
  }
  return finalPayload;
}

/**
 * Get all conversations for the current user.
 */
export async function getConversations() {
  const data = await apiFetch("/api/conversations");
  return data.conversations;
}

export const listConversations = getConversations;

/**
 * Get a single conversation with all its messages.
 */
export async function getConversation(conversationId) {
  return apiFetch(`/api/conversations/${conversationId}`);
}

/**
 * Create a new conversation.
 */
export async function createConversation(title = "New Chat") {
  const data = await apiFetch("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
  return data.conversation;
}

/**
 * Rename a conversation.
 */
export async function renameConversation(conversationId, title) {
  const data = await apiFetch(`/api/conversations/${conversationId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
  return data.conversation;
}

/**
 * Delete a conversation.
 */
export async function deleteConversation(conversationId) {
  return apiFetch(`/api/conversations/${conversationId}`, {
    method: "DELETE",
  });
}

/**
 * Migrate guest conversation to authenticated user's account.
 */
export async function migrateGuestConversation(messages, title = null) {
  return apiFetch("/api/chat/migrate", {
    method: "POST",
    body: JSON.stringify({ messages, title }),
  });
}
