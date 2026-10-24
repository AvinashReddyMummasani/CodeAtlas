// js/chat.js — Right panel RAG chat component with ChatGPT-style conversation history

const ChatPanel = ({ sid, tree, onJump, toast, user, token }) => {
  const [threads, setThreads] = React.useState([]);
  const [activeThreadId, setActiveThreadId] = React.useState(null);
  const [showHistory, setShowHistory] = React.useState(false);
  const [msgs, setMsgs] = React.useState([
    { role: 'ai', content: "👋 Hi! I'm your CodeAtlas AI. Ask me anything about your codebase — I'll search the code and give you grounded answers.", cited: [] }
  ]);
  const [inp, setInp] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [loadingHistory, setLoadingHistory] = React.useState(false);
  const bottom = React.useRef();

  React.useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' });
  }, [msgs, loading]);

  // Load threads for the session
  const fetchThreads = React.useCallback(async () => {
    if (!sid) return;
    try {
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
      const r = await fetch(`${API}/session/${sid}/threads`, { headers });
      if (r.ok) {
        const data = await r.json();
        setThreads(data || []);
      }
    } catch (_) {}
  }, [sid, token]);

  React.useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  // Load messages when selecting a thread
  const selectThread = async (th) => {
    if (!th || !th.id) return;
    setActiveThreadId(th.id);
    setShowHistory(false);
    setLoadingHistory(true);
    try {
      const r = await fetch(`${API}/session/${sid}/threads/${th.id}/messages`);
      if (r.ok) {
        const d = await r.json();
        const serverMsgs = (d.messages || []).map(m => ({
          role: m.sender === 'user' ? 'user' : 'ai',
          content: m.text,
          cited: m.citations || []
        }));
        if (serverMsgs.length > 0) {
          setMsgs(serverMsgs);
        } else {
          setMsgs([
            { role: 'ai', content: `Starting conversation: "${th.title}". What would you like to explore?`, cited: [] }
          ]);
        }
      }
    } catch (e) {
      if (toast) toast('Failed loading chat history', 'error');
    } finally {
      setLoadingHistory(false);
    }
  };

  // Start a fresh new chat
  const startNewChat = () => {
    setActiveThreadId(null);
    setShowHistory(false);
    setMsgs([
      { role: 'ai', content: "👋 New conversation started. Ask me anything about this codebase!", cited: [] }
    ]);
  };

  // Delete a thread
  const deleteThread = async (e, threadId) => {
    e.stopPropagation();
    try {
      const r = await fetch(`${API}/session/${sid}/threads/${threadId}`, { method: 'DELETE' });
      if (r.ok) {
        setThreads(prev => prev.filter(t => t.id !== threadId));
        if (activeThreadId === threadId) {
          startNewChat();
        }
        if (toast) toast('Chat thread deleted', 'info');
      }
    } catch (_) {
      if (toast) toast('Failed to delete thread', 'error');
    }
  };

  const send = async () => {
    if (!inp.trim() || !sid || loading) return;
    const q = inp.trim();
    setInp('');
    setMsgs(m => [...m, { role: 'user', content: q, cited: [] }]);
    setLoading(true);

    try {
      const hist = msgs.slice(-8).map(m => ({
        role: m.role === 'user' ? 'user' : 'model',
        content: m.content
      }));

      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const r = await fetch(`${API}/session/${sid}/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          question: q,
          chat_history: hist,
          thread_id: activeThreadId
        })
      });

      const d = await r.json();
      if (!r.ok) {
        throw new Error(d.detail || 'Chat query failed');
      }

      setMsgs(m => [...m, {
        role: 'ai',
        content: d.answer || 'No answer generated.',
        cited: d.cited_functions || []
      }]);

      if (d.thread_id && !activeThreadId) {
        setActiveThreadId(d.thread_id);
      }
      fetchThreads();
    } catch (err) {
      setMsgs(m => [...m, {
        role: 'ai',
        content: '⚠ Error generating answer — ' + (err.message || 'check server connection.'),
        cited: []
      }]);
    } finally {
      setLoading(false);
    }
  };

  const SUGGESTIONS = [
    "What does this codebase do?",
    "List all entry points",
    "What are the main classes?",
    "Find functions with most dependencies",
    "How does data flow through the app?"
  ];

  return (
    <div style={{ width: 330, minWidth: 330, display: 'flex', flexDirection: 'column', height: '100%', background: '#161b22', borderLeft: '1px solid #30363d', position: 'relative' }}>
      {/* Top Header */}
      <div style={{ padding: '10px 12px', borderBottom: '1px solid #30363d', flexShrink: 0, background: '#1c2128' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 28, height: 28, borderRadius: 8, background: 'linear-gradient(135deg,#388bfd,#bc8cff)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14 }}>💬</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 13, color: '#e6edf3' }}>Codebase Chat</div>
              <div style={{ fontSize: 9.5, color: '#8b949e' }}>RAG Architecture Agent</div>
            </div>
          </div>
          <AIBadge />
        </div>

        {/* Action Bar: New Chat & History Toggle */}
        {sid && (
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            <button
              onClick={startNewChat}
              className="btn btn-solid-blue"
              style={{ flex: 1, padding: '4px 8px', fontSize: 11, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}
              title="Start a new chat conversation"
            >
              <span>➕</span> New Chat
            </button>
            <button
              onClick={() => {
                setShowHistory(prev => !prev);
                fetchThreads();
              }}
              className="btn"
              style={{
                flex: 1,
                padding: '4px 8px',
                fontSize: 11,
                fontWeight: 600,
                background: showHistory ? '#388bfd22' : '#21262d',
                color: showHistory ? '#58a6ff' : '#c9d1d9',
                border: `1px solid ${showHistory ? '#58a6ff' : '#30363d'}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 4
              }}
              title="View past conversation history"
            >
              <span>📜</span> History ({threads.length})
            </button>
          </div>
        )}

        {!sid && (
          <div style={{ marginTop: 8, fontSize: 11, color: '#d29922', background: '#d2992210', borderRadius: 5, padding: '4px 8px' }}>
            Upload a project to enable chat &amp; history
          </div>
        )}
      </div>

      {/* History Drawer Overlay */}
      {showHistory && (
        <div
          className="anim-slide"
          style={{
            position: 'absolute',
            top: 86,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 30,
            background: '#161b22fa',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            flexDirection: 'column',
            padding: '12px 10px',
            borderTop: '1px solid #30363d',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, paddingBottom: 6, borderBottom: '1px solid #30363d' }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#e6edf3' }}>📜 Conversation History</span>
            <button
              onClick={() => setShowHistory(false)}
              style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: 14 }}
            >
              ✕
            </button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
            {threads.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#8b949e', fontSize: 12, padding: '30px 10px' }}>
                No saved conversations yet.<br />
                <span style={{ fontSize: 11, color: '#484f58' }}>Ask a question to start your first chat thread.</span>
              </div>
            ) : (
              threads.map(t => (
                <div
                  key={t.id}
                  onClick={() => selectThread(t)}
                  style={{
                    padding: '8px 10px',
                    borderRadius: 8,
                    background: activeThreadId === t.id ? '#1f6feb22' : '#21262d',
                    border: `1px solid ${activeThreadId === t.id ? '#58a6ff66' : '#30363d'}`,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 8,
                    transition: 'all 0.15s ease'
                  }}
                  className="card-hover"
                >
                  <div style={{ overflow: 'hidden', flex: 1 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: activeThreadId === t.id ? '#58a6ff' : '#e6edf3', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {t.title}
                    </div>
                    <div style={{ fontSize: 10, color: '#8b949e', marginTop: 2, display: 'flex', gap: 6 }}>
                      <span>💬 {t.message_count || 0} msgs</span>
                      <span>•</span>
                      <span>{new Date(t.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => deleteThread(e, t.id)}
                    style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: 12, padding: '2px 4px' }}
                    title="Delete thread"
                  >
                    🗑️
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Messages Stream */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 10px 4px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {loadingHistory && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 20 }}>
            <Spin sz={16} />
          </div>
        )}

        {!loadingHistory && msgs.map((m, i) => (
          <div key={i} className="anim-slide" style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div
              className={m.role === 'user' ? 'bubble-user' : 'bubble-ai'}
              style={{
                maxWidth: '90%',
                padding: '9px 12px',
                fontSize: 12.5,
                lineHeight: 1.65,
                color: m.role === 'user' ? '#fff' : '#c9d1d9',
                boxShadow: '0 2px 8px #00000033'
              }}
            >
              {m.role === 'ai' && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 }}>
                  <AIBadge />
                </div>
              )}
              <div style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>
              {(m.cited || []).length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {m.cited.map((cf, j) => (
                    <button
                      key={j}
                      onClick={() => onJump && onJump(cf)}
                      style={{
                        fontSize: 10.5,
                        padding: '2px 8px',
                        borderRadius: 5,
                        background: '#58a6ff18',
                        color: '#58a6ff',
                        border: '1px solid #58a6ff33',
                        cursor: 'pointer',
                        fontFamily: 'monospace',
                        fontWeight: 500
                      }}
                      title="Jump to code node in tree"
                    >
                      → {cf.name || cf.func_id}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div className="bubble-ai" style={{ padding: '9px 14px', fontSize: 12, color: '#8b949e', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Spin sz={11} /> <span className="anim-pulse">Searching vector index &amp; generating grounded answer…</span>
            </div>
          </div>
        )}
        <div ref={bottom} />
      </div>

      {/* Suggested Questions if fresh chat */}
      {msgs.length <= 1 && sid && !showHistory && (
        <div style={{ padding: '0 10px 6px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ fontSize: 10, color: '#8b949e', paddingLeft: 2 }}>Quick Prompts:</div>
          {SUGGESTIONS.slice(0, 3).map(s => (
            <button
              key={s}
              onClick={() => setInp(s)}
              style={{
                textAlign: 'left',
                padding: '6px 10px',
                borderRadius: 7,
                background: '#21262d',
                border: '1px solid #30363d',
                color: '#8b949e',
                fontSize: 11,
                cursor: 'pointer'
              }}
              className="tree-item"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input Form */}
      <div style={{ padding: '8px 10px', borderTop: '1px solid #30363d', flexShrink: 0, background: '#1c2128' }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <input
            className="inp"
            style={{ fontSize: 12.5 }}
            placeholder={sid ? 'Ask code question…' : 'Upload project first'}
            value={inp}
            disabled={!sid || loading}
            onChange={e => setInp(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          />
          <button
            onClick={send}
            disabled={!sid || loading || !inp.trim()}
            className="btn btn-solid-blue"
            style={{ padding: '6px 12px', borderRadius: 8, fontSize: 14, flexShrink: 0 }}
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  );
};
