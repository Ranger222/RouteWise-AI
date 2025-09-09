"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = { id: string; role: "user" | "assistant"; content: string; createdAt: number };

type Chat = { id: string; title: string; messages: Message[]; createdAt: number; updatedAt: number };

function uid() { return Math.random().toString(36).slice(2); }

const PRESETS = [
  "2-day weekend in Jaipur on a budget",
  "7-day Europe rail trip for 2, mid-range",
  "Goa beach getaway, 3 days, nightlife",
  "Himachal hiking loop, 5 days, scenic stays",
];

export default function ChatPage() {
  // Initialize with static values to avoid SSR/client mismatch
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeId, setActiveId] = useState<string>("");
  const [mounted, setMounted] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load from localStorage only on client after mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem("rw:chats");
      const saved = raw ? (JSON.parse(raw) as Chat[]) : [];
      setChats(saved);
      setActiveId(saved[0]?.id ?? uid());
    } catch {}
    setMounted(true);
  }, []);

  const activeChat = useMemo(
    () => chats.find((c) => c.id === activeId) ?? { id: activeId || "", title: "New Chat", messages: [], createdAt: Date.now(), updatedAt: Date.now() },
    [chats, activeId]
  );

  useEffect(() => { if (mounted) localStorage.setItem("rw:chats", JSON.stringify(chats)); }, [chats, mounted]);
  useEffect(() => { if (mounted) scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }, [activeChat.messages.length, loading, mounted]);

  function ensureActiveChat() {
    if (!activeId) return; // wait until mount sets an id
    if (!chats.find((c) => c.id === activeId)) {
      const now = Date.now();
      const nc: Chat = { id: activeId, title: "New Chat", messages: [], createdAt: now, updatedAt: now };
      setChats((prev) => [nc, ...prev]);
    }
  }

  async function sendQuery(q: string) {
    if (!mounted) return;
    if (!q.trim()) return;

    // Choose a stable target chat id for this request
    const targetId = activeId || uid();

    // Ensure chat exists and is active
    if (!chats.find((c) => c.id === targetId)) {
      const now = Date.now();
      setChats((prev) => [{ id: targetId, title: "New Chat", messages: [], createdAt: now, updatedAt: now }, ...prev]);
    }
    if (activeId !== targetId) setActiveId(targetId);

    const userMsg: Message = { id: uid(), role: "user", content: q.trim(), createdAt: Date.now() };
    setChats((prev) => prev.map((c) => c.id === targetId ? { ...c, title: c.messages.length ? c.title : q.slice(0, 40), messages: [...c.messages, userMsg], updatedAt: Date.now() } : c));
    setInput("");
    setLoading(true); setError(null);

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 1000 * 120); // 2 min safety timeout
      const res = await fetch("/api/plan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: q, sessionId: targetId }), signal: controller.signal });
      clearTimeout(timeout);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error((data as any)?.error || "Request failed");
      const content = (data as any).markdown || "";
      const assistantMsg: Message = { id: uid(), role: "assistant", content: content || "I couldn’t generate an itinerary. Please try refining your request.", createdAt: Date.now() };
      setChats((prev) => prev.map((c) => c.id === targetId ? { ...c, messages: [...c.messages, assistantMsg], updatedAt: Date.now() } : c));
    } catch (err: any) {
      setError(err?.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  function newChat() {
    const id = uid();
    const now = Date.now();
    const nc: Chat = { id, title: "New Chat", messages: [], createdAt: now, updatedAt: now };
    setChats((prev) => [nc, ...prev]);
    setActiveId(id);
    setInput("");
  }

  function deleteChat(id: string) {
    setChats((prev) => prev.filter((c) => c.id !== id));
    if (id === activeId) {
      const next = chats.find((c) => c.id !== id)?.id || "";
      setActiveId(next);
    }
  }

  if (!mounted) {
    return (
      <div className="min-h-screen grid grid-cols-12" suppressHydrationWarning>
        <main className="col-span-12 p-4">
          <div className="max-w-3xl mx-auto text-center mt-10 fade-in">
            <div className="mx-auto mb-6 h-20 w-20 rounded-full orb" />
            <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-slate-900">RouteWise</h1>
            <p className="mt-2 text-slate-600">Loading…</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen grid grid-cols-12" suppressHydrationWarning>
      {/* Sidebar */}
      <aside className="col-span-12 md:col-span-3 lg:col-span-2 border-r border-slate-200 bg-white/60 dark:bg-slate-900/50 dark:border-slate-800 p-4 space-y-3 hidden md:block">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-semibold text-slate-700 dark:text-slate-200">RouteWise</div>
          <button className="chip" onClick={newChat}>+ New</button>
        </div>
        <div className="space-y-1 overflow-auto max-h-[calc(100vh-8rem)] pr-1">
          {chats.length === 0 && (
            <div className="text-xs text-slate-500 dark:text-slate-400">No chats yet. Create one!</div>
          )}
          {chats.map((c) => (
            <div key={c.id} className={`group flex items-center justify-between rounded-lg px-2 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer ${c.id === activeId ? "bg-slate-100 dark:bg-slate-800" : ""}`} onClick={() => setActiveId(c.id)}>
              <span className="truncate pr-2 text-slate-700 dark:text-slate-200">{c.title}</span>
              <button className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 transition" onClick={(e) => { e.stopPropagation(); deleteChat(c.id); }}>✕</button>
            </div>
          ))}
        </div>
      </aside>

      {/* Main area */}
      <main className="col-span-12 md:col-span-9 lg:col-span-10 p-4">
        <div className="max-w-2xl mx-auto">
          {/* Hero */}
          {activeChat.messages.length === 0 && !loading && (
            <div className="text-center mt-3 fade-in">
              <div className="mx-auto mb-3 h-14 w-14 rounded-full orb" />
              <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">Hi there, traveler</h1>
              <p className="mt-1 text-slate-600 dark:text-slate-400">How can I help you plan today?</p>
            </div>
          )}

          {/* Presets: hide once conversation starts */}
          {activeChat.messages.length === 0 && !loading && (
            <div className="mt-4 flex flex-wrap gap-2 justify-center">
              {PRESETS.map((p) => (
                <button key={p} className="chip" onClick={() => { setInput(p); sendQuery(p); }}>{p}</button>
              ))}
            </div>
          )}

          {/* Chat messages */}
          <div ref={scrollRef} className="mt-4 card p-3 max-h-[65vh] overflow-auto scroll-smooth">
            {activeChat.messages.length === 0 && (
              <div className="text-sm text-slate-500 dark:text-slate-400 text-center">Ask anything about your trip. I’ll plan it.</div>
            )}
            <div className="space-y-3">
              {activeChat.messages.map((m) => (
                <div key={m.id} className={`rounded-2xl px-4 py-3 text-sm shadow-sm transition ${m.role === "user" ? "bubble-user ml-auto max-w-[80%]" : "bubble-assistant mr-auto max-w-[90%]"}`}>
                  {m.role === "assistant" ? (
                    <div className="prose prose-slate dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <div>{m.content}</div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="rounded-2xl px-4 py-3 text-sm bubble-assistant mr-auto max-w-[90%] animate-pulse">Thinking…</div>
              )}
            </div>
          </div>

          {error && (
            <div className="mt-3 card p-3 text-sm text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-800">{error}</div>
          )}

          {/* Input */}
          <form
            onSubmit={(e) => { e.preventDefault(); sendQuery(input); }}
            className="sticky bottom-4 mt-3 flex gap-2 items-center bg-white/60 dark:bg-slate-900/50 p-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm"
          >
            <input
              className="input flex-1"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe your trip… (destination, days, budget, interests)"
            />
            <button type="submit" className="btn" disabled={loading || !input.trim()}>
              {loading ? "Planning…" : "Send"}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
