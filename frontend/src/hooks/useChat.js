/**
 * useChat — custom hook for chat message lifecycle, sending, retry, and regeneration.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext.jsx";
import * as chatService from "../services/chat.js";
import { DEFAULT_THINKING_MESSAGE } from "../config/branding.js";

let _localId = 1;
const localId = () => `local-${_localId++}`;
const GUEST_MESSAGES_KEY = "charusat_guest_messages";
function nowIso() { return new Date().toISOString(); }

export function useChat() {
  const { conversationId: urlConversationId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, isGuest, isGuestLimitReached, incrementGuestCount, getGuestMessageCount, guestLimit } = useAuth();

  const [activeConversationId, setActiveConversationId] = useState(urlConversationId || null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingStatus, setThinkingStatus] = useState(DEFAULT_THINKING_MESSAGE);
  const [showGuestLimit, setShowGuestLimit] = useState(false);

  const guestMessagesRef = useRef([]);
  const autoSentRef = useRef(false);

  // 1. Load messages for existing authenticated conversation
  useEffect(() => {
    if (!urlConversationId || isGuest) return;
    setActiveConversationId(urlConversationId);
    let cancelled = false;
    chatService.getConversation(urlConversationId)
      .then((data) => {
        if (!cancelled && data?.messages) {
          setMessages(
            data.messages.map((m) => ({
              id: m.id,
              role: m.role,
              content: m.content,
              timestamp: m.created_at,
            }))
          );
        }
      })
      .catch(console.error);
    return () => { cancelled = true; };
  }, [urlConversationId, isGuest]);

  // 2. Restore guest messages from sessionStorage
  useEffect(() => {
    if (!isGuest) return;
    try {
      const saved = sessionStorage.getItem(GUEST_MESSAGES_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        setMessages(parsed);
        guestMessagesRef.current = parsed;
      }
    } catch {/* ignore */}
  }, [isGuest]);

  // 3. Migrate guest conversation on auth
  useEffect(() => {
    if (isGuest || !user) return;
    const msgs = guestMessagesRef.current;
    if (!msgs.length) {
      try {
        const saved = sessionStorage.getItem(GUEST_MESSAGES_KEY);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed.length) {
            guestMessagesRef.current = parsed;
            migrateGuest(parsed);
          }
        }
      } catch {/* ignore */}
      return;
    }
    migrateGuest(msgs);

    async function migrateGuest(mList) {
      try {
        const res = await chatService.migrateGuestConversation(
          mList.map((m) => ({ role: m.role, content: m.content }))
        );
        sessionStorage.removeItem(GUEST_MESSAGES_KEY);
        guestMessagesRef.current = [];
        setActiveConversationId(res.conversation_id);
        navigate(`/chat/${res.conversation_id}`, { replace: true });
      } catch (err) {
        console.error("Guest migration failed:", err);
      }
    }
  }, [isGuest, user, navigate]);

  // 4. Send Message
  const sendMessage = useCallback(
    async (question) => {
      if (!question || typeof question !== "string") return;
      if (isGuest && isGuestLimitReached()) {
        setShowGuestLimit(true);
        return;
      }

      const userMsg = { id: localId(), role: "user", content: question, timestamp: nowIso() };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setThinkingStatus(DEFAULT_THINKING_MESSAGE);

      const assistantId = localId();
      let finalContent = "";
      let receivedAnswer = false;
      let thinkingTimer = null;
      thinkingTimer = setTimeout(() => {
        setIsLoading(true);
      }, 400);

      const appendChunk = (chunk) => {
        // Classic mode: we still accept chunks but will render full answer at end
        if (thinkingTimer) {
          clearTimeout(thinkingTimer);
          thinkingTimer = null;
        }
        setIsLoading(false);
      };

      try {
        let response;
        try {
          response = await chatService.streamMessage(
            question,
            isGuest ? null : activeConversationId,
            messages,
            {
              onThinking: (message) => setThinkingStatus(message || DEFAULT_THINKING_MESSAGE),
              onChunk: appendChunk,
            }
          );
        } catch (streamErr) {
          // Fall back to the non-streaming endpoint only if nothing rendered yet.
          if (receivedChunk) throw streamErr;
          response = await chatService.sendMessage(
            question,
            isGuest ? null : activeConversationId,
            messages
          );
        }

        if (thinkingTimer) {
          clearTimeout(thinkingTimer);
          thinkingTimer = null;
        }
        setIsLoading(false);
        const finalContentAnswer = response.answer ?? "";
        const assistantMsg = {
          id: response.message_id || assistantId,
          role: "assistant",
          content: finalContentAnswer,
          timestamp: nowIso(),
          suggestedQuestions: response.suggested_questions || [],
          quickReplies: response.quick_replies || [],
          isStreaming: false,
        };
        setMessages((prev) => [...prev, assistantMsg]);

        if (isGuest) {
          incrementGuestCount();
          const updated = [...messages, userMsg, assistantMsg];
          try {
            sessionStorage.setItem(GUEST_MESSAGES_KEY, JSON.stringify(updated));
          } catch {/* ignore */}
          guestMessagesRef.current = updated;
          if (getGuestMessageCount() + 1 >= guestLimit) {
            setTimeout(() => setShowGuestLimit(true), 1500);
          }
        } else if (response.conversation_id && !activeConversationId) {
          setActiveConversationId(response.conversation_id);
          navigate(`/chat/${response.conversation_id}`, { replace: true });
        }
      } catch (err) {
        if (thinkingTimer) {
          clearTimeout(thinkingTimer);
          thinkingTimer = null;
        }
        setIsLoading(false);
        const errMsg = {
          id: localId(),
          role: "assistant",
          isError: true,
          content: err.isNetworkError
            ? "Unable to reach the assistant. Please check that the backend is running."
            : `Something went wrong. (${err.message})`,
        };
        setMessages((prev) => [...prev, errMsg]);
      } finally {
        if (thinkingTimer) {
          clearTimeout(thinkingTimer);
          thinkingTimer = null;
        }
        setIsLoading(false);
        setThinkingStatus(DEFAULT_THINKING_MESSAGE);
      }
    },
    [
      isGuest,
      activeConversationId,
      isGuestLimitReached,
      incrementGuestCount,
      getGuestMessageCount,
      guestLimit,
      messages,
      navigate,
    ]
  );

  // 5. Pre-seeded query param (?q=)
  useEffect(() => {
    const q = searchParams.get("q");
    if (!q || autoSentRef.current) return;
    autoSentRef.current = true;
    setSearchParams({}, { replace: true });
    setTimeout(() => { sendMessage(q); }, 200);
  }, [searchParams, setSearchParams, sendMessage]);

  // 6. Retry
  const retryMessage = useCallback(
    (errMsg) => {
      const idx = messages.findIndex((m) => m.id === errMsg.id);
      const lastUser = [...messages.slice(0, idx)].reverse().find((m) => m.role === "user");
      if (!lastUser) return;
      setMessages((prev) => prev.filter((m) => m.id !== errMsg.id));
      sendMessage(lastUser.content);
    },
    [messages, sendMessage]
  );

  // 7. Regenerate (re-send last user question)
  const regenerateLastMessage = useCallback(() => {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    // Remove last assistant message
    const lastMsg = messages[messages.length - 1];
    if (lastMsg && lastMsg.role === "assistant") {
      setMessages((prev) => prev.slice(0, -1));
    }
    sendMessage(lastUser.content);
  }, [messages, sendMessage]);

  const clearChat = useCallback(() => {
    setActiveConversationId(null);
    setMessages([]);
    guestMessagesRef.current = [];
    setThinkingStatus(DEFAULT_THINKING_MESSAGE);
    try {
      sessionStorage.removeItem(GUEST_MESSAGES_KEY);
    } catch {/* ignore */}
    navigate("/chat", { replace: true });
  }, [navigate]);

  return {
    messages,
    isLoading,
    thinkingStatus,
    activeConversationId,
    setActiveConversationId,
    showGuestLimit,
    setShowGuestLimit,
    sendMessage,
    retryMessage,
    regenerateLastMessage,
    clearChat,
  };
}
