// js/primitives.js — Reusable primitive UI components

// ── Spinner ───────────────────────────────────────────────────────────────
const Spin = ({ sz = 14, color = '#58a6ff' }) => (
  <svg className="anim-spin" width={sz} height={sz} viewBox="0 0 24 24" fill="none" strokeWidth="2.5">
    <circle cx="12" cy="12" r="10" stroke={color} strokeOpacity=".15" />
    <path d="M12 2a10 10 0 0 1 10 10" stroke={color} />
  </svg>
);

// ── AI Badge ──────────────────────────────────────────────────────────────
const AIBadge = () => <span className="ai-badge">⚠ AI Advisory</span>;

// ── Star rating ───────────────────────────────────────────────────────────
const Stars = ({ n = 0, max = 5 }) => (
  <span style={{ display: 'inline-flex', gap: 2 }}>
    {Array.from({ length: max }, (_, i) => (
      <svg key={i} width="13" height="13" viewBox="0 0 24 24"
        fill={i < n ? '#f0883e' : '#30363d'}>
        <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" />
      </svg>
    ))}
  </span>
);

// ── Skeleton loader ───────────────────────────────────────────────────────
const SkeletonCard = () => (
  <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
    <div className="skeleton" style={{ height: 14, width: '60%' }} />
    <div className="skeleton" style={{ height: 11, width: '90%' }} />
    <div className="skeleton" style={{ height: 11, width: '75%' }} />
    <div className="skeleton" style={{ height: 11, width: '50%' }} />
  </div>
);

// ── Severity badge ────────────────────────────────────────────────────────
const SevBadge = ({ s }) => {
  const c = { HIGH: 'H', MEDIUM: 'M', LOW: 'L' }[s] || 'L';
  return <span className={cls('sev', 'sev-' + c)}>{s || 'INFO'}</span>;
};

// ── Toast notifications ───────────────────────────────────────────────────
const Toasts = ({ T, rm }) => (
  <div style={{ position: 'fixed', bottom: 20, right: 20, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 8, pointerEvents: 'none' }}>
    {T.map(t => (
      <div key={t.id} onClick={() => rm(t.id)}
        style={{
          pointerEvents: 'auto', padding: '10px 16px', borderRadius: 10,
          fontSize: 13, fontWeight: 500, cursor: 'pointer', boxShadow: '0 4px 24px #0009',
          background: t.type === 'error' ? '#2d1515' : t.type === 'success' ? '#0d2117' : '#0d1a2d',
          border: `1px solid ${t.type === 'error' ? '#f8514955' : t.type === 'success' ? '#3fb95055' : '#58a6ff55'}`,
          color: t.type === 'error' ? '#f85149' : t.type === 'success' ? '#3fb950' : '#58a6ff'
        }}>
        {t.msg}
      </div>
    ))}
  </div>
);

// ── Code viewer with Prism syntax highlight ───────────────────────────────
const CodeViewer = ({ source = '', lineno, endLineno, maxH = '100%' }) => {
  const ref = React.useRef();
  React.useEffect(() => {
    if (ref.current && window.Prism)
      ref.current.querySelectorAll('code.language-python').forEach(e => Prism.highlightElement(e));
  }, [source]);
  const lines = React.useMemo(() => source.split('\n'), [source]);
  if (!source) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#484f58', fontSize: 13 }}>
      No source available
    </div>
  );
  return (
    <div ref={ref} style={{ overflowY: 'auto', maxHeight: maxH, background: '#0d1117', borderRadius: 8, fontFamily: 'monospace' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 12.5 }}>
        <tbody>
          {lines.map((line, i) => {
            const ln = i + 1, hi = lineno && ln >= lineno && ln <= (endLineno || lineno);
            return (
              <tr key={i} className={hi ? 'hi-line' : ''}>
                <td style={{ paddingLeft: 12, paddingRight: 10, textAlign: 'right', color: '#484f58', minWidth: 42, verticalAlign: 'top', userSelect: 'none', fontSize: 11, paddingTop: 1, paddingBottom: 1 }}>{ln}</td>
                <td style={{ paddingRight: 16, verticalAlign: 'top', whiteSpace: 'pre-wrap', wordBreak: 'break-all', paddingTop: 1, paddingBottom: 1 }}>
                  <code className="language-python">{line}</code>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

// ── Summarization progress overlay ────────────────────────────────────────
const SumProgress = ({ status }) => {
  if (!status || status.finished) return null;
  return (
    <div style={{ position: 'absolute', inset: 0, background: '#0d111788', backdropFilter: 'blur(4px)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20, zIndex: 50 }}>
      <div className="card anim-glow" style={{ maxWidth: 380, width: '90%', textAlign: 'center', padding: 28 }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>🤖</div>
        <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 6 }}>AI Summarizing Your Code</div>
        <div style={{ fontSize: 12, color: '#8b949e', marginBottom: 16 }}>{status.stage || 'Working…'}</div>
        <div className="prog-bar" style={{ marginBottom: 10 }}>
          <div className="prog-fill anim-pulse" style={{ width: '65%' }} />
        </div>
        <div style={{ fontSize: 11, color: '#484f58' }}>Using gemini-2.0-flash-lite · You can browse the tree while this runs</div>
        {status.error && (
          <div style={{ marginTop: 12, fontSize: 11, color: '#f85149', background: '#f8514910', borderRadius: 6, padding: '6px 10px' }}>
            ⚠ {status.error}
          </div>
        )}
      </div>
    </div>
  );
};

// ── Drop zone ─────────────────────────────────────────────────────────────
const DropZone = ({ onFile, uploading, progress, large = false }) => {
  const [drag, setDrag] = React.useState(false);
  const inp = React.useRef();
  return (
    <div className={cls('dropzone', drag && 'drag')}
      style={large ? { padding: '32px 24px' } : {}}
      onDragOver={e => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={e => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) onFile(f); }}
      onClick={() => !uploading && inp.current?.click()}>
      <input ref={inp} type="file" accept=".zip" style={{ display: 'none' }}
        onChange={e => e.target.files[0] && onFile(e.target.files[0])} />
      {uploading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <Spin sz={32} />
          <div style={{ fontSize: 13, color: '#8b949e', fontWeight: 500 }}>{progress?.stage || 'Processing…'}</div>
          <div className="prog-bar" style={{ width: '100%' }}>
            <div className="prog-fill" style={{ width: `${progress?.pct || 15}%` }} />
          </div>
          <div style={{ fontSize: 11, color: '#484f58' }}>{progress?.pct || 0}%</div>
        </div>
      ) : (
        <>
          <div style={{ fontSize: large ? 36 : 26, marginBottom: 8 }}>📦</div>
          <div style={{ fontSize: large ? 14 : 12, fontWeight: 600, color: '#c9d1d9' }}>Drop .zip here</div>
          <div style={{ fontSize: 11, color: '#8b949e', marginTop: 3 }}>or click to browse · Only .zip files</div>
        </>
      )}
    </div>
  );
};
