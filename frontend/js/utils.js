// js/utils.js — Shared utilities and constants for CodeAtlas frontend
const API = 'http://localhost:8000/api';

// Helper: join class names
const cls = (...a) => a.filter(Boolean).join(' ');
// Helper: basename from path
const bn = p => p ? p.replace(/\\/g, '/').split('/').pop() : '';
// Helper: short string
const short = (s, n = 110) => s ? (s.length > n ? s.slice(0, n) + '…' : s) : '';

// ── Toast hook ────────────────────────────────────────────────────────────
function useToast() {
  const [T, setT] = React.useState([]);
  const add = React.useCallback((msg, type = 'info') => {
    const id = Date.now() + Math.random();
    setT(p => [...p, { id, msg, type }]);
    setTimeout(() => setT(p => p.filter(t => t.id !== id)), 5000);
  }, []);
  const rm = React.useCallback(id => setT(p => p.filter(t => t.id !== id)), []);
  return { toasts: T, toast: add, rmToast: rm };
}

// ── Level config ──────────────────────────────────────────────────────────
const LEVELS = {
  FILE:          { icon: '📄', color: '#58a6ff', label: 'File' },
  BLOCK:         { icon: '🔷', color: '#bc8cff', label: 'Block' },
  LOGICAL_BLOCK: { icon: '🔶', color: '#d29922', label: 'Logic' },
  FUNCTION:      { icon: '🔹', color: '#3fb950', label: 'Function' },
};

// ── Build tree from function_tree ─────────────────────────────────────────
function buildTree(ft) {
  if (!ft?.files) return [];
  return Object.entries(ft.files).map(([fp, fn]) => ({
    id: fp, name: bn(fp), level: 'FILE',
    source: fn.source, summary: fn.summary, file: fp,
    entry_point: fn.entry_point,
    children: [
      ...Object.entries(fn.blocks || {}).map(([id, b]) => ({
        id, name: b.name || id, level: 'BLOCK',
        lineno: b.lineno, endLineno: b.end_lineno,
        source: b.source_snippet, summary: b.summary, file: fp, children: []
      })),
      ...Object.entries(fn.logical_blocks || {}).map(([id, l]) => ({
        id, name: `${l.type || 'block'} @ L${l.lineno}`, level: 'LOGICAL_BLOCK',
        lineno: l.lineno, endLineno: l.end_lineno,
        source: l.source_snippet, summary: l.summary, file: fp, children: []
      })),
      ...Object.entries(fn.functions || {}).map(([id, f]) => ({
        id, name: f.name || id, level: 'FUNCTION',
        lineno: f.lineno, endLineno: f.end_lineno,
        source: f.source_snippet, summary: f.summary, file: fp,
        callers: f.callers || [], callees: f.callees || [], children: []
      })),
    ]
  }));
}
