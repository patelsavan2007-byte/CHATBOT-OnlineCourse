/**
 * useChat -- custom hook for chat message lifecycle, sending, abort, retry, and regeneration.
 *
 * Key fixes vs prior version:
 *  - F1: receivedChunk was undeclared; replaced with receivedAnswer (bool).
 *  - F32: thinkingTimer re-called setIsLoading(true) on a no-op; now shows a
 *         cold-start banner after COLD_START_MS of silence.
 *  - AbortController: sendMessage wires a controller so stop() cancels in-flight
 *    SSE streams. The composer gets a Stop button while isLoading.
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

/** How long (ms) to wait with no response before showing the cold-start banner. */
const COLD_START_MS = 5000;

export function useChat() {
  const { conversationId: urlConversationId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, isGuest, isGuestLimitReached, incrementGuestCount, getGuestMessageCount, guestLimit } = useAuth();

  const [activeConversationId, setActiveConversationId] = useState(urlConversationId || null);
  const [messages, setMessages]       = useState([]);
  const [isLoading, setIsLoading]     = useState(false);
  const [thinkingStatus, setThinkingStatus] = useState(DEFAULT_THINKING_MESSAGE);
  const [showColdStart, setShowColdStart]   = useState(false);
  const [showGuestLimit, setShowGuestLimit] = useState(false);

  const guestMessagesRef = useRef([]);
  const autoSentRef      = useRef(false);
  const abortRef         = useRef(null); // holds current AbortController

  // ----------------------------------------------------------------
  // 1. Load messages for existing authenticated conversation
  // ----------------------------------------------------------------
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
              sources: m.sources || [],
            }))
          );
        }
      })
      .catch(console.error);
    return () => { cancelled = true; };
  }, [urlConversationId, isGuest]);

  // ----------------------------------------------------------------
  // 2. Restore guest messages from sessionStorage
  // ----------------------------------------------------------------
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

  // ----------------------------------------------------------------
  // 3. Migrate guest conversation on auth
  // ----------------------------------------------------------------
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

  // ----------------------------------------------------------------
  // 4. Stop any in-flight request
  // ----------------------------------------------------------------
  const stop = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsLoading(false);
    setShowColdStart(false);
    setThinkingStatus(DEFAULT_THINKING_MESSAGE);
  }, []);

  // ----------------------------------------------------------------
  // 5. Send Message
  // ----------------------------------------------------------------
  const sendMessage = useCallback(
    async (question) => {
      if (!question || typeof question !== "string") return;
      if (isGuest && isGuestLimitReached()) {
        setShowGuestLimit(true);
        return;
      }

      // Cancel any previous in-flight request
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const userMsg = { id: localId(), role: "user", content: question, timestamp: nowIso() };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setShowColdStart(false);
      setThinkingStatus(DEFAULT_THINKING_MESSAGE);

      // Cold-start banner: if there is no response at all after COLD_START_MS,
      // tell the user the backend is waking up (Render free-plan cold start).
      let coldTimer = setTimeout(() => {
        setShowColdStart(true);
      }, COLD_START_MS);

      // Track whether we ever received content so the non-stream fallback knows
      // whether to throw (F1 fix: receivedAnswer replaces undeclared receivedChunk).
      let receivedAnswer = false;

      const appendChunk = () => {
        if (coldTimer) {
          clearTimeout(coldTimer);
          coldTimer = null;
          setShowColdStart(false);
        }
        receivedAnswer = true;
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
              onThinking: (msg) => setThinkingStatus(msg || DEFAULT_THINKING_MESSAGE),
              onChunk: appendChunk,
              signal: controller.signal,
            }
          );
        } catch (streamErr) {
          // If the stream was explicitly aborted, stop cleanly.
          if (streamErr?.name === "AbortError") {
            clearTimeout(coldTimer);
            setIsLoading(false);
            setShowColdStart(false);
            return;
          }
          // Fall back to the non-streaming endpoint only if we have not yet
          // rendered any incremental content (F1 fix: was undeclared receivedChunk).
          if (receivedAnswer) throw streamErr;
          response = await chatService.sendMessage(
            question,
            isGuest ? null : activeConversationId,
            messages,
            { signal: controller.signal }
          );
        }

        if (controller.signal.aborted) {
          clearTimeout(coldTimer);
          return;
        }

        clearTimeout(coldTimer);
        setShowColdStart(false);
        setIsLoading(false);

        const finalContent = response.answer ?? "";
        const assistantMsg = {
          id: response.message_id || localId(),
          role: "assistant",
          content: finalContent,
          timestamp: nowIso(),
          sources: response.sources || [],
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
        if (err?.name === "AbortError") return; // user hit Stop, silently exit
        clearTimeout(coldTimer);
        setShowColdStart(false);
        setIsLoading(false);
        const errMsg = {
          id:      localId(),
          role:    "assistant",
          isError: true,
          content: err.isNetworkError
            ? "Unable to reach the assistant. Please check your internet connection or try again in a moment."
            : `Something went wrong. (${err.message})`,
        };
        setMessages((prev) => [...prev, errMsg]);
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        clearTimeout(coldTimer);
        setIsLoading(false);
        setShowColdStart(false);
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

  // ----------------------------------------------------------------
  // 6. Pre-seeded query param (?q=)
  // ----------------------------------------------------------------
  useEffect(() => {
    const q = searchParams.get("q");
    if (!q || autoSentRef.current) return;
    autoSentRef.current = true;
    setSearchParams({}, { replace: true });
    setTimeout(() => { sendMessage(q); }, 200);
  }, [searchParams, setSearchParams, sendMessage]);

  // ----------------------------------------------------------------
  // 7. Retry
  // ----------------------------------------------------------------
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

  // ----------------------------------------------------------------
  // 8. Regenerate (re-send last user question)
  // ----------------------------------------------------------------
  const regenerateLastMessage = useCallback(() => {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    const lastMsg = messages[messages.length - 1];
    if (lastMsg && lastMsg.role === "assistant") {
      setMessages((prev) => prev.slice(0, -1));
    }
    sendMessage(lastUser.content);
  }, [messages, sendMessage]);

  // ----------------------------------------------------------------
  // 9. Clear chat
  // ----------------------------------------------------------------
  const clearChat = useCallback(() => {
    stop();
    setActiveConversationId(null);
    setMessages([]);
    guestMessagesRef.current = [];
    setThinkingStatus(DEFAULT_THINKING_MESSAGE);
    try {
      sessionStorage.removeItem(GUEST_MESSAGES_KEY);
    } catch {/* ignore */}
    navigate("/chat", { replace: true });
  }, [navigate, stop]);

  return {
    messages,
    isLoading,
    thinkingStatus,
    showColdStart,
    activeConversationId,
    setActiveConversationId,
    showGuestLimit,
    setShowGuestLimit,
    sendMessage,
    stop,
    retryMessage,
    regenerateLastMessage,
    clearChat,
  };
}
