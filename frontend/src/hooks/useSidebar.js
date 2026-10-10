/**
 * useSidebar — hook managing conversations list, active state,
 * sidebar desktop toggle (with localStorage persistence), and mobile drawer.
 */
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext.jsx";
import * as chatService from "../services/chat.js";

const SIDEBAR_STORAGE_KEY = "charusat_sidebar_open";

export function useSidebar({ activeConversationId, onSelectConversation, onNewChat }) {
  const { isGuest, user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [conversationsLoaded, setConversationsLoaded] = useState(false);

  // Load conversations for authenticated user
  useEffect(() => {
    if (isGuest || !user) {
      setConversations([]);
      setConversationsLoaded(true);
      return;
    }
    let cancelled = false;
    chatService.listConversations()
      .then((data) => {
        if (!cancelled) {
          const list = Array.isArray(data) ? data : data?.conversations || [];
          setConversations(list);
        }
      })
      .catch((err) => console.error("Failed to load conversations:", err))
      .finally(() => {
        if (!cancelled) setConversationsLoaded(true);
      });

    return () => { cancelled = true; };
  }, [isGuest, user, activeConversationId]);

  const deleteConversation = useCallback(
    async (id) => {
      try {
        await chatService.deleteConversation(id);
        setConversations((prev) => prev.filter((c) => c.id !== id));
        if (activeConversationId === id) onNewChat?.();
      } catch (err) {
        console.error("Delete conversation failed:", err);
      }
    },
    [activeConversationId, onNewChat]
  );

  const renameConversation = useCallback(async (id, newTitle) => {
    try {
      const updated = await chatService.renameConversation(id, newTitle);
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: updated.title } : c))
      );
    } catch (err) {
      console.error("Rename conversation failed:", err);
    }
  }, []);

  return {
    conversations,
    conversationsLoaded,
    deleteConversation,
    renameConversation,
  };
}
