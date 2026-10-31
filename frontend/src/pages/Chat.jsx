/**
 * Chat page - full-screen ChatGPT/Claude-style AI assistant.
 * Powered by useChat and useSidebar hooks.
 */
import { useCallback, useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import ChatLayout from "../components/chat/ChatLayout.jsx";
import MessageList from "../components/chat/MessageList.jsx";
import ChatComposer from "../components/chat/ChatComposer.jsx";
import WelcomeScreen from "../components/chat/WelcomeScreen.jsx";
import GuestLimitModal from "../components/chat/GuestLimitModal.jsx";
import { useChat } from "../hooks/useChat.js";
import { useSidebar } from "../hooks/useSidebar.js";
import { loadQuestionBank } from "../lib/questionBank.js";

const TYPING_SUGGESTIONS_KEY = "charusat_typing_suggestions";

function loadTypingSuggestionsPreference() {
  try {
    return localStorage.getItem(TYPING_SUGGESTIONS_KEY) !== "off";
  } catch {
    return true;
  }
}

export default function Chat() {
  const navigate = useNavigate();
  const {
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
  } = useChat();

  const handleSelectConversation = useCallback(
    (id) => {
      setActiveConversationId(id);
      navigate(`/chat/${id}`);
    },
    [navigate, setActiveConversationId]
  );

  const {
    conversations,
    deleteConversation,
    renameConversation,
  } = useSidebar({
    activeConversationId,
    onSelectConversation: handleSelectConversation,
    onNewChat: clearChat,
  });

  const [typingSuggestionsEnabled, setTypingSuggestionsEnabled] = useState(
    loadTypingSuggestionsPreference
  );
  const [questionBank, setQuestionBank] = useState([]);

  useEffect(() => {
    let cancelled = false;
    loadQuestionBank().then((data) => {
      if (!cancelled && data) setQuestionBank(data);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleTypingSuggestions = useCallback(() => {
    setTypingSuggestionsEnabled((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(TYPING_SUGGESTIONS_KEY, next ? "on" : "off");
      } catch {/* ignore */}
      return next;
    });
  }, []);

  // Detect currently discussed programme from messages
  const currentProgramme = useMemo(() => {
    return messages.reduceRight((found, m) => {
      if (found) return found;
      const c = m.content?.toLowerCase() || "";
      if (/\b(bba|online bba)\b/.test(c)) return "bba";
      if (/\b(bca|online bca)\b/.test(c)) return "bca";
      if (/\b(mba|online mba)\b/.test(c)) return "mba";
      if (/\b(mca|online mca)\b/.test(c)) return "mca";
      return null;
    }, null);
  }, [messages]);

  return (
    <>
      <ChatLayout
        conversations={conversations}
        activeConversationId={activeConversationId}
        onNewChat={clearChat}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={deleteConversation}
        onRenameConversation={renameConversation}
        typingSuggestionsEnabled={typingSuggestionsEnabled}
        onToggleTypingSuggestions={toggleTypingSuggestions}
      >
        <div className="flex h-full flex-col">
          {messages.length > 0 ? (
            <MessageList
              messages={messages}
              isLoading={isLoading}
              thinkingStatus={thinkingStatus}
              onRetry={retryMessage}
              onRegenerate={regenerateLastMessage}
              onSuggestedQuestion={sendMessage}
            />
          ) : (
            <div className="flex-1 overflow-y-auto chat-scroll">
              <WelcomeScreen onSendPrompt={sendMessage} questionBank={questionBank} />
            </div>
          )}
          {showColdStart && (
            <div
              role="status"
              aria-live="polite"
              className="mx-auto max-w-3xl px-4 py-2 sm:px-6"
            >
              <p className="rounded-lg border px-3.5 py-2.5 text-xs leading-relaxed" style={{ borderColor: "var(--border)", background: "var(--surface)", color: "var(--muted)" }}>
                The assistant is starting up -- this may take up to 30 seconds on first load. Please wait.
              </p>
            </div>
          )}
          <ChatComposer
            onSend={sendMessage}
            onStop={stop}
            disabled={isLoading}
            typingSuggestionsEnabled={typingSuggestionsEnabled}
            currentProgramme={currentProgramme}
            questionBank={questionBank}
            conversationId={activeConversationId}
            history={messages.slice(-4).map((m) => ({ role: m.role, content: m.content }))}
          />
        </div>
      </ChatLayout>

      {showGuestLimit && <GuestLimitModal onClose={() => setShowGuestLimit(false)} />}
    </>
  );
}