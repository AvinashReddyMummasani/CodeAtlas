// js/chat.js — Right panel RAG chat component

const ChatPanel = ({ sid, tree, onJump, toast }) => {
  const [msgs, setMsgs] = React.useState([
    { role: 'ai', content: "👋 Hi! I'm your CodeAtlas AI. Ask me anything about your codebase — I'll search the code and give you grounded answers.", cited: [] }
  ]);
  const [inp, setInp] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const bottom = React.useRef();
  React.useEffect(() => bottom.current?.scrollIntoView({ behavior: 'smooth' }), [msgs]);

  const send = async () => {
    if (!inp.trim() || !sid || loading) return;
    const q = inp.trim(); setInp('');
    setMsgs(m => [...m, { role: 'user', content: q, cited: [] }]);
    setLoading(true);
    try {
      const hist = msgs.slice(-8).map(m => ({ role: m.role === 'user' ? 'user' : 'model', content: m.content }));
      const r = await fetch(`${API}/session/${sid}/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q, chat_history: hist }) });
      const d = await r.json();
      setMsgs(m => [...m, { role: 'ai', content: d.answer || 'No answer generated.', cited: d.cited_functions || [] }]);
    } catch { setMsgs(m => [...m, { role: 'ai', content: '⚠ Connection error — is the backend running?', cited: [] }]); }
    finally { setLoading(false); }
  };

  const SUGGESTIONS = ["What does this codebase do?", "List all entry points", "What are the main classes?", "Find functions with most dependencies", "How does data flow through the app?"];

  return (
    <div style={{ width: 300, minWidth: 300, display: 'flex', flexDirection: 'column', height: '100%', background: '#161b22', borderLeft: '1px solid #30363d' }}>
      {/* Header */}
      <div style={{ padding: '12px 14px', borderBottom: '1px solid #30363d', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 30, height: 30, borderRadius: 8, background: 'linear-gradient(135deg,#388bfd,#bc8cff)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15 }}>💬</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 13, color: '#e6edf3' }}>Explorer Chat</div>
            <div style={{ fontSize: 10, color: '#8b949e' }}>RAG-powered · Codebase-grounded</div>
          </div>
          <span style={{ marginLeft: 'auto' }}><AIBadge /></span>
        </div>
        {!sid && <div style={{ marginTop: 8, fontSize: 11, color: '#d29922', background: '#d2992210', borderRadius: 5, padding: '4px 8px' }}>Upload a project to enable chat</div>}
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 10px 4px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {msgs.map((m, i) => (
          <div key={i} className="anim-slide" style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div className={m.role === 'user' ? 'bubble-user' : 'bubble-ai'}
              style={{ maxWidth: '88%', padding: '9px 12px', fontSize: 12.5, lineHeight: 1.65, color: m.role === 'user' ? '#fff' : '#c9d1d9' }}>
              {m.role === 'ai' && <div style={{ marginBottom: 5 }}><AIBadge /></div>}
              <div style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>
              {(m.cited || []).length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {m.cited.map((cf, j) => (
                    <button key={j} onClick={() => onJump(cf)}
                      style={{ fontSize: 10.5, padding: '2px 8px', borderRadius: 5, background: '#58a6ff18', color: '#58a6ff', border: '1px solid #58a6ff33', cursor: 'pointer', fontFamily: 'monospace', fontWeight: 500 }}>
                      → {cf.name}
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
              <Spin sz={11} /> <span className="anim-pulse">Searching codebase…</span>
            </div>
          </div>
        )}
        <div ref={bottom} />
      </div>

      {/* Suggestions */}
      {msgs.length <= 1 && sid && (
        <div style={{ padding: '0 10px 6px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ fontSize: 10, color: '#484f58', paddingLeft: 2 }}>Try asking:</div>
          {SUGGESTIONS.slice(0, 3).map(s => (
            <button key={s} onClick={() => setInp(s)}
              style={{ textAlign: 'left', padding: '6px 10px', borderRadius: 7, background: '#21262d', border: '1px solid #30363d', color: '#8b949e', fontSize: 11, cursor: 'pointer' }}
              className="tree-item">
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={{ padding: '8px 10px', borderTop: '1px solid #30363d', flexShrink: 0 }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <input className="inp" style={{ fontSize: 12.5 }}
            placeholder={sid ? 'Ask anything about your code…' : 'Upload a project first'}
            value={inp} disabled={!sid || loading}
            onChange={e => setInp(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()} />
          <button onClick={send} disabled={!sid || loading || !inp.trim()}
            className="btn btn-solid-blue"
            style={{ padding: '6px 12px', borderRadius: 8, fontSize: 15, flexShrink: 0 }}>➤</button>
        </div>
      </div>
    </div>
  );
};
