/**
 * Chat service — handles conversations, messages, and chat API calls.
 */
import { apiFetch } from "./api.js";

/**
 * Send a chat message through the enhanced API endpoint.
 * Works for both guests (no conversationId) and authenticated users.
 * `history` is the recent local message list used for smarter suggestions.
 */
export async function sendMessage(question, conversationId = null, history = null) {
  const body = { question };
  if (conversationId) body.conversation_id = conversationId;
  if (history && history.length) {
    body.history = history.slice(-8).map(({ role, content }) => ({ role, content }));
  }

  return apiFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/**
 * Get all conversations for the current user.
 */
export async function getConversations() {
  const data = await apiFetch("/api/conversations");
  return data.conversations;
}

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
