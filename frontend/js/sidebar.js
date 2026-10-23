// js/sidebar.js — Left sidebar: upload, tree, search

// ── Tree node component ───────────────────────────────────────────────────
const TreeNode = ({ node, depth = 0, onSel, selId, defaultOpen = false }) => {
  const [open, setOpen] = React.useState(defaultOpen || depth === 0);
  const has = node.children?.length > 0;
  const sel = selId === node.id;
  const cfg = LEVELS[node.level] || LEVELS.FUNCTION;
  return (
    <div>
      <div className={cls('tree-item', sel && 'selected')}
        style={{ display: 'flex', alignItems: 'center', gap: 6, padding: `4px ${8 + depth * 12}px` }}
        onClick={() => { has && setOpen(o => !o); onSel(node); }}>
        <span style={{ width: 12, textAlign: 'center', color: '#484f58', fontSize: 10, flexShrink: 0 }}>
          {has ? (open ? '▾' : '▸') : null}
        </span>
        <span style={{ flexShrink: 0, fontSize: 13 }}>{cfg.icon}</span>
        <span style={{ flex: 1, fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: sel ? '#58a6ff' : cfg.color }}>
          {node.name}
        </span>
        {node.entry_point && <span title="Entry point" style={{ fontSize: 9, background: '#3fb95022', color: '#3fb950', border: '1px solid #3fb95044', borderRadius: 3, padding: '0 4px' }}>ENTRY</span>}
        {node.lineno && <span style={{ fontSize: 10, color: '#484f58', flexShrink: 0 }}>:{node.lineno}</span>}
      </div>
      {open && has && (
        <div>{node.children.map(c => <TreeNode key={c.id} node={c} depth={depth + 1} onSel={onSel} selId={selId} />)}</div>
      )}
    </div>
  );
};

// ── Sidebar component ─────────────────────────────────────────────────────
const Sidebar = ({ sid, tree, sel, onSel, onUpload, uploading, progress, sumStatus }) => {
  const [q, setQ] = React.useState('');
  const [res, setRes] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const timer = React.useRef();
  const tdata = React.useMemo(() => tree ? buildTree(tree) : [], [tree]);

  React.useEffect(() => {
    clearTimeout(timer.current);
    if (!q || !sid) { setRes([]); return; }
    timer.current = setTimeout(async () => {
      setLoading(true);
      try {
        const r = await fetch(`${API}/session/${sid}/search?q=${encodeURIComponent(q)}`);
        setRes(await r.json());
      } catch { } finally { setLoading(false); }
    }, 320);
  }, [q, sid]);

  const pick = r => {
    const fn = tree?.all_functions?.[r.func_id];
    if (fn) onSel({ id: r.func_id, name: r.name, level: 'FUNCTION', lineno: fn.lineno, endLineno: fn.end_lineno, source: fn.source_snippet, summary: fn.summary, file: fn.file || fn.filepath, callers: fn.callers || [], callees: fn.callees || [] });
    setQ(''); setRes([]);
  };

  return (
    <div style={{ width: 268, minWidth: 268, display: 'flex', flexDirection: 'column', height: '100%', background: '#161b22', borderRight: '1px solid #30363d' }}>
      {/* Logo */}
      <div style={{ padding: '14px 14px 10px', borderBottom: '1px solid #30363d', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <div style={{ width: 34, height: 34, borderRadius: 8, background: 'linear-gradient(135deg,#1f6feb,#388bfd)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, boxShadow: '0 2px 12px #1f6feb44' }}>🗺️</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: '#e6edf3', lineHeight: 1.2 }}>CodeAtlas</div>
            <div style={{ fontSize: 10, color: '#8b949e' }}>AI Code Intelligence</div>
          </div>
        </div>
        <AIBadge />
      </div>

      {/* Upload */}
      <div style={{ padding: 10, borderBottom: '1px solid #30363d', flexShrink: 0 }}>
        <DropZone onFile={onUpload} uploading={uploading} progress={progress} />
        {sid && (
          <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <div style={{ fontSize: 11, color: '#8b949e' }}>
              <span style={{ color: '#484f58' }}>Session </span>
              <span style={{ fontFamily: 'monospace', color: '#58a6ff' }}>{sid.slice(0, 10)}…</span>
            </div>
            {tree && (
              <div style={{ fontSize: 11, color: '#8b949e', display: 'flex', gap: 10 }}>
                <span>📄 {Object.keys(tree.files || {}).length} files</span>
                <span>🔹 {Object.keys(tree.all_functions || {}).length} fns</span>
                {Object.keys(tree.syntax_errors || {}).length > 0 && <span style={{ color: '#f85149' }}>⚠ {Object.keys(tree.syntax_errors).length} errors</span>}
              </div>
            )}
            {/* Inline summarization status */}
            {sumStatus && !sumStatus.finished && (
              <div style={{ fontSize: 11, color: '#58a6ff', display: 'flex', alignItems: 'center', gap: 5, background: '#1f6feb10', borderRadius: 5, padding: '3px 7px', marginTop: 2 }}>
                <Spin sz={10} />{sumStatus.stage || 'AI working…'}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Search */}
      {tree && (
        <div style={{ padding: '8px 10px', borderBottom: '1px solid #30363d', flexShrink: 0, position: 'relative' }}>
          <div style={{ position: 'relative' }}>
            <span style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', fontSize: 13, color: '#484f58' }}>🔍</span>
            <input className="inp" style={{ paddingLeft: 30, fontSize: 12 }} placeholder="Search functions…"
              value={q} onChange={e => setQ(e.target.value)} />
            {loading && <span style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)' }}><Spin sz={11} /></span>}
          </div>
          {res.length > 0 && (
            <div style={{ position: 'absolute', left: 10, right: 10, top: '100%', marginTop: 4, background: '#21262d', border: '1px solid #30363d', borderRadius: 8, zIndex: 100, maxHeight: 220, overflowY: 'auto', boxShadow: '0 8px 32px #000a' }}>
              {res.map(r => (
                <div key={r.func_id} onClick={() => pick(r)}
                  style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid #30363d44', fontSize: 12 }}
                  className="tree-item">
                  <div style={{ color: '#3fb950', fontFamily: 'monospace', fontWeight: 600 }}>{r.name}</div>
                  <div style={{ color: '#8b949e', fontSize: 11 }}>{bn(r.file)} :{r.lineno}</div>
                  {r.summary_short && <div style={{ color: '#484f58', fontSize: 11, marginTop: 2 }}>{r.summary_short}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tree */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '4px 4px 8px' }}>
        {!tree ? (
          <div style={{ padding: 20, textAlign: 'center', color: '#484f58', fontSize: 12 }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>🌲</div>
            Upload a .zip to explore your codebase
          </div>
        ) : tdata.map(n => <TreeNode key={n.id} node={n} depth={0} onSel={onSel} selId={sel?.id} />)}
        {tree?.syntax_errors && Object.keys(tree.syntax_errors).length > 0 && (
          <div style={{ margin: '8px 4px', padding: 10, background: '#f8514910', border: '1px solid #f8514933', borderRadius: 8, fontSize: 11 }}>
            <div style={{ color: '#f85149', fontWeight: 600, marginBottom: 4 }}>⚠ Syntax Errors</div>
            {Object.keys(tree.syntax_errors).map(f => (
              <div key={f} style={{ color: '#8b949e', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{bn(f)}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
