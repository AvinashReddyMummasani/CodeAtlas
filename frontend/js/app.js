// js/app.js — CodeAtlas main application controller and tab coordinator

const TABS = [
  { id: 'home',     label: '🏠 Home' },
  { id: 'overview', label: '🌲 Project Tree Studio' },
  { id: 'detail',   label: '⚡ Optimality & Risk' },
  { id: 'flow',     label: '🌊 Execution Flow' },
  { id: 'report',   label: '📊 Project Report' },
];

function App() {
  const [sid, setSid] = React.useState(null);
  const [tree, setTree] = React.useState(null);
  const [sel, setSel] = React.useState(null);
  const [tab, setTab] = React.useState('home');
  const [uploading, setUploading] = React.useState(false);
  const [progress, setProgress] = React.useState(null);
  const [sumStatus, setSumStatus] = React.useState(null);
  const [keysInfo, setKeysInfo] = React.useState(null);
  const pollRef = React.useRef(null);
  const { toasts, toast, rmToast } = useToast();

  // Fetch API key rotation status periodically
  const fetchKeyStatus = React.useCallback(async () => {
    try {
      const r = await fetch(`${API}/keys/status`);
      if (r.ok) {
        const d = await r.json();
        setKeysInfo(d.keys || []);
      }
    } catch (_) {}
  }, []);

  React.useEffect(() => {
    fetchKeyStatus();
    const interval = setInterval(fetchKeyStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchKeyStatus]);

  // Poll /status while summarization runs
  const startPolling = React.useCallback((sessionId) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API}/session/${sessionId}/status`);
        if (!r.ok) return;
        const s = await r.json();
        setSumStatus(s);
        if (s.finished || s.tree_ready) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          if (s.error) {
            toast('AI summarization notice: ' + s.error, 'error');
          } else {
            toast('✅ AI summaries complete!', 'success');
          }
          // Fetch the completed tree
          const tr = await fetch(`${API}/session/${sessionId}/tree`);
          if (tr.ok) {
            const fullTree = await tr.json();
            setTree(fullTree);
            setSumStatus(null);
            // Default select root
            const built = buildTree(fullTree);
            if (built.length > 0 && !sel) {
              setSel(built[0]);
            }
          }
        }
      } catch (_) {}
    }, 2000);
  }, [toast, sel]);

  React.useEffect(() => {
    return () => pollRef.current && clearInterval(pollRef.current);
  }, []);

  const upload = async (file) => {
    if (!file.name.endsWith('.zip')) {
      toast('Please upload a valid .zip file', 'error');
      return;
    }
    setUploading(true);
    setProgress({ stage: 'Reading archive…', pct: 10 });
    const fd = new FormData();
    fd.append('file', file);
    if (sid) fd.append('session_id', sid);

    try {
      setProgress({ stage: 'Uploading & extracting…', pct: 25 });
      const r = await fetch(`${API}/upload`, { method: 'POST', body: fd });
      if (!r.ok) {
        const e = await r.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(e.detail || 'Upload failed');
      }
      const data = await r.json();
      setProgress({ stage: 'Parsing AST hierarchy…', pct: 60 });
      setSid(data.session_id);
      setProgress({ stage: 'Starting batch AI summarization…', pct: 85 });
      toast(`✅ ${data.py_files_count} Python files parsed`, 'success');

      if (data.summarizing) {
        setSumStatus({ stage: 'Starting AI summarization…', finished: false, error: null });
        startPolling(data.session_id);
        setTab('overview');
      }
      setProgress({ stage: 'Done!', pct: 100 });
    } catch (e) {
      toast(e.message || 'Upload failed', 'error');
    } finally {
      setUploading(false);
      setTimeout(() => setProgress(null), 800);
    }
  };

  const selNode = (n) => {
    setSel(n);
    if (tab === 'home') setTab('overview');
  };

  const jumpFn = (cf) => {
    if (!tree?.all_functions?.[cf.func_id]) return;
    const fn = tree.all_functions[cf.func_id];
    setSel({
      id: cf.func_id,
      name: `def ${cf.name}`,
      rawName: cf.name,
      level: 'FUNCTION',
      lineno: fn.lineno,
      endLineno: fn.end_lineno,
      source: fn.source_snippet || fn.source,
      summary: fn.summary,
      file: fn.file || fn.filepath,
      callers: fn.callers || [],
      callees: fn.callees || []
    });
    setTab('overview');
  };

  const jumpToFlow = (funcId) => {
    if (tree?.all_functions?.[funcId]) {
      const fn = tree.all_functions[funcId];
      setSel({
        id: funcId,
        name: `def ${fn.name}`,
        rawName: fn.name,
        level: 'FUNCTION',
        lineno: fn.lineno,
        endLineno: fn.end_lineno,
        source: fn.source_snippet || fn.source,
        summary: fn.summary,
        file: fn.file || fn.filepath,
        callers: fn.callers || [],
        callees: fn.callees || []
      });
    }
    setTab('flow');
  };

  const retryAI = async () => {
    if (!sid) return;
    toast('Retrying AI summaries…', 'info');
    try {
      await fetch(`${API}/session/${sid}/retry_summarization`, { method: 'POST' });
      const tr = await fetch(`${API}/session/${sid}/tree`);
      if (tr.ok) {
        setTree(await tr.json());
        toast('✅ Summaries updated', 'success');
      }
    } catch (_) {
      toast('Retry failed', 'error');
    }
  };

  const activeKeysCount = keysInfo ? keysInfo.filter(k => k.available).length : 0;
  const totalKeysCount = keysInfo ? keysInfo.length : 0;

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: '#0d1117' }}>
      <Sidebar
        sid={sid}
        tree={tree}
        sel={sel}
        onSel={selNode}
        onUpload={upload}
        uploading={uploading}
        progress={progress}
        sumStatus={sumStatus}
      />

      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', position: 'relative' }}>
        {/* Top Tab Bar */}
        <div style={{ display: 'flex', alignItems: 'center', borderBottom: '1px solid #30363d', background: '#161b22', paddingLeft: 4, flexShrink: 0, height: 42 }}>
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cls('tab', tab === t.id && 'active')}
            >
              {t.label}
            </button>
          ))}

          {/* AI Summarization progress pill */}
          {sumStatus && !sumStatus.finished && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 8, fontSize: 11, color: '#58a6ff', background: '#1f6feb15', border: '1px solid #1f6feb33', borderRadius: 6, padding: '2px 10px' }}>
              <Spin sz={10} /> {sumStatus.stage || 'AI working…'}
            </div>
          )}

          {/* Multi-Key Rotation Status Indicator */}
          {totalKeysCount > 0 && (
            <div
              title={`Gemini API Key Rotation: ${activeKeysCount}/${totalKeysCount} keys operational`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                marginLeft: 'auto',
                marginRight: 8,
                fontSize: 11,
                padding: '3px 8px',
                borderRadius: 6,
                background: activeKeysCount > 0 ? '#3fb95015' : '#f8514915',
                border: `1px solid ${activeKeysCount > 0 ? '#3fb95033' : '#f8514933'}`,
                color: activeKeysCount > 0 ? '#3fb950' : '#f85149',
                cursor: 'default'
              }}
            >
              <span>🔑</span>
              <span>{activeKeysCount}/{totalKeysCount} {totalKeysCount === 1 ? 'Key' : 'Keys'}</span>
            </div>
          )}

          {tree && tab !== 'home' && (
            <button
              onClick={retryAI}
              className="btn btn-yellow"
              style={{ marginLeft: totalKeysCount > 0 ? 0 : 'auto', marginRight: 8, padding: '4px 10px', fontSize: 11 }}
            >
              🔄 Retry AI
            </button>
          )}
        </div>

        {/* Tab Content Panes */}
        <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          {tab === 'home' && (
            <WelcomeHome onUpload={upload} uploading={uploading} progress={progress} />
          )}
          {tab === 'overview' && (
            <OverviewTab
              tree={tree}
              node={sel}
              sid={sid}
              onSelectNode={setSel}
              toast={toast}
              onJumpToFlow={jumpToFlow}
            />
          )}
          {tab === 'detail' && (
            <DetailTab sid={sid} node={sel} toast={toast} />
          )}
          {tab === 'flow' && (
            <FlowTab sid={sid} node={sel} toast={toast} />
          )}
          {tab === 'report' && (
            <ReportTab sid={sid} toast={toast} />
          )}

          {/* Summarization Overlay */}
          {sumStatus && !sumStatus.finished && (
            <SumProgress status={sumStatus} />
          )}
        </div>
      </div>

      {/* Global Explorer RAG Chatbot (right-side drawer) */}
      <ChatPanel sid={sid} tree={tree} onJump={jumpFn} toast={toast} />
      <Toasts T={toasts} rm={rmToast} />
    </div>
  );
}

// Render root
ReactDOM.createRoot(document.getElementById('root')).render(<App />);
