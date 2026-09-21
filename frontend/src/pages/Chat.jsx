/**
 * Chat page — full-screen ChatGPT/Claude-style AI assistant.
 *
 * Features:
 * - Guest mode (limited messages, session storage)
 * - Authenticated mode (persistent MongoDB conversations)
 * - ?q= URL param for pre-seeded questions
 * - Context-aware suggested follow-up questions (dismissable / disableable)
 * - Guest-to-auth conversation migration on sign-in
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext.jsx";
import ChatLayout      from "../components/chat/ChatLayout.jsx";
import MessageList     from "../components/chat/MessageList.jsx";
import ChatComposer    from "../components/chat/ChatComposer.jsx";
import WelcomeScreen   from "../components/chat/WelcomeScreen.jsx";
import GuestLimitModal from "../components/chat/GuestLimitModal.jsx";
import * as chatService from "../services/chat.js";

let _localId = 1;
const localId = () => `local-${_localId++}`;

const GUEST_MESSAGES_KEY = "charusat_guest_messages";
const SUGGESTIONS_KEY    = "charusat_suggestions_enabled";

/* "Today at 3:41 PM"-style timestamps for messages */
function nowIso() { return new Date().toISOString(); }

function loadSuggestionsPreference() {
  try {
    return localStorage.getItem(SUGGESTIONS_KEY) !== "off";
  } catch {
    return true;
  }
}

export default function Chat() {
  const { conversationId: urlConversationId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, isGuest, isGuestLimitReached, incrementGuestCount, getGuestMessageCount, guestLimit } = useAuth();

  const [conversations,        setConversations]        = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(urlConversationId || null);
  const [messages,             setMessages]             = useState([]);
  const [isLoading,            setIsLoading]            = useState(false);
  const [showGuestLimit,       setShowGuestLimit]       = useState(false);
  const [conversationsLoaded,  setConversationsLoaded]  = useState(false);
  const [showSuggestions,      setShowSuggestions]      = useState(loadSuggestionsPreference);

  const guestMessagesRef = useRef([]);
  const autoSentRef      = useRef(false); // prevent duplicate auto-send

  const toggleSuggestions = useCallback(() => {
    setShowSuggestions((prev) => {
      const next = !prev;
      try { localStorage.setItem(SUGGESTIONS_KEY, next ? "on" : "off"); } catch {/* ignore */}
      return next;
    });
  }, []);

  // ------------------------------------------------------------------
  // Load conversations (authenticated)
  // ------------------------------------------------------------------
  useEffect(() => {
    if (isGuest || conversationsLoaded) return;
    let cancelled = false;
    chatService.getConversations()
      .then((convs) => { if (!cancelled) { setConversations(convs); setConversationsLoaded(true); } })
      .catch(() => { if (!cancelled) setConversationsLoaded(true); });
    return () => { cancelled = true; };
  }, [isGuest, conversationsLoaded]);

  // ------------------------------------------------------------------
  // Load messages for URL conversation
  // ------------------------------------------------------------------
  useEffect(() => {
    if (!urlConversationId || isGuest) return;
    setActiveConversationId(urlConversationId);
    let cancelled = false;
    chatService.getConversation(urlConversationId)
      .then((data) => {
        if (!cancelled) {
          setMessages(data.messages.map((m) => ({
            id: m.id, role: m.role, content: m.content, sources: m.sources,
            suggested_questions: m.suggested_questions || [],
            timestamp: m.created_at,
          })));
        }
      })
      .catch(console.error);
    return () => { cancelled = true; };
  }, [urlConversationId, isGuest]);

  // ------------------------------------------------------------------
  // Restore guest messages from sessionStorage
  // ------------------------------------------------------------------
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

  // ------------------------------------------------------------------
  // Migrate guest conversation after sign-in
  // ------------------------------------------------------------------
  useEffect(() => {
    if (isGuest || !user) return;
    const msgs = guestMessagesRef.current;
    if (!msgs.length) {
      try {
        const saved = sessionStorage.getItem(GUEST_MESSAGES_KEY);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed.length) { guestMessagesRef.current = parsed; migrateGuestMessages(parsed); }
        }
      } catch {/* ignore */}
      return;
    }
    migrateGuestMessages(msgs);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isGuest, user]);

  async function migrateGuestMessages(msgs) {
    try {
      const result = await chatService.migrateGuestConversation(
        msgs.map((m) => ({ role: m.role, content: m.content, sources: m.sources }))
      );
      sessionStorage.removeItem(GUEST_MESSAGES_KEY);
      guestMessagesRef.current = [];
      setActiveConversationId(result.conversation_id);
      navigate(`/chat/${result.conversation_id}`, { replace: true });
      setConversationsLoaded(false);
    } catch (err) {
      console.error("Guest migration failed:", err);
    }
  }

  // ------------------------------------------------------------------
  // ?q= pre-seeded question from landing page
  // ------------------------------------------------------------------
  useEffect(() => {
    const q = searchParams.get("q");
    if (!q || autoSentRef.current) return;
    autoSentRef.current = true;
    // Remove param from URL cleanly
    setSearchParams({}, { replace: true });
    // Short delay so the UI is ready
    setTimeout(() => { handleSend(q); }, 200);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ------------------------------------------------------------------
  // Send message
  // ------------------------------------------------------------------
  const handleSend = useCallback(async (question) => {
    if (!question || typeof question !== "string") return;
    if (isGuest && isGuestLimitReached()) { setShowGuestLimit(true); return; }

    const userMsg = { id: localId(), role: "user", content: question, timestamp: nowIso() };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await chatService.sendMessage(
        question,
        isGuest ? null : activeConversationId,
        messages,
      );

      const assistantMsg = {
        id:      response.message_id || localId(),
        role:    "assistant",
        content: response.answer,
        sources: response.sources || [],
        suggested_questions: response.suggested_questions || [],
        timestamp: nowIso(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (isGuest) {
        incrementGuestCount();
        const updated = [...messages, userMsg, assistantMsg];
        try { sessionStorage.setItem(GUEST_MESSAGES_KEY, JSON.stringify(updated)); } catch {/* ignore */}
        guestMessagesRef.current = updated;
        if (getGuestMessageCount() + 1 >= guestLimit) {
          setTimeout(() => setShowGuestLimit(true), 1500);
        }
      } else if (response.conversation_id) {
        if (!activeConversationId) {
          setActiveConversationId(response.conversation_id);
          navigate(`/chat/${response.conversation_id}`, { replace: true });
          setConversationsLoaded(false);
        }
      }
    } catch (err) {
      const errMsg = {
        id:      localId(),
        role:    "assistant",
        isError: true,
        timestamp: nowIso(),
        content:
          err.message === "Failed to fetch"
            ? "Unable to reach the assistant. Please check that the backend is running."
            : `Something went wrong. (${err.message})`,
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [
    isGuest, activeConversationId, isGuestLimitReached,
    incrementGuestCount, getGuestMessageCount, guestLimit,
    messages, navigate,
  ]);

  // ------------------------------------------------------------------
  // Retry a failed assistant message (re-sends the preceding user message)
  // ------------------------------------------------------------------
  const handleRetry = useCallback((errMsg) => {
    const idx = messages.findIndex((m) => m.id === errMsg.id);
    const lastUser = [...messages.slice(0, idx)].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    // Drop the failed assistant message and its (already present) user message is kept;
    // re-send the user's question.
    setMessages((prev) => prev.filter((m) => m.id !== errMsg.id));
    handleSend(lastUser.content);
  }, [messages, handleSend]);

  // ------------------------------------------------------------------
  // Conversation management
  // ------------------------------------------------------------------
  const handleNewChat = useCallback(() => {
    setActiveConversationId(null);
    setMessages([]);
    navigate("/chat", { replace: true });
  }, [navigate]);

  const handleSelectConversation = useCallback((id) => {
    setActiveConversationId(id);
    navigate(`/chat/${id}`);
  }, [navigate]);

  const handleDeleteConversation = useCallback(async (id) => {
    try {
      await chatService.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) handleNewChat();
    } catch (err) {
      console.error("Delete failed:", err);
    }
  }, [activeConversationId, handleNewChat]);

  const handleRenameConversation = useCallback(async (id, newTitle) => {
    try {
      const updated = await chatService.renameConversation(id, newTitle);
      setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title: updated.title } : c)));
    } catch (err) {
      console.error("Rename failed:", err);
    }
  }, []);

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------
  return (
    <>
      <ChatLayout
        conversations={conversations}
        activeConversationId={activeConversationId}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
        onToggleSuggestions={toggleSuggestions}
        suggestionsEnabled={showSuggestions}
      >
        <div className="flex h-full flex-col">
          {messages.length > 0 ? (
            <MessageList
              messages={messages}
              isLoading={isLoading}
              onSendPrompt={handleSend}
              suggestionsEnabled={showSuggestions}
              onDisableSuggestions={toggleSuggestions}
              onRetry={handleRetry}
            />
          ) : (
            <div className="flex-1 overflow-y-auto chat-scroll">
              <WelcomeScreen onSendPrompt={handleSend} />
            </div>
          )}
          <ChatComposer onSend={handleSend} disabled={isLoading} />
        </div>
      </ChatLayout>

      {showGuestLimit && <GuestLimitModal onClose={() => setShowGuestLimit(false)} />}
    </>
  );
}