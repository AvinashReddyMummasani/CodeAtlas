// js/tabs.js — Center pane tab components

// ── Welcome / Home tab ────────────────────────────────────────────────────
const WelcomeHome = ({ onUpload, uploading, progress }) => (
  <div style={{ height: '100%', overflowY: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 40, gap: 30 }}>
    <div style={{ textAlign: 'center' }}>
      <div style={{ width: 76, height: 76, borderRadius: 20, background: 'linear-gradient(135deg,#1f6feb 0%,#388bfd 50%,#bc8cff 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 38, margin: '0 auto 16px', boxShadow: '0 8px 32px #1f6feb44' }}>🗺️</div>
      <h1 style={{ fontSize: 30, fontWeight: 800, color: '#e6edf3', letterSpacing: '-.5px' }}>CodeAtlas</h1>
      <p style={{ fontSize: 13, color: '#8b949e', marginTop: 6 }}>AI-powered Python code analysis &amp; documentation platform</p>
    </div>

    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, maxWidth: 560, width: '100%' }}>
      {[
        { e: '🌳', t: 'Layered Overview', d: 'File→Block→Function drill-down with AI summaries', c: '#58a6ff' },
        { e: '📊', t: 'Project Report', d: 'CVE scan + AI-graded findings with remediation', c: '#f0883e' },
        { e: '⚡', t: 'Optimality Check', d: 'Complexity analysis &amp; refactoring suggestions', c: '#d29922' },
        { e: '💥', t: 'Blast Radius', d: 'Call-graph risk score 0–10 with impact analysis', c: '#f85149' },
        { e: '🌊', t: 'Execution Flow', d: 'Trace entry-point → function paths visually', c: '#bc8cff' },
        { e: '💬', t: 'RAG Chat', d: 'Natural-language Q&A grounded in your code', c: '#3fb950' },
      ].map(({ e, t, d, c }) => (
        <div key={t} style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: 14, cursor: 'default', transition: 'border .15s' }}
          onMouseEnter={ev => ev.currentTarget.style.borderColor = c + '66'}
          onMouseLeave={ev => ev.currentTarget.style.borderColor = '#30363d'}>
          <div style={{ fontSize: 22, marginBottom: 6 }}>{e}</div>
          <div style={{ fontSize: 12, fontWeight: 600, color: c, marginBottom: 4 }}>{t}</div>
          <div style={{ fontSize: 11, color: '#8b949e', lineHeight: 1.5 }} dangerouslySetInnerHTML={{ __html: d }} />
        </div>
      ))}
    </div>

    <div style={{ maxWidth: 380, width: '100%' }}>
      <DropZone onFile={onUpload} uploading={uploading} progress={progress} large />
    </div>

    <div style={{ textAlign: 'center', fontSize: 11, color: '#484f58', lineHeight: 1.8 }}>
      Strictly static analysis — your code is <strong style={{ color: '#e6edf3' }}>never executed or imported</strong><br />
      <AIBadge />
    </div>
  </div>
);

// ── Overview tab ──────────────────────────────────────────────────────────
const OverviewTab = ({ tree, node }) => {
  if (!tree) return <WelcomeHint />;
  if (!node) return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12, color: '#484f58' }}>
      <span style={{ fontSize: 52 }}>🌳</span>
      <div style={{ fontSize: 14, color: '#8b949e' }}>Click any node in the left tree to explore it</div>
    </div>
  );

  const cfg = LEVELS[node.level] || LEVELS.FUNCTION;
  const LEVEL_ORDER = ['FILE', 'BLOCK', 'LOGICAL_BLOCK', 'FUNCTION'];
  const breadcrumb = LEVEL_ORDER.slice(0, LEVEL_ORDER.indexOf(node.level) + 1).map(l => LEVELS[l].label).join(' › ');

  return (
    <div className="anim-fade" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '12px 20px', borderBottom: '1px solid #30363d', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 20 }}>{cfg.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 15, color: '#e6edf3', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{node.name}</div>
          <div style={{ fontSize: 11, color: '#8b949e', marginTop: 1 }}>{breadcrumb} · {bn(node.file)}{node.lineno ? ` :${node.lineno}` : ''}</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          {node.entry_point && <span style={{ fontSize: 10, background: '#3fb95022', color: '#3fb950', border: '1px solid #3fb95044', borderRadius: 4, padding: '2px 8px', fontWeight: 600 }}>ENTRY POINT</span>}
          <AIBadge />
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {/* AI Summary */}
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #21262d', flexShrink: 0 }}>
          <div className="sec-hdr">AI Summary</div>
          <div style={{ background: '#0d1117', borderRadius: 8, padding: 14, border: '1px solid #21262d' }}>
            {node.summary
              ? <p style={{ fontSize: 13.5, color: '#c9d1d9', lineHeight: 1.75 }}>{node.summary}</p>
              : <p style={{ fontSize: 13, color: '#484f58', fontStyle: 'italic' }}>Summary not yet available — AI is still processing, or click "Retry AI" in the top bar.</p>
            }
          </div>
          {/* Call relations */}
          {node.level === 'FUNCTION' && (node.callers?.length > 0 || node.callees?.length > 0) && (
            <div style={{ marginTop: 10, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              {node.callers?.length > 0 && (
                <div style={{ fontSize: 11 }}>
                  <span style={{ color: '#8b949e' }}>Called by: </span>
                  {node.callers.slice(0, 5).map((c, i) => <span key={i} style={{ fontFamily: 'monospace', color: '#bc8cff', marginRight: 4 }}>{c.split('::').pop()}</span>)}
                  {node.callers.length > 5 && <span style={{ color: '#484f58' }}>+{node.callers.length - 5}</span>}
                </div>
              )}
              {node.callees?.length > 0 && (
                <div style={{ fontSize: 11 }}>
                  <span style={{ color: '#8b949e' }}>Calls: </span>
                  {node.callees.slice(0, 5).map((c, i) => <span key={i} style={{ fontFamily: 'monospace', color: '#3fb950', marginRight: 4 }}>{c.split('::').pop()}</span>)}
                  {node.callees.length > 5 && <span style={{ color: '#484f58' }}>+{node.callees.length - 5}</span>}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Code viewer */}
        <div style={{ flex: 1, overflow: 'hidden', padding: '12px 20px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div className="sec-hdr">Source Code
            {node.lineno && <span style={{ fontWeight: 400, color: '#484f58', marginLeft: 8 }}>Lines {node.lineno}–{node.endLineno || node.lineno}</span>}
          </div>
          <div style={{ flex: 1, overflow: 'hidden', border: '1px solid #21262d', borderRadius: 8 }}>
            <CodeViewer source={node.source || node.source_snippet} lineno={node.lineno} endLineno={node.endLineno} maxH="100%" />
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Welcome hint (inside Overview when no project) ────────────────────────
const WelcomeHint = () => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 20, padding: 32, textAlign: 'center' }}>
    <div style={{ fontSize: 56 }}>🗺️</div>
    <div>
      <div style={{ fontWeight: 700, fontSize: 22, color: '#e6edf3', marginBottom: 6 }}>Welcome to CodeAtlas</div>
      <div style={{ fontSize: 13, color: '#8b949e', lineHeight: 1.7 }}>Upload a Python .zip project using the sidebar.<br />CodeAtlas will parse, analyze, and summarize your entire codebase.</div>
    </div>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 10, maxWidth: 480, width: '100%' }}>
      {[['🔍 Layered Overview', 'File → Block → Function drill-down', '#58a6ff'],
        ['📊 Project Report', 'CVE scan + severity-graded findings', '#f0883e'],
        ['⚡ Optimality Check', 'Complexity & refactoring suggestions', '#d29922'],
        ['💥 Blast Radius', 'Call-graph impact score 0–10', '#f85149'],
        ['🌊 Execution Flow', 'Trace entry-point → target path', '#bc8cff'],
        ['💬 RAG Chat', 'Natural-language Q&A over your code', '#3fb950'],
      ].map(([t, d, c]) => (
        <div key={t} style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: '12px 14px', textAlign: 'left' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: c, marginBottom: 3 }}>{t}</div>
          <div style={{ fontSize: 11, color: '#8b949e' }}>{d}</div>
        </div>
      ))}
    </div>
    <div style={{ fontSize: 11, color: '#484f58' }}>Strictly static analysis — your code is never executed.</div>
  </div>
);

// ── Detail tab (Optimality + Risk) ────────────────────────────────────────
const DetailTab = ({ sid, node, toast }) => {
  const [opt, setOpt] = React.useState(null);
  const [risk, setRisk] = React.useState(null);
  const [lOpt, setLOpt] = React.useState(false);
  const [lRisk, setLRisk] = React.useState(false);

  const doOpt = async () => {
    if (!node?.id) return; setLOpt(true); setOpt(null);
    try {
      const r = await fetch(`${API}/session/${sid}/optimize`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ func_id: node.id }) });
      const d = await r.json(); if (d.error) toast('Optimality: ' + d.error, 'error'); else setOpt(d);
    } catch { toast('Optimality check failed', 'error'); } finally { setLOpt(false); }
  };

  const doRisk = async () => {
    if (!node?.id) return; setLRisk(true); setRisk(null);
    try {
      const r = await fetch(`${API}/session/${sid}/risk`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ func_id: node.id }) });
      const d = await r.json(); if (d.error) toast('Risk: ' + d.error, 'error'); else setRisk(d);
    } catch { toast('Risk check failed', 'error'); } finally { setLRisk(false); }
  };

  if (!node || node.level !== 'FUNCTION') return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12, color: '#484f58' }}>
      <span style={{ fontSize: 52 }}>⚡</span>
      <div style={{ fontSize: 14, color: '#8b949e' }}>Select a <strong style={{ color: '#3fb950' }}>function</strong> from the tree to analyze</div>
    </div>
  );

  const RatingLabel = { 1: 'Poor', 2: 'Below Avg', 3: 'Average', 4: 'Good', 5: 'Excellent' };
  const RatingColor = { 1: '#f85149', 2: '#f0883e', 3: '#d29922', 4: '#58a6ff', 5: '#3fb950' };
  const rating = opt?.optimality?.rating || 0;
  const riskScore = risk?.risk_score || 0;
  const tier = risk?.risk_tier || 'LOW';
  const tierColor = { HIGH: '#f85149', MEDIUM: '#d29922', LOW: '#3fb950' }[tier];

  return (
    <div className="anim-fade" style={{ height: '100%', overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 15, color: '#3fb950' }}>🔹 {node.name}</span>
        <span style={{ fontSize: 11, color: '#8b949e' }}>{bn(node.file)} :{node.lineno}</span>
        <AIBadge />
      </div>

      {/* Optimality card */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div style={{ fontWeight: 600, fontSize: 13 }}>⚡ Function Optimality</div>
          <button className="btn btn-blue" onClick={doOpt} disabled={lOpt}>
            {lOpt ? <Spin sz={12} /> : '🔍'}{lOpt ? 'Analyzing…' : 'Check Optimality'}
          </button>
        </div>

        {lOpt && <SkeletonCard />}

        {opt?.optimality && !lOpt && (
          <div className="anim-fade" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 12, background: '#0d1117', borderRadius: 8, border: '1px solid #21262d' }}>
              <div style={{ width: 46, height: 46, borderRadius: '50%', background: `${RatingColor[rating]}22`, border: `2px solid ${RatingColor[rating]}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 20, color: RatingColor[rating] }}>{rating}</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 15, color: RatingColor[rating] }}>{RatingLabel[rating] || '?'}</div>
                <Stars n={rating} />
              </div>
              <div style={{ marginLeft: 'auto', fontSize: 11, color: '#8b949e', textAlign: 'right' }}>
                {opt.optimality.time_complexity && <div>Time: <span style={{ color: '#bc8cff' }}>{opt.optimality.time_complexity}</span></div>}
                {opt.optimality.space_complexity && <div>Space: <span style={{ color: '#bc8cff' }}>{opt.optimality.space_complexity}</span></div>}
              </div>
            </div>

            {(opt.optimality.issues || []).map((iss, i) => (
              <div key={i} style={{ background: '#0d1117', borderRadius: 8, padding: 10, border: '1px solid #21262d' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: '#d29922', textTransform: 'uppercase', background: '#d2992215', padding: '1px 6px', borderRadius: 4 }}>{iss.type}</span>
                  {iss.line_hint && <span style={{ fontSize: 11, color: '#484f58' }}>line {iss.line_hint}</span>}
                </div>
                <div style={{ fontSize: 12.5, color: '#c9d1d9' }}>{iss.description}</div>
              </div>
            ))}

            {(opt.optimality.refactoring_suggestions || []).map((s, i) => (
              <div key={i} style={{ background: '#0a1f0a', borderRadius: 8, padding: 12, border: '1px solid #3fb95033' }}>
                <div style={{ fontSize: 11, color: '#3fb950', fontWeight: 600, marginBottom: 6 }}>💡 {s.description}</div>
                {s.code_example && (
                  <pre style={{ fontSize: 11.5, background: '#0d1117', borderRadius: 6, padding: 10, overflowX: 'auto', fontFamily: 'monospace', color: '#8b949e', border: '1px solid #30363d', margin: 0, whiteSpace: 'pre-wrap' }}>{s.code_example}</pre>
                )}
              </div>
            ))}
          </div>
        )}

        {!opt && !lOpt && <div style={{ fontSize: 12, color: '#484f58', textAlign: 'center', padding: '16px 0' }}>Click "Check Optimality" to get an AI rating and suggestions</div>}
      </div>

      {/* Risk card */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div style={{ fontWeight: 600, fontSize: 13 }}>💥 Blast Radius &amp; Risk Score</div>
          <button className="btn btn-red" onClick={doRisk} disabled={lRisk}>
            {lRisk ? <Spin sz={12} /> : '💥'}{lRisk ? 'Computing…' : 'Check Risk'}
          </button>
        </div>

        {lRisk && <SkeletonCard />}

        {risk && !lRisk && (
          <div className="anim-fade" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ background: '#0d1117', borderRadius: 8, padding: 14, border: '1px solid #21262d' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <span style={{ fontWeight: 700, fontSize: 26, color: tierColor }}>{riskScore.toFixed(1)}<span style={{ fontSize: 13, color: '#8b949e' }}>/10</span></span>
                <span style={{ fontSize: 12, fontWeight: 700, padding: '3px 12px', borderRadius: 6, background: `${tierColor}22`, color: tierColor, border: `1px solid ${tierColor}44` }}>{tier} RISK</span>
              </div>
              <div className="prog-bar">
                <div className="gauge-fill" style={{ width: `${riskScore * 10}%`, background: `linear-gradient(90deg,${tierColor}88,${tierColor})` }} />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {[['Functions Affected', risk.dependent_count || 0, '🔹'], ['Files Affected', risk.file_spread || 0, '📄']].map(([l, v, e]) => (
                <div key={l} style={{ background: '#0d1117', borderRadius: 8, padding: 12, border: '1px solid #21262d', textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: '#8b949e', marginBottom: 4 }}>{e} {l}</div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: '#e6edf3' }}>{v}</div>
                </div>
              ))}
            </div>

            {risk.blast_radius_narrative && <div style={{ fontSize: 12.5, color: '#c9d1d9', background: '#0d1117', borderRadius: 8, padding: 12, border: '1px solid #21262d', lineHeight: 1.65 }}>{risk.blast_radius_narrative}</div>}
            {risk.partial_graph && <div style={{ fontSize: 11, color: '#d29922', background: '#d2992210', borderRadius: 6, padding: 8, border: '1px solid #d2992230' }}>⚠ Partial graph — some files had syntax errors; score may be underestimated</div>}

            {(risk.affected_functions || []).length > 0 && (
              <div>
                <div className="sec-hdr">Affected Functions</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                  {risk.affected_functions.slice(0, 20).map((f, i) => (
                    <span key={i} style={{ background: '#21262d', border: '1px solid #30363d', color: '#8b949e', fontSize: 11, padding: '2px 7px', borderRadius: 5, fontFamily: 'monospace' }}>
                      {typeof f === 'string' ? f.split('::').pop() : f.name || f}
                    </span>
                  ))}
                  {risk.affected_functions.length > 20 && <span style={{ fontSize: 11, color: '#484f58' }}>+{risk.affected_functions.length - 20} more</span>}
                </div>
              </div>
            )}
          </div>
        )}

        {!risk && !lRisk && <div style={{ fontSize: 12, color: '#484f58', textAlign: 'center', padding: '16px 0' }}>Click "Check Risk" to see how changes propagate through the codebase</div>}
      </div>
    </div>
  );
};

// ── Flow tab ──────────────────────────────────────────────────────────────
const FlowTab = ({ sid, node, toast }) => {
  const [flow, setFlow] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [pi, setPi] = React.useState(0);

  const doFlow = async () => {
    if (!node?.id) return; setLoading(true); setFlow(null); setPi(0);
    try {
      const r = await fetch(`${API}/session/${sid}/flow`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ func_id: node.id }) });
      const d = await r.json(); if (d.error) toast(d.error, 'error'); else setFlow(d);
    } catch { toast('Flow analysis failed', 'error'); } finally { setLoading(false); }
  };

  if (!node || node.level !== 'FUNCTION') return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12, color: '#484f58' }}>
      <span style={{ fontSize: 52 }}>🌊</span>
      <div style={{ fontSize: 14, color: '#8b949e' }}>Select a <strong style={{ color: '#3fb950' }}>function</strong> to trace its execution flow</div>
    </div>
  );

  const paths = flow?.paths || [];
  const cur = paths[pi];

  return (
    <div className="anim-fade" style={{ height: '100%', overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>🌊 Execution Flow</div>
          <div style={{ fontSize: 12, color: '#8b949e', marginTop: 2 }}>Tracing paths to <span style={{ fontFamily: 'monospace', color: '#58a6ff' }}>{node.name}</span></div>
        </div>
        <button className="btn btn-purple" onClick={doFlow} disabled={loading}>
          {loading ? <Spin sz={12} /> : '🔍'}{loading ? 'Tracing paths…' : 'Trace Execution Flow'}
        </button>
      </div>

      {loading && <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}><SkeletonCard /><SkeletonCard /></div>}

      {flow && !loading && (
        <div className="anim-fade">
          {flow.dead_code_hint && (
            <div style={{ background: '#1a1500', border: '1px solid #d2992244', borderRadius: 10, padding: 16, fontSize: 13, color: '#d29922', lineHeight: 1.6 }}>
              <strong>⚠ No execution paths found.</strong><br />
              <span style={{ fontSize: 12, color: '#8b949e' }}>This function may be dead code, called dynamically (callbacks, importlib, __getattr__), or entry points weren't detected in this project.</span>
            </div>
          )}

          {paths.length > 1 && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 4 }}>
              <span className="sec-hdr" style={{ margin: 0 }}>Paths found:</span>
              {paths.map((_, i) => (
                <button key={i} onClick={() => setPi(i)}
                  style={{ padding: '4px 12px', borderRadius: 7, fontSize: 11, fontWeight: 600, cursor: 'pointer', border: `1px solid ${i === pi ? '#58a6ff' : '#30363d'}`, background: i === pi ? '#1f6feb' : '#21262d', color: i === pi ? '#fff' : '#8b949e' }}>
                  Path {i + 1}
                </button>
              ))}
              <span style={{ fontSize: 11, color: '#484f58', marginLeft: 'auto' }}>{flow.total_paths} path{flow.total_paths !== 1 ? 's' : ''}</span>
            </div>
          )}

          {cur && (
            <div className="card" style={{ overflowX: 'auto' }}>
              <div className="sec-hdr">Execution Path {pi + 1}</div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, paddingBottom: 4, flexWrap: 'wrap' }}>
                {cur.steps.map((step, i) => (
                  <React.Fragment key={step.func_id || i}>
                    <div className={cls('flow-step', i === 0 && 'entry', i === cur.steps.length - 1 && 'target')}>
                      <div style={{ fontSize: 10, color: '#8b949e', marginBottom: 4 }}>
                        {i === 0 ? '🟢 Entry Point' : i === cur.steps.length - 1 ? '🎯 Target' : `Step ${i + 1}`}
                      </div>
                      <div style={{ fontFamily: 'monospace', fontSize: 11.5, fontWeight: 700, color: '#e6edf3', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{step.name}</div>
                      <div style={{ fontSize: 10, color: '#484f58', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{bn(step.file)}</div>
                      {step.summary_short && <div style={{ fontSize: 10, color: '#8b949e', marginTop: 5, lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{step.summary_short}</div>}
                    </div>
                    {i < cur.steps.length - 1 && <span className="flow-arrow">→</span>}
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!flow && !loading && <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#484f58', fontSize: 13 }}>Click "Trace Execution Flow" to find how this function is reached from entry points</div>}
    </div>
  );
};

// ── Report tab ────────────────────────────────────────────────────────────
const ReportTab = ({ sid, toast }) => {
  const [rpt, setRpt] = React.useState(null);
  const [loading, setLoading] = React.useState(false);

  const gen = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/session/${sid}/report`, { method: 'POST' });
      const d = await r.json(); if (d.error) toast(d.error, 'error'); else setRpt(d);
    } catch { toast('Report generation failed', 'error'); } finally { setLoading(false); }
  };

  if (!sid) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#484f58', fontSize: 13 }}>Upload a project first</div>;

  const ReportItem = ({ item, isImprov }) => (
    <div style={{ background: '#0d1117', borderRadius: 8, padding: 12, border: '1px solid #21262d', marginBottom: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
        <SevBadge s={isImprov ? item.priority : item.severity} />
        <span style={{ fontWeight: 600, fontSize: 13, color: '#e6edf3' }}>{item.title}</span>
      </div>
      <p style={{ fontSize: 12.5, color: '#8b949e', lineHeight: 1.6, marginBottom: item.remediation || item.suggestion ? 8 : 0 }}>{item.description}</p>
      {(item.remediation || item.suggestion) && <div style={{ fontSize: 12, color: '#3fb950', borderTop: '1px solid #21262d', paddingTop: 8 }}>💡 {item.remediation || item.suggestion}</div>}
      {item.affected_code && <div style={{ marginTop: 6, fontSize: 11, fontFamily: 'monospace', color: '#484f58', background: '#161b2266', padding: '3px 8px', borderRadius: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.affected_code}</div>}
    </div>
  );

  const Section = ({ emoji, title, items, isImprov }) =>
    items?.length > 0 ? (
      <div className="card">
        <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12 }}>{emoji} {title} <span style={{ fontWeight: 400, color: '#484f58', fontSize: 12 }}>({items.length})</span></div>
        {items.map((item, i) => <ReportItem key={i} item={item} isImprov={isImprov} />)}
      </div>
    ) : null;

  return (
    <div className="anim-fade" style={{ height: '100%', overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10, flexShrink: 0 }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>📊 Project Health Report</div>
          <div style={{ fontSize: 12, color: '#8b949e', marginTop: 2 }}>Two-stage analysis: web CVE search + AI findings</div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {rpt && <button className="btn btn-green" onClick={() => window.open(`${API}/session/${sid}/report/export`, '_blank')}>⬇ Download .md</button>}
          <button className="btn btn-blue" onClick={gen} disabled={loading}>
            {loading ? <Spin sz={12} /> : '📊'}{loading ? 'Generating…' : 'Generate Report'}
          </button>
        </div>
      </div>

      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, gap: 16, color: '#8b949e' }}>
          <Spin sz={48} />
          <div style={{ fontSize: 15, fontWeight: 500 }}>Running two-stage analysis…</div>
          <div style={{ fontSize: 12, color: '#484f58', textAlign: 'center', lineHeight: 1.7 }}>
            Stage 1: Searching for CVEs and library vulnerabilities<br />
            Stage 2: AI synthesizing findings with remediation steps
          </div>
        </div>
      )}

      {rpt && !loading && (
        <div className="anim-fade" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {!rpt.web_search_used && <span className="no-web">⚠ Generated without live web verification</span>}
          <AIBadge />

          {rpt.report?.summary && (
            <div className="card" style={{ background: 'linear-gradient(135deg,#161b22,#0d1a2d)' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 10, gap: 12 }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>Executive Summary</div>
                <div style={{ textAlign: 'center', flexShrink: 0 }}>
                  <div style={{ fontSize: 34, fontWeight: 800, lineHeight: 1, color: (rpt.report?.overall_score || 0) >= 70 ? '#3fb950' : (rpt.report?.overall_score || 0) >= 40 ? '#d29922' : '#f85149' }}>{rpt.report?.overall_score || '—'}</div>
                  <div style={{ fontSize: 10, color: '#8b949e' }}>/ 100</div>
                </div>
              </div>
              <div className="prog-bar" style={{ marginBottom: 12 }}>
                <div className="prog-fill" style={{ width: `${rpt.report?.overall_score || 0}%`, background: (rpt.report?.overall_score || 0) >= 70 ? 'linear-gradient(90deg,#196c2e,#3fb950)' : (rpt.report?.overall_score || 0) >= 40 ? 'linear-gradient(90deg,#7d4e00,#d29922)' : 'linear-gradient(90deg,#8a1919,#f85149)' }} />
              </div>
              <p style={{ fontSize: 13, color: '#c9d1d9', lineHeight: 1.7 }}>{rpt.report.summary}</p>
            </div>
          )}

          <Section emoji="🔴" title="Vulnerabilities" items={rpt.report?.vulnerabilities} />
          <Section emoji="🟡" title="Code Smells" items={rpt.report?.code_smells} />
          <Section emoji="🔵" title="Improvement Suggestions" items={rpt.report?.improvements} isImprov />

          {(rpt.sources || []).length > 0 && (
            <div className="card">
              <div className="sec-hdr">Web Sources</div>
              {rpt.sources.slice(0, 6).map((s, i) => (
                <a key={i} href={s} target="_blank" rel="noopener noreferrer"
                  style={{ display: 'block', fontSize: 12, color: '#58a6ff', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textDecoration: 'none' }}
                  onMouseEnter={e => e.target.style.textDecoration = 'underline'}
                  onMouseLeave={e => e.target.style.textDecoration = 'none'}>{s}</a>
              ))}
            </div>
          )}
        </div>
      )}

      {!rpt && !loading && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: '#484f58' }}>
          <span style={{ fontSize: 56 }}>📊</span>
          <div style={{ fontSize: 15, color: '#8b949e', fontWeight: 500 }}>Generate a full project health report</div>
          <div style={{ fontSize: 12, color: '#484f58', textAlign: 'center', lineHeight: 1.7 }}>Searches for CVEs in your dependencies, then uses AI<br />to generate severity-graded findings with remediation steps.</div>
        </div>
      )}
    </div>
  );
};
