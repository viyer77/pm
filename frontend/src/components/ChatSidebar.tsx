"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type ChatSidebarProps = {
  onBoardChanged: () => void;
};

export const ChatSidebar = ({ onBoardChanged }: ChatSidebarProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = {
      id: `${Date.now()}-user`,
      role: "user",
      content: text,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await api.chatAI(text);
      setMessages((prev) => [
        ...prev,
        { id: `${Date.now()}-ai`, role: "assistant", content: res.response },
      ]);
      if (res.actions_executed > 0) {
        onBoardChanged();
      }
    } catch {
      setError("Failed to get a response. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    try {
      await api.clearChatAI();
    } catch {
      // best-effort
    }
    setMessages([]);
    setError(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  return (
    <aside className="w-[360px] flex-shrink-0 border-l border-[var(--stroke)] bg-white flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--stroke)]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
            AI Assistant
          </p>
          <p className="text-sm font-semibold text-[var(--navy-dark)] mt-0.5">
            Kanban Studio
          </p>
        </div>
        <button
          onClick={() => void handleClear()}
          className="text-xs text-[var(--gray-text)] hover:text-[var(--navy-dark)] transition"
          aria-label="Clear conversation"
        >
          Clear
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.length === 0 && !loading && (
          <p className="text-xs text-[var(--gray-text)] text-center mt-8 leading-relaxed px-4">
            Ask the AI to create, move, update, or delete cards on your board.
          </p>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-[var(--secondary-purple)] text-white rounded-tr-sm"
                  : "bg-[var(--surface)] text-[var(--navy-dark)] border border-[var(--stroke)] rounded-tl-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-[var(--surface)] border border-[var(--stroke)] rounded-2xl rounded-tl-sm px-4 py-3">
              <span className="flex gap-1.5 items-center">
                <span
                  className="h-1.5 w-1.5 rounded-full bg-[var(--gray-text)] animate-bounce"
                  style={{ animationDelay: "0ms" }}
                />
                <span
                  className="h-1.5 w-1.5 rounded-full bg-[var(--gray-text)] animate-bounce"
                  style={{ animationDelay: "150ms" }}
                />
                <span
                  className="h-1.5 w-1.5 rounded-full bg-[var(--gray-text)] animate-bounce"
                  style={{ animationDelay: "300ms" }}
                />
              </span>
            </div>
          </div>
        )}

        {error && (
          <p className="text-xs text-red-600 text-center px-2">{error}</p>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-4 border-t border-[var(--stroke)]">
        <div className="flex gap-2 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask the AI anything about your board..."
            disabled={loading}
            rows={2}
            className="flex-1 resize-none rounded-xl border-2 border-[var(--stroke)] px-3 py-2 text-sm text-[var(--navy-dark)] placeholder:text-[var(--gray-text)] focus:outline-none focus:border-[var(--primary-blue)] transition disabled:opacity-50"
            aria-label="Message input"
          />
          <button
            onClick={() => void handleSend()}
            disabled={loading || !input.trim()}
            className="flex-shrink-0 rounded-xl bg-[var(--secondary-purple)] hover:brightness-110 disabled:opacity-40 px-4 py-2 text-white text-sm font-semibold transition"
            aria-label="Send message"
          >
            Send
          </button>
        </div>
        <p className="mt-2 text-xs text-[var(--gray-text)]">
          Enter to send · Shift+Enter for newline
        </p>
      </div>
    </aside>
  );
};
