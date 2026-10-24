// js/app.js — CodeAtlas main application controller and tab coordinator with Authentication & Projects Management

const TABS = [
  { id: 'home',     label: '🏠 Home' },
  { id: 'overview', label: '🌲 Project Tree Studio' },
  { id: 'detail',   label: '⚡ Optimality & Risk' },
  { id: 'flow',     label: '🌊 Execution Flow' },
  { id: 'report',   label: '📊 Project Report' },
];

// ── Auth Modal Component (Login & Signup) ──────────────────────────────────
const AuthModal = ({ mode: initialMode, onClose, onAuthSuccess, toast }) => {
  const [mode, setMode] = React.useState(initialMode || 'login');
  const [username, setUsername] = React.useState('');
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!username.trim() || !password) {
      setError('Please fill in all required fields.');
      return;
    }
    if (mode === 'signup' && !email.trim()) {
      setError('Email address is required for registration.');
      return;
    }

    setLoading(true);
    try {
      const endpoint = mode === 'signup' ? `${API}/auth/signup` : `${API}/auth/login`;
      const body = mode === 'signup'
        ? { username: username.trim(), email: email.trim(), password }
        : { username_or_email: username.trim(), password };

      const r = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await r.json();

      if (!r.ok) {
        throw new Error(data.detail || (mode === 'signup' ? 'Registration failed' : 'Login failed'));
      }

      onAuthSuccess(data);
      if (toast) toast(mode === 'signup' ? `🎉 Welcome to CodeAtlas, ${data.user.username}!` : `👋 Welcome back, ${data.user.username}!`, 'success');
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        background: '#00000088',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20
      }}
      onClick={onClose}
    >
      <div
        className="card anim-scale"
        style={{
          width: '100%',
          maxWidth: 400,
          background: '#161b22',
          border: '1px solid #30363d',
          borderRadius: 12,
          padding: 24,
          boxShadow: '0 16px 48px #000000aa',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid #30363d', marginBottom: 20 }}>
          <button
            onClick={() => { setMode('login'); setError(null); }}
            style={{
              flex: 1,
              padding: '10px',
              fontSize: 14,
              fontWeight: 700,
              background: 'transparent',
              border: 'none',
              borderBottom: mode === 'login' ? '2px solid #58a6ff' : '2px solid transparent',
              color: mode === 'login' ? '#58a6ff' : '#8b949e',
              cursor: 'pointer'
            }}
          >
            🔑 Sign In
          </button>
          <button
            onClick={() => { setMode('signup'); setError(null); }}
            style={{
              flex: 1,
              padding: '10px',
              fontSize: 14,
              fontWeight: 700,
              background: 'transparent',
              border: 'none',
              borderBottom: mode === 'signup' ? '2px solid #58a6ff' : '2px solid transparent',
              color: mode === 'signup' ? '#58a6ff' : '#8b949e',
              cursor: 'pointer'
            }}
          >
            ✨ Create Account
          </button>
        </div>

        {error && (
          <div style={{ padding: '8px 12px', borderRadius: 6, background: '#f8514918', border: '1px solid #f8514944', color: '#f85149', fontSize: 12, marginBottom: 16 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#8b949e', marginBottom: 4 }}>
              {mode === 'signup' ? 'Username' : 'Username or Email'}
            </label>
            <input
              className="inp"
              type="text"
              placeholder={mode === 'signup' ? 'e.g. dev_alex' : 'Username or email'}
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>

          {mode === 'signup' && (
            <div>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#8b949e', marginBottom: 4 }}>
                Email Address
              </label>
              <input
                className="inp"
                type="email"
                placeholder="you@domain.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </div>
          )}

          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#8b949e', marginBottom: 4 }}>
              Password
            </label>
            <input
              className="inp"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-solid-blue"
            disabled={loading}
            style={{ padding: '10px', fontSize: 13, fontWeight: 700, marginTop: 6 }}
          >
            {loading ? <Spin sz={14} /> : (mode === 'signup' ? 'Sign Up & Continue' : 'Sign In')}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: 16, fontSize: 11.5, color: '#8b949e' }}>
          {mode === 'login' ? (
            <span>
              Don't have an account?{' '}
              <button
                onClick={() => { setMode('signup'); setError(null); }}
                style={{ background: 'transparent', border: 'none', color: '#58a6ff', cursor: 'pointer', fontWeight: 600 }}
              >
                Sign up
              </button>
            </span>
          ) : (
            <span>
              Already have an account?{' '}
              <button
                onClick={() => { setMode('login'); setError(null); }}
                style={{ background: 'transparent', border: 'none', color: '#58a6ff', cursor: 'pointer', fontWeight: 600 }}
              >
                Sign in
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

// ── User Projects Modal ────────────────────────────────────────────────────
const ProjectsModal = ({ projects, onClose, onSelectProject, activeSid }) => {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        background: '#00000088',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20
      }}
      onClick={onClose}
    >
      <div
        className="card anim-scale"
        style={{
          width: '100%',
          maxWidth: 520,
          background: '#161b22',
          border: '1px solid #30363d',
          borderRadius: 12,
          padding: 24,
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 16px 48px #000000aa',
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 20 }}>📁</span>
            <span style={{ fontSize: 16, fontWeight: 700, color: '#e6edf3' }}>My Saved Projects</span>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: 16 }}
          >
            ✕
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, paddingRight: 4 }}>
          {projects.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '30px 10px', color: '#8b949e', fontSize: 13 }}>
              No uploaded projects saved to your account yet.<br />
              <span style={{ fontSize: 11.5, color: '#484f58' }}>Upload any Python .zip archive to save it here.</span>
            </div>
          ) : (
            projects.map(p => {
              const isActive = activeSid === p.session_id;
              return (
                <div
                  key={p.session_id}
                  style={{
                    padding: '12px 14px',
                    borderRadius: 8,
                    background: isActive ? '#1f6feb22' : '#21262d',
                    border: `1px solid ${isActive ? '#58a6ff66' : '#30363d'}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 12
                  }}
                  className="card-hover"
                >
                  <div>
                    <div style={{ fontSize: 13.5, fontWeight: 700, color: isActive ? '#58a6ff' : '#e6edf3' }}>
                      📦 {p.project_name}
                    </div>
                    <div style={{ fontSize: 11, color: '#8b949e', marginTop: 3 }}>
                      {p.files_count || 0} Files · {p.functions_count || 0} Functions · {new Date(p.created_at).toLocaleDateString()}
                    </div>
                  </div>

                  <button
                    onClick={() => onSelectProject(p)}
                    className={cls('btn', isActive ? 'btn-solid-blue' : '')}
                    style={{
                      padding: '5px 12px',
                      fontSize: 12,
                      fontWeight: 600,
                      background: isActive ? undefined : '#30363d',
                      color: isActive ? '#fff' : '#c9d1d9'
                    }}
                  >
                    {isActive ? 'Active' : 'Open →'}
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

// ── Main App Controller ────────────────────────────────────────────────────
function App() {
  const [sid, setSid] = React.useState(null);
  const [tree, setTree] = React.useState(null);
  const [sel, setSel] = React.useState(null);
  const [tab, setTab] = React.useState('home');
  const [uploading, setUploading] = React.useState(false);
  const [progress, setProgress] = React.useState(null);
  const [sumStatus, setSumStatus] = React.useState(null);
  const [keysInfo, setKeysInfo] = React.useState(null);

  // Authentication & User state
  const [user, setUser] = React.useState(null);
  const [token, setToken] = React.useState(() => localStorage.getItem('codeatlas_token'));
  const [userProjects, setUserProjects] = React.useState([]);
  const [showAuthModal, setShowAuthModal] = React.useState(false);
  const [authMode, setAuthMode] = React.useState('login');
  const [showProjectsModal, setShowProjectsModal] = React.useState(false);

  const pollRef = React.useRef(null);
  const { toasts, toast, rmToast } = useToast();

  // Validate stored token and fetch user profile
  const fetchCurrentUser = React.useCallback(async (userToken) => {
    if (!userToken) return;
    try {
      const r = await fetch(`${API}/auth/me`, {
        headers: { 'Authorization': `Bearer ${userToken}` }
      });
      if (r.ok) {
        const d = await r.json();
        setUser(d.user);
        setUserProjects(d.projects || []);
      } else {
        localStorage.removeItem('codeatlas_token');
        setToken(null);
        setUser(null);
      }
    } catch (_) {}
  }, []);

  React.useEffect(() => {
    if (token) {
      fetchCurrentUser(token);
    }
  }, [token, fetchCurrentUser]);

  // Handle successful login/signup
  const handleAuthSuccess = (data) => {
    if (data.token) {
      localStorage.setItem('codeatlas_token', data.token);
      setToken(data.token);
      setUser(data.user);
      fetchCurrentUser(data.token);
    }
  };

  // Handle logout
  const handleLogout = async () => {
    try {
      if (token) {
        await fetch(`${API}/auth/logout`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
      }
    } catch (_) {}
    localStorage.removeItem('codeatlas_token');
    setToken(null);
    setUser(null);
    setUserProjects([]);
    toast('Logged out successfully', 'info');
  };

  // Open existing project from user's history
  const activateProject = async (proj) => {
    setShowProjectsModal(false);
    toast(`Loading ${proj.project_name}…`, 'info');
    try {
      const r = await fetch(`${API}/session/${proj.session_id}/activate`, { method: 'POST' });
      if (!r.ok) throw new Error('Could not activate session');

      const tr = await fetch(`${API}/session/${proj.session_id}/tree`);
      if (!tr.ok) throw new Error('Could not fetch session tree');

      const fullTree = await tr.json();
      setSid(proj.session_id);
      setTree(fullTree);
      setSumStatus(null);
      const built = buildTree(fullTree);
      if (built.length > 0) setSel(built[0]);
      setTab('overview');
      toast(`✅ Loaded ${proj.project_name}`, 'success');
    } catch (err) {
      toast(err.message || 'Failed loading project', 'error');
    }
  };

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
            const built = buildTree(fullTree);
            if (built.length > 0 && !sel) {
              setSel(built[0]);
            }
          }
          // Refresh user projects
          if (token) fetchCurrentUser(token);
        }
      } catch (_) {}
    }, 2000);
  }, [toast, sel, token, fetchCurrentUser]);

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
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
      const r = await fetch(`${API}/upload`, { method: 'POST', headers, body: fd });
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
      if (token) fetchCurrentUser(token);
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
        <div style={{ display: 'flex', alignItems: 'center', borderBottom: '1px solid #30363d', background: '#161b22', paddingLeft: 4, paddingRight: 8, flexShrink: 0, height: 42 }}>
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

          {/* Right Header Navigation Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto' }}>
            {/* Multi-Key Rotation Status Indicator */}
            {totalKeysCount > 0 && (
              <div
                title={`Gemini API Key Rotation: ${activeKeysCount}/${totalKeysCount} operational`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  fontSize: 11,
                  padding: '3px 7px',
                  borderRadius: 6,
                  background: activeKeysCount > 0 ? '#3fb95015' : '#f8514915',
                  border: `1px solid ${activeKeysCount > 0 ? '#3fb95033' : '#f8514933'}`,
                  color: activeKeysCount > 0 ? '#3fb950' : '#f85149',
                  cursor: 'default'
                }}
              >
                <span>🔑</span>
                <span>{activeKeysCount}/{totalKeysCount}</span>
              </div>
            )}

            {/* Authentication Buttons / User Profile */}
            {user ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <button
                  onClick={() => setShowProjectsModal(true)}
                  className="btn"
                  style={{
                    padding: '3px 8px',
                    fontSize: 11,
                    fontWeight: 600,
                    background: '#21262d',
                    color: '#c9d1d9',
                    border: '1px solid #30363d',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4
                  }}
                  title="View saved projects"
                >
                  <span>📁</span> Projects ({userProjects.length})
                </button>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5,
                    padding: '2px 8px',
                    borderRadius: 6,
                    background: '#1f6feb22',
                    border: '1px solid #388bfd44',
                    fontSize: 11,
                    fontWeight: 600,
                    color: '#58a6ff'
                  }}
                >
                  <div style={{ width: 16, height: 16, borderRadius: '50%', background: '#388bfd', color: '#fff', fontSize: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                  <span>{user.username}</span>
                </div>

                <button
                  onClick={handleLogout}
                  className="btn"
                  style={{ padding: '3px 8px', fontSize: 11, background: '#21262d', color: '#8b949e', border: '1px solid #30363d' }}
                  title="Sign out of account"
                >
                  Logout
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <button
                  onClick={() => { setAuthMode('login'); setShowAuthModal(true); }}
                  className="btn"
                  style={{ padding: '3px 9px', fontSize: 11, fontWeight: 600, background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d' }}
                >
                  🔑 Sign In
                </button>
                <button
                  onClick={() => { setAuthMode('signup'); setShowAuthModal(true); }}
                  className="btn btn-solid-blue"
                  style={{ padding: '3px 9px', fontSize: 11, fontWeight: 600 }}
                >
                  ✨ Sign Up
                </button>
              </div>
            )}

            {tree && tab !== 'home' && (
              <button
                onClick={retryAI}
                className="btn btn-yellow"
                style={{ padding: '3px 8px', fontSize: 11 }}
              >
                🔄 Retry AI
              </button>
            )}
          </div>
        </div>

        {/* Tab Content Panes */}
        <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          {tab === 'home' && (
            <WelcomeHome
              onUpload={upload}
              uploading={uploading}
              progress={progress}
              sid={sid}
              tree={tree}
              onNavigate={setTab}
              onOpenChat={() => {
                const el = document.querySelector('input[placeholder*="Ask"]');
                if (el) el.focus();
              }}
            />
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

      {/* Global Explorer RAG Chatbot (right-side drawer with Chat History) */}
      <ChatPanel
        sid={sid}
        tree={tree}
        onJump={jumpFn}
        toast={toast}
        user={user}
        token={token}
      />

      {/* Authentication Modal */}
      {showAuthModal && (
        <AuthModal
          mode={authMode}
          onClose={() => setShowAuthModal(false)}
          onAuthSuccess={handleAuthSuccess}
          toast={toast}
        />
      )}

      {/* Saved Projects Modal */}
      {showProjectsModal && (
        <ProjectsModal
          projects={userProjects}
          activeSid={sid}
          onClose={() => setShowProjectsModal(false)}
          onSelectProject={activateProject}
        />
      )}

      <Toasts T={toasts} rm={rmToast} />
    </div>
  );
}

// Render root
ReactDOM.createRoot(document.getElementById('root')).render(<App />);
