// js/tabs.js — Main workspace tabs: Interactive Graph Tree Studio, Detail, Flow, Report

// ── Welcome / Home tab ────────────────────────────────────────────────────
const WelcomeHome = ({ onUpload, uploading, progress, sid, tree, onNavigate, onOpenChat }) => {
  const cards = [
    {
      e: '🗺️',
      t: 'Graph Tree Explorer',
      subtitle: 'Visual Architecture Map',
      d: 'Interactive 2D graph tree with pan & zoom, collapsible branches, and 5 granularity levels',
      c: '#58a6ff',
      tab: 'overview'
    },
    {
      e: '📊',
      t: 'Project Report',
      subtitle: 'Security & Architectural Audit',
      d: 'Two-stage CVE vulnerability scan + severity-graded findings with Markdown export',
      c: '#f0883e',
      tab: 'report'
    },
    {
      e: '⚡',
      t: 'Optimality Check',
      subtitle: 'Complexity & Refactoring',
      d: 'Time & space complexity scoring with automated refactoring suggestions',
      c: '#d29922',
      tab: 'detail'
    },
    {
      e: '💥',
      t: 'Blast Radius Risk',
      subtitle: 'Call-Graph Impact 0–10',
      d: 'Measure ripple effects and affected dependencies if a function changes',
      c: '#f85149',
      tab: 'detail'
    },
    {
      e: '🌊',
      t: 'Execution Flow',
      subtitle: 'Root-to-Function Paths',
      d: 'Step-by-step playback of execution paths with live graph tree node highlighting',
      c: '#bc8cff',
      tab: 'flow'
    },
    {
      e: '💬',
      t: 'Explorer RAG Chat',
      subtitle: 'Codebase Assistant',
      d: 'Ask questions grounded in your code with direct source line citations',
      c: '#3fb950',
      tab: 'chat'
    },
  ];

  return (
    <div style={{ height: '100%', overflowY: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '36px 20px', gap: 24 }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ width: 76, height: 76, borderRadius: 20, background: 'linear-gradient(135deg,#1f6feb 0%,#388bfd 50%,#bc8cff 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 38, margin: '0 auto 14px', boxShadow: '0 8px 32px #1f6feb44' }}>🗺️</div>
        <h1 style={{ fontSize: 30, fontWeight: 800, color: '#e6edf3', letterSpacing: '-.5px' }}>CodeAtlas</h1>
        <p style={{ fontSize: 13.5, color: '#8b949e', marginTop: 4 }}>AI-Powered Python Code Analysis, Interactive Graph Tree &amp; Architecture Map</p>
      </div>

      {/* Prominent Active Project Banner if tree is already loaded */}
      {tree && (
        <div className="anim-fade" style={{ background: 'linear-gradient(135deg, #1f6feb22, #58a6ff11)', border: '1px solid #58a6ff55', borderRadius: 12, padding: '16px 22px', maxWidth: 660, width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14, boxShadow: '0 4px 20px #1f6feb15' }}>
          <div>
            <div style={{ fontSize: 11, color: '#58a6ff', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>🚀 Project Loaded &amp; Ready</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#e6edf3', marginTop: 3 }}>
              📦 {Object.keys(tree.files || {}).length} Python Files · {Object.keys(tree.all_functions || {}).length} Functions Analyzed
            </div>
            <div style={{ fontSize: 11.5, color: '#8b949e', marginTop: 2 }}>
              Explore the visual 2D Graph Tree with pan &amp; zoom, step through execution flows, or run AI audits.
            </div>
          </div>
          <button
            className="btn btn-solid-blue"
            onClick={() => onNavigate && onNavigate('overview')}
            style={{ padding: '8px 18px', fontSize: 13, flexShrink: 0, fontWeight: 700 }}
          >
            🗺️ Open Graph Tree →
          </button>
        </div>
      )}

      {/* 6 Clickable Feature Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, maxWidth: 660, width: '100%' }}>
        {cards.map(({ e, t, subtitle, d, c, tab }) => (
          <div
            key={t}
            onClick={() => {
              if (tab === 'chat') {
                if (onOpenChat) onOpenChat();
              } else if (onNavigate) {
                onNavigate(tab);
              }
            }}
            style={{
              background: '#161b22',
              border: '1px solid #30363d',
              borderRadius: 12,
              padding: 16,
              cursor: 'pointer',
              transition: 'all .18s ease',
              textAlign: 'left',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
            onMouseEnter={ev => {
              ev.currentTarget.style.borderColor = c + 'aa';
              ev.currentTarget.style.transform = 'translateY(-2px)';
              ev.currentTarget.style.background = '#1a2230';
            }}
            onMouseLeave={ev => {
              ev.currentTarget.style.borderColor = '#30363d';
              ev.currentTarget.style.transform = 'none';
              ev.currentTarget.style.background = '#161b22';
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 24 }}>{e}</span>
                <span style={{ fontSize: 10, color: c, background: c + '18', padding: '2px 6px', borderRadius: 4, fontWeight: 700 }}>
                  OPEN ➔
                </span>
              </div>
              <div style={{ fontSize: 13.5, fontWeight: 700, color: '#e6edf3', marginBottom: 2 }}>{t}</div>
              <div style={{ fontSize: 10.5, color: c, fontWeight: 600, marginBottom: 6 }}>{subtitle}</div>
              <div style={{ fontSize: 11, color: '#8b949e', lineHeight: 1.5 }} dangerouslySetInnerHTML={{ __html: d }} />
            </div>
          </div>
        ))}
      </div>

      <div style={{ maxWidth: 420, width: '100%' }}>
        <DropZone onFile={onUpload} uploading={uploading} progress={progress} large />
      </div>

      <div style={{ textAlign: 'center', fontSize: 11, color: '#484f58', lineHeight: 1.8 }}>
        Strictly static AST analysis — your code is <strong style={{ color: '#e6edf3' }}>never executed or imported</strong><br />
        <AIBadge />
      </div>
    </div>
  );
};

// ── Graph Tree Layout Engine (Walker / Reingold-Tilford Horizontal Tree) ──
function layoutGraphTree(rootNode, openMap, levelFilter = 'ALL', searchQuery = '') {
  if (!rootNode) return { nodes: [], links: [], totalWidth: 800, totalHeight: 600 };

  const nodeWidth = 260;
  const nodeHeight = 80;
  const gapX = 85;
  const gapY = 24;

  let currentY = 40;
  const nodes = [];
  const links = [];

  function postOrder(node, depth = 0) {
    const hasChildren = node.children && node.children.length > 0;
    // Default open: Project, Files, and Classes open; Functions closed unless toggled
    const defaultOpen = depth < 3;
    const isOpen = openMap[node.id] !== undefined ? openMap[node.id] : defaultOpen;

    let validChildren = node.children || [];
    if (levelFilter !== 'ALL') {
      validChildren = validChildren.filter(c => {
        if (c.level === levelFilter) return true;
        const flat = flattenTree([c]);
        return flat.some(f => f.level === levelFilter);
      });
    }

    const childrenToRender = (isOpen && hasChildren) ? validChildren : [];
    const laidChildren = [];

    for (const child of childrenToRender) {
      laidChildren.push(postOrder(child, depth + 1));
    }

    let y;
    if (laidChildren.length === 0) {
      y = currentY;
      currentY += nodeHeight + gapY;
    } else {
      y = (laidChildren[0].y + laidChildren[laidChildren.length - 1].y) / 2;
    }

    const x = 50 + depth * (nodeWidth + gapX);
    const result = {
      ...node,
      x,
      y,
      depth,
      hasChildren,
      isOpen,
      childrenCount: node.children ? node.children.length : 0
    };

    nodes.push(result);

    for (const child of laidChildren) {
      links.push({
        source: { x: x + nodeWidth, y: y + nodeHeight / 2 },
        target: { x: child.x, y: child.y + nodeHeight / 2 },
        sourceId: node.id,
        targetId: child.id
      });
    }

    return result;
  }

  postOrder(rootNode, 0);

  const maxDepth = nodes.reduce((m, n) => Math.max(m, n.depth), 0);
  const totalWidth = 50 + (maxDepth + 1) * (nodeWidth + gapX) + 200;
  const totalHeight = Math.max(currentY + 60, 600);

  return { nodes, links, totalWidth, totalHeight };
}

// ── Visual Graph Node Card Component (Floating in the 2D Canvas) ──────────
const GraphNodeCard = ({
  node,
  isSelected,
  onSelect,
  onToggleOpen,
  flowStepNumber,
  isFlowActive,
  onTraceFlow,
  searchQuery,
}) => {
  const cfg = LEVELS[node.level] || LEVELS.FUNCTION;
  const matchesSearch = searchQuery
    ? (node.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
       (node.summary && node.summary.toLowerCase().includes(searchQuery.toLowerCase())))
    : true;

  // Derive location, module, or count subtitle
  let locationInfo = '';
  if (node.level === 'PROJECT') {
    locationInfo = `Root Module · ${node.stats?.files || 0} files · ${node.stats?.functions || 0} fns`;
  } else if (node.level === 'FILE') {
    const dir = node.file ? node.file.replace(/\\/g, '/').split('/').slice(0, -1).join('/') : '';
    locationInfo = `${dir ? dir + '/' : ''}${bn(node.file)}`;
  } else if (node.level === 'BLOCK') {
    locationInfo = `${bn(node.file)}${node.lineno ? ` :L${node.lineno}` : ''}`;
  } else if (node.level === 'FUNCTION') {
    const cctx = node.class_ctx ? `${node.class_ctx}.` : '';
    const callers = node.callers?.length || 0;
    const callees = node.callees?.length || 0;
    locationInfo = `${cctx}${bn(node.file)}${node.lineno ? ` :L${node.lineno}` : ''} · ${callers} in / ${callees} out`;
  } else if (node.level === 'LOGICAL_BLOCK') {
    locationInfo = `L${node.lineno}–L${node.endLineno || node.lineno} · inside function`;
  }

  return (
    <div
      className={cls(
        'graph-node-card',
        isSelected && 'selected',
        isFlowActive && 'flow-active'
      )}
      style={{
        position: 'absolute',
        left: `${node.x}px`,
        top: `${node.y}px`,
        width: '260px',
        height: '80px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '9px 12px',
        opacity: searchQuery && !matchesSearch ? 0.35 : 1,
        borderLeft: `4px solid ${cfg.color}`,
        zIndex: isSelected ? 20 : isFlowActive ? 15 : 5,
      }}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(node);
      }}
    >
      {/* Top Header Row: Level Badge & Indicators */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ fontSize: 13 }}>{cfg.icon}</span>
          <span
            style={{
              fontSize: 9.5,
              fontWeight: 700,
              color: cfg.color,
              background: `${cfg.color}18`,
              padding: '1px 5px',
              borderRadius: 4,
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}
          >
            {cfg.label}
          </span>
          {node.entry_point && (
            <span style={{ fontSize: 9, fontWeight: 700, background: '#3fb95022', color: '#3fb950', border: '1px solid #3fb95044', borderRadius: 3, padding: '0 4px' }}>
              ENTRY
            </span>
          )}
        </div>

        {/* Right side: Flow Badge or Expand/Collapse Toggle Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {flowStepNumber !== undefined && (
            <span style={{ fontSize: 9.5, fontWeight: 700, padding: '1px 6px', borderRadius: 4, background: isFlowActive ? '#1f6feb' : '#21262d', color: isFlowActive ? '#fff' : '#58a6ff', border: `1px solid ${isFlowActive ? '#58a6ff' : '#30363d'}` }}>
              {flowStepNumber === 0 ? '🟢 ENTRY' : `STEP ${flowStepNumber + 1}`}
            </span>
          )}

          {node.hasChildren && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleOpen(node.id);
              }}
              style={{
                fontSize: 10,
                fontWeight: 600,
                background: node.isOpen ? '#21262d' : '#1f6feb33',
                color: node.isOpen ? '#8b949e' : '#58a6ff',
                border: `1px solid ${node.isOpen ? '#30363d' : '#58a6ff66'}`,
                borderRadius: 99,
                padding: '1px 7px',
                cursor: 'pointer',
              }}
              title={node.isOpen ? 'Click to collapse branch' : 'Click to expand branch'}
            >
              {node.isOpen ? `▾ ${node.childrenCount}` : `+ ${node.childrenCount}`}
            </button>
          )}
        </div>
      </div>

      {/* Middle: Title */}
      <div
        style={{
          fontFamily: node.level === 'FUNCTION' || node.level === 'BLOCK' ? 'monospace' : 'inherit',
          fontSize: 12.5,
          fontWeight: 700,
          color: isSelected ? '#58a6ff' : '#e6edf3',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
        title={node.name}
      >
        {node.name}
      </div>

      {/* Bottom Row: Location & Quick Action */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#8b949e' }}>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '175px' }} title={locationInfo}>
          {locationInfo}
        </span>

        {node.level === 'FUNCTION' && onTraceFlow && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onTraceFlow(node.id);
            }}
            style={{
              fontSize: 9.5,
              padding: '1px 5px',
              borderRadius: 3,
              background: '#bc8cff15',
              border: '1px solid #bc8cff44',
              color: '#bc8cff',
              cursor: 'pointer',
            }}
            title="Trace execution flow from entry point"
          >
            🌊 Trace
          </button>
        )}
      </div>
    </div>
  );
};

// ── 2D Graph Tree Canvas with Pan, Zoom & Bezier Curve Connectors ──────────
const GraphTreeView = ({
  rootNode,
  openMap,
  onToggleOpen,
  selNode,
  onSelectNode,
  levelFilter,
  searchQuery,
  flowActiveStep,
  flowStepMap,
  flowData,
  onTraceFlow,
}) => {
  const containerRef = React.useRef(null);
  const [zoom, setZoom] = React.useState(0.85);
  const [pan, setPan] = React.useState({ x: 40, y: 30 });
  const [isDragging, setIsDragging] = React.useState(false);
  const dragStartRef = React.useRef({ x: 0, y: 0 });

  // Calculate layout
  const { nodes, links, totalWidth, totalHeight } = React.useMemo(() => {
    return layoutGraphTree(rootNode, openMap, levelFilter, searchQuery);
  }, [rootNode, openMap, levelFilter, searchQuery]);

  // Set of node IDs in active flow path
  const flowPathIds = React.useMemo(() => {
    if (!flowData?.paths?.[0]?.steps) return new Set();
    return new Set(flowData.paths[0].steps.map(s => s.func_id));
  }, [flowData]);

  // Mouse pan handlers
  const handleMouseDown = (e) => {
    // Only pan if clicked on background canvas
    if (e.target.closest('.graph-node-card') || e.target.closest('.zoom-controls')) return;
    setIsDragging(true);
    dragStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Mouse wheel zoom handler
  const handleWheel = (e) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.08 : 0.92;
    setZoom(prev => Math.min(Math.max(prev * factor, 0.25), 2.2));
  };

  // Zoom control buttons
  const zoomIn = () => setZoom(z => Math.min(z + 0.15, 2.2));
  const zoomOut = () => setZoom(z => Math.max(z - 0.15, 0.25));
  const resetZoom = () => {
    setZoom(0.85);
    setPan({ x: 40, y: 30 });
  };
  const fitToScreen = () => {
    if (!containerRef.current) return;
    const w = containerRef.current.clientWidth || 800;
    const h = containerRef.current.clientHeight || 600;
    const scaleX = (w - 80) / totalWidth;
    const scaleY = (h - 80) / totalHeight;
    const fitScale = Math.min(scaleX, scaleY, 1.0);
    setZoom(Math.max(fitScale, 0.3));
    setPan({ x: 30, y: 20 });
  };

  return (
    <div
      ref={containerRef}
      className="graph-canvas-bg"
      style={{
        flex: 1,
        height: '100%',
        position: 'relative',
        overflow: 'hidden',
        cursor: isDragging ? 'grabbing' : 'grab',
        userSelect: 'none',
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
      {/* Zoom & Pan Floating Controls Toolbar */}
      <div
        className="zoom-controls"
        style={{
          position: 'absolute',
          bottom: 16,
          right: 16,
          zIndex: 40,
          background: '#161b22e6',
          backdropFilter: 'blur(8px)',
          border: '1px solid #30363d',
          borderRadius: 8,
          padding: '4px 8px',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          boxShadow: '0 4px 20px #00000088',
        }}
      >
        <button className="btn" style={{ padding: '3px 8px', fontSize: 12, background: '#21262d', color: '#c9d1d9' }} onClick={zoomIn} title="Zoom In">
          ➕
        </button>
        <span style={{ fontSize: 11, color: '#8b949e', fontFamily: 'monospace', minWidth: 42, textAlign: 'center' }}>
          {Math.round(zoom * 100)}%
        </span>
        <button className="btn" style={{ padding: '3px 8px', fontSize: 12, background: '#21262d', color: '#c9d1d9' }} onClick={zoomOut} title="Zoom Out">
          ➖
        </button>
        <button className="btn" style={{ padding: '3px 8px', fontSize: 11, background: '#21262d', color: '#c9d1d9' }} onClick={fitToScreen} title="Fit to Screen">
          📐 Fit
        </button>
        <button className="btn" style={{ padding: '3px 8px', fontSize: 11, background: '#21262d', color: '#c9d1d9' }} onClick={resetZoom} title="Reset View">
          🎯 Center
        </button>
      </div>

      {/* Scalable & Pannable World Group */}
      <div
        style={{
          position: 'absolute',
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: '0 0',
          width: `${totalWidth}px`,
          height: `${totalHeight}px`,
        }}
      >
        {/* SVG Bezier Connectors Layer */}
        <svg
          width={totalWidth}
          height={totalHeight}
          style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 1 }}
        >
          {links.map((link, idx) => {
            const midX = (link.source.x + link.target.x) / 2;
            const d = `M ${link.source.x} ${link.source.y} C ${midX} ${link.source.y}, ${midX} ${link.target.y}, ${link.target.x} ${link.target.y}`;
            const isFlowEdge = flowPathIds.has(link.sourceId) && flowPathIds.has(link.targetId);

            return (
              <path
                key={idx}
                d={d}
                fill="none"
                stroke={isFlowEdge ? '#388bfd' : '#30363d'}
                strokeWidth={isFlowEdge ? '3.5' : '1.8'}
                strokeOpacity={isFlowEdge ? '1' : '0.75'}
                strokeDasharray={isFlowEdge ? '8 4' : 'none'}
                className={isFlowEdge ? 'anim-flow-dash' : undefined}
                filter={isFlowEdge ? 'drop-shadow(0 0 6px #388bfd)' : undefined}
              />
            );
          })}
        </svg>

        {/* HTML Node Cards Layer */}
        {nodes.map(n => {
          const flowStepNumber = flowStepMap ? flowStepMap[n.id] : undefined;
          const isFlowActive = flowActiveStep !== null && flowStepNumber === flowActiveStep;

          return (
            <GraphNodeCard
              key={n.id}
              node={n}
              isSelected={selNode?.id === n.id}
              onSelect={onSelectNode}
              onToggleOpen={onToggleOpen}
              flowStepNumber={flowStepNumber}
              isFlowActive={isFlowActive}
              onTraceFlow={onTraceFlow}
              searchQuery={searchQuery}
            />
          );
        })}
      </div>
    </div>
  );
};

// ── Interactive Outline Tree Node Row (For List Outline Mode) ─────────────
const InteractiveTreeNode = ({
  node,
  depth = 0,
  selNode,
  onSelect,
  openMap,
  onToggleOpen,
  levelFilter,
  searchQuery,
  flowActiveStep,
  flowStepMap,
  callerHighlightIds = [],
  calleeHighlightIds = [],
  onTraceFlow,
}) => {
  const hasChildren = node.children && node.children.length > 0;
  const isOpen = openMap[node.id] !== undefined ? openMap[node.id] : (depth < 2);
  const isSelected = selNode?.id === node.id;
  const cfg = LEVELS[node.level] || LEVELS.FUNCTION;

  if (levelFilter !== 'ALL' && node.level !== 'PROJECT' && node.level !== levelFilter) {
    if (!hasChildren) return null;
  }

  const matchesSearch = searchQuery
    ? (node.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
       (node.summary && node.summary.toLowerCase().includes(searchQuery.toLowerCase())))
    : true;

  const flowStepNumber = flowStepMap ? flowStepMap[node.id] : undefined;
  const isFlowActive = flowActiveStep !== null && flowStepNumber === flowActiveStep;
  const isCaller = callerHighlightIds.includes(node.id);
  const isCallee = calleeHighlightIds.includes(node.id);

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <div
        className={cls(
          'tree-node-row',
          isSelected && 'selected',
          isFlowActive && 'flow-active',
          isCaller && 'highlight-caller',
          isCallee && 'highlight-callee'
        )}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '6px 10px',
          paddingLeft: `${10 + depth * 18}px`,
          cursor: 'pointer',
          borderRadius: 6,
          margin: '1px 4px',
          background: isFlowActive
            ? 'linear-gradient(90deg, #1f6feb33, #58a6ff11)'
            : isSelected
            ? '#1f6feb22'
            : isCaller
            ? '#bc8cff18'
            : isCallee
            ? '#3fb95018'
            : 'transparent',
          border: isFlowActive
            ? '1.5px solid #58a6ff'
            : isSelected
            ? '1px solid #1f6feb66'
            : isCaller
            ? '1px dashed #bc8cff66'
            : isCallee
            ? '1px dashed #3fb95066'
            : '1px solid transparent',
          opacity: searchQuery && !matchesSearch ? 0.35 : 1,
          transition: 'all 0.15s ease',
        }}
        onClick={(e) => {
          e.stopPropagation();
          if (hasChildren) {
            onToggleOpen(node.id);
          }
          onSelect(node);
        }}
      >
        <span
          style={{
            width: 16,
            height: 16,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 10,
            color: '#8b949e',
            borderRadius: 4,
            cursor: hasChildren ? 'pointer' : 'default',
            userSelect: 'none',
            background: hasChildren ? '#21262d' : 'transparent',
          }}
          onClick={(e) => {
            if (hasChildren) {
              e.stopPropagation();
              onToggleOpen(node.id);
            }
          }}
        >
          {hasChildren ? (isOpen ? '▼' : '▶') : '•'}
        </span>

        <span style={{ fontSize: 14, flexShrink: 0 }}>{cfg.icon}</span>

        <span
          style={{
            fontFamily: node.level === 'FUNCTION' || node.level === 'BLOCK' ? 'monospace' : 'inherit',
            fontSize: node.level === 'PROJECT' ? 13.5 : node.level === 'FILE' ? 12.5 : 12,
            fontWeight: node.level === 'PROJECT' ? 700 : (node.level === 'FILE' || node.level === 'BLOCK' ? 600 : 400),
            color: isSelected ? '#58a6ff' : cfg.color,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flex: 1,
          }}
          title={node.name}
        >
          {node.name}
        </span>

        {hasChildren && (
          <span style={{ fontSize: 10, color: '#8b949e', background: '#21262d', padding: '1px 6px', borderRadius: 4, flexShrink: 0 }}>
            {isOpen ? '▾' : '▸'} {node.children.length}
          </span>
        )}

        {flowStepNumber !== undefined && (
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              padding: '1px 7px',
              borderRadius: 5,
              background: isFlowActive ? '#1f6feb' : '#21262d',
              border: `1px solid ${isFlowActive ? '#58a6ff' : '#30363d'}`,
              color: isFlowActive ? '#fff' : '#58a6ff',
            }}
          >
            {flowStepNumber === 0 ? '🟢 ENTRY' : `STEP ${flowStepNumber + 1}`}
          </span>
        )}

        {node.entry_point && (
          <span style={{ fontSize: 9.5, fontWeight: 700, padding: '1px 6px', borderRadius: 4, background: '#3fb95022', color: '#3fb950', border: '1px solid #3fb95044' }}>
            ENTRY
          </span>
        )}

        {node.lineno ? (
          <span style={{ fontSize: 10.5, color: '#484f58', fontFamily: 'monospace', flexShrink: 0 }}>
            L{node.lineno}
          </span>
        ) : null}

        {node.level === 'FUNCTION' && onTraceFlow && (
          <button
            title="Trace Root Execution Flow to this function"
            style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, background: '#bc8cff15', border: '1px solid #bc8cff33', color: '#bc8cff', cursor: 'pointer', flexShrink: 0 }}
            onClick={(e) => {
              e.stopPropagation();
              onTraceFlow(node.id);
            }}
          >
            🌊 Trace
          </button>
        )}
      </div>

      {hasChildren && isOpen && (
        <div style={{ borderLeft: '1px solid #21262d', marginLeft: `${16 + depth * 18}px` }}>
          {node.children.map(c => (
            <InteractiveTreeNode
              key={c.id}
              node={c}
              depth={depth + 1}
              selNode={selNode}
              onSelect={onSelect}
              openMap={openMap}
              onToggleOpen={onToggleOpen}
              levelFilter={levelFilter}
              searchQuery={searchQuery}
              flowActiveStep={flowActiveStep}
              flowStepMap={flowStepMap}
              callerHighlightIds={callerHighlightIds}
              calleeHighlightIds={calleeHighlightIds}
              onTraceFlow={onTraceFlow}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// ── Interactive Project Tree & Graph Studio (Centerpiece of CodeAtlas) ────
const OverviewTab = ({ tree, node, sid, onSelectNode, toast, onJumpToFlow }) => {
  if (!tree) return <WelcomeHint />;

  // View Mode: 'graph' (2D Canvas with Pan & Zoom) | 'outline' (Collapsible List)
  const [viewMode, setViewMode] = React.useState('graph');

  // State for Tree Explorer
  const [openMap, setOpenMap] = React.useState({ PROJECT_ROOT: true });
  const [levelFilter, setLevelFilter] = React.useState('ALL');
  const [searchQuery, setSearchQuery] = React.useState('');
  const [inspectorTab, setInspectorTab] = React.useState('details');

  // Flow Control State integrated directly into the Tree
  const [flowMode, setFlowMode] = React.useState(false);
  const [flowData, setFlowData] = React.useState(null);
  const [flowActiveStep, setFlowActiveStep] = React.useState(0);
  const [isPlayingFlow, setIsPlayingFlow] = React.useState(false);
  const flowTimer = React.useRef(null);

  // In-Tree AI Chat State
  const [treeChatMsgs, setTreeChatMsgs] = React.useState([]);
  const [treeChatInp, setTreeChatInp] = React.useState('');
  const [treeChatLoading, setTreeChatLoading] = React.useState(false);

  // Call graph highlight state
  const [callerHighlightIds, setCallerHighlightIds] = React.useState([]);
  const [calleeHighlightIds, setCalleeHighlightIds] = React.useState([]);

  // Build full 5-level project tree
  const projectTree = React.useMemo(() => buildTree(tree), [tree]);
  const rootNode = projectTree[0] || null;

  // Selected node fallback to root if null
  const activeNode = node || rootNode;

  // Toggle node open/closed
  const toggleOpen = (id) => {
    setOpenMap(prev => ({ ...prev, [id]: prev[id] !== undefined ? !prev[id] : false }));
  };

  // Expand all nodes
  const expandAll = () => {
    const flat = flattenTree(projectTree);
    const newMap = {};
    flat.forEach(n => { newMap[n.id] = true; });
    setOpenMap(newMap);
  };

  // Collapse all except project root
  const collapseAll = () => {
    setOpenMap({ PROJECT_ROOT: true });
  };

  // Auto-expand ancestors when a node is selected
  React.useEffect(() => {
    if (activeNode?.id) {
      const ancestors = getNodeAncestors(projectTree, activeNode.id);
      if (ancestors.length > 0) {
        setOpenMap(prev => {
          const updated = { ...prev };
          ancestors.forEach(aId => { updated[aId] = true; });
          return updated;
        });
      }
    }
  }, [activeNode?.id, projectTree]);

  // Flow Step Mapping: node.id -> step index in flow
  const flowStepMap = React.useMemo(() => {
    if (!flowData?.paths?.[0]?.steps) return {};
    const map = {};
    flowData.paths[0].steps.forEach((s, idx) => {
      map[s.func_id] = idx;
    });
    return map;
  }, [flowData]);

  // Trace Flow for a target function
  const triggerFlow = async (targetFuncId) => {
    if (!sid || !targetFuncId) return;
    setFlowMode(true);
    setFlowActiveStep(0);
    setIsPlayingFlow(false);
    toast(`Tracing execution flow to ${targetFuncId.split('::').pop()}…`, 'info');
    try {
      const r = await fetch(`${API}/session/${sid}/flow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ func_id: targetFuncId })
      });
      const data = await r.json();
      if (data.error) {
        toast(data.error, 'error');
        setFlowData(null);
      } else {
        setFlowData(data);
        if (data.paths?.[0]?.steps?.length > 0) {
          const firstStep = data.paths[0].steps[0];
          const found = findNodeInTree(projectTree, firstStep.func_id);
          if (found) onSelectNode(found);
        }
      }
    } catch {
      toast('Execution flow analysis failed', 'error');
    }
  };

  const goToFlowStep = (idx) => {
    if (!flowData?.paths?.[0]?.steps) return;
    const steps = flowData.paths[0].steps;
    if (idx < 0 || idx >= steps.length) return;
    setFlowActiveStep(idx);
    const step = steps[idx];
    const found = findNodeInTree(projectTree, step.func_id);
    if (found) onSelectNode(found);
  };

  const togglePlayFlow = () => {
    setIsPlayingFlow(p => !p);
  };

  React.useEffect(() => {
    if (isPlayingFlow) {
      flowTimer.current = setInterval(() => {
        setFlowActiveStep(currentStep => {
          const steps = flowData?.paths?.[0]?.steps || [];
          if (currentStep + 1 >= steps.length) {
            setIsPlayingFlow(false);
            return currentStep;
          }
          const nextStep = currentStep + 1;
          const step = steps[nextStep];
          const found = findNodeInTree(projectTree, step.func_id);
          if (found) onSelectNode(found);
          return nextStep;
        });
      }, 1600);
    } else {
      clearInterval(flowTimer.current);
    }
    return () => clearInterval(flowTimer.current);
  }, [isPlayingFlow, flowData, projectTree, onSelectNode]);

  // In-Tree AI Chat Sender
  const sendTreeQuestion = async (customQ) => {
    const q = (customQ || treeChatInp).trim();
    if (!q || !sid || treeChatLoading) return;
    setTreeChatInp('');

    const contextPrefix = activeNode
      ? `Regarding ${activeNode.level} "${activeNode.name}" (ID: ${activeNode.id}${activeNode.file ? ` in ${activeNode.file}` : ''}): `
      : 'Regarding the entire codebase: ';

    const fullQuestion = contextPrefix + q;

    setTreeChatMsgs(prev => [...prev, { role: 'user', content: q, targetNode: activeNode?.name }]);
    setTreeChatLoading(true);

    try {
      const hist = treeChatMsgs.slice(-6).map(m => ({
        role: m.role === 'user' ? 'user' : 'model',
        content: m.content
      }));
      const r = await fetch(`${API}/session/${sid}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: fullQuestion, chat_history: hist })
      });
      const d = await r.json();
      setTreeChatMsgs(prev => [
        ...prev,
        { role: 'ai', content: d.answer || 'No answer generated.', cited: d.cited_functions || [] }
      ]);
    } catch {
      setTreeChatMsgs(prev => [
        ...prev,
        { role: 'ai', content: '⚠ Failed to query AI. Ensure the backend is reachable.', cited: [] }
      ]);
    } finally {
      setTreeChatLoading(false);
    }
  };

  // Toggle caller/callee highlights
  const toggleCallerHighlights = (callers) => {
    if (callerHighlightIds.length > 0) {
      setCallerHighlightIds([]);
    } else {
      setCallerHighlightIds(callers || []);
      setCalleeHighlightIds([]);
      toast(`Highlighted ${callers.length} callers in purple`, 'info');
    }
  };

  const toggleCalleeHighlights = (callees) => {
    if (calleeHighlightIds.length > 0) {
      setCalleeHighlightIds([]);
    } else {
      setCalleeHighlightIds(callees || []);
      setCallerHighlightIds([]);
      toast(`Highlighted ${callees.length} callees in green`, 'info');
    }
  };

  const activeCfg = LEVELS[activeNode?.level] || LEVELS.FUNCTION;

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden', background: '#0d1117' }}>
      {/* ── Left / Center Stage: Visual Graph Tree or Outline Tree ────────── */}
      <div style={{ flex: '1 1 54%', display: 'flex', flexDirection: 'column', borderRight: '1px solid #30363d', minWidth: 400, overflow: 'hidden' }}>
        
        {/* Top Tree Toolbar */}
        <div style={{ padding: '10px 14px', borderBottom: '1px solid #30363d', background: '#161b22', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
            {/* View Mode Toggle: Graph Tree Canvas vs Outline Tree */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ display: 'flex', background: '#0d1117', padding: 2, borderRadius: 6, border: '1px solid #30363d' }}>
                <button
                  onClick={() => setViewMode('graph')}
                  style={{
                    padding: '3px 10px',
                    borderRadius: 5,
                    fontSize: 11.5,
                    fontWeight: 600,
                    cursor: 'pointer',
                    background: viewMode === 'graph' ? '#1f6feb' : 'transparent',
                    color: viewMode === 'graph' ? '#fff' : '#8b949e',
                    border: 'none',
                  }}
                >
                  🗺️ Graph Tree Canvas
                </button>
                <button
                  onClick={() => setViewMode('outline')}
                  style={{
                    padding: '3px 10px',
                    borderRadius: 5,
                    fontSize: 11.5,
                    fontWeight: 600,
                    cursor: 'pointer',
                    background: viewMode === 'outline' ? '#1f6feb' : 'transparent',
                    color: viewMode === 'outline' ? '#fff' : '#8b949e',
                    border: 'none',
                  }}
                >
                  📑 Outline Tree
                </button>
              </div>

              <span style={{ fontSize: 11, color: '#8b949e', background: '#21262d', padding: '2px 8px', borderRadius: 99, border: '1px solid #30363d' }}>
                5 Levels
              </span>
            </div>

            {/* Tree Actions */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <button
                className="btn btn-blue"
                style={{ padding: '3px 8px', fontSize: 11 }}
                onClick={() => setFlowMode(m => !m)}
              >
                🌊 {flowMode ? 'Hide Flow' : 'Flow Control'}
              </button>
              <button
                className="btn"
                style={{ padding: '3px 8px', fontSize: 11, background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d' }}
                onClick={expandAll}
              >
                📂 Expand All
              </button>
              <button
                className="btn"
                style={{ padding: '3px 8px', fontSize: 11, background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d' }}
                onClick={collapseAll}
              >
                📁 Collapse
              </button>
            </div>
          </div>

          {/* Search & Level Filter Row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <input
                className="inp"
                style={{ fontSize: 11.5, padding: '5px 8px 5px 24px' }}
                placeholder="Search graph nodes by name or summary…"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              <span style={{ position: 'absolute', left: 7, top: '50%', transform: 'translateY(-50%)', fontSize: 11, color: '#8b949e' }}>🔍</span>
            </div>

            {/* Level Chips */}
            <div style={{ display: 'flex', gap: 4 }}>
              {[
                { id: 'ALL', label: 'All' },
                { id: 'FILE', label: '📄 Files' },
                { id: 'BLOCK', label: '🔷 Classes' },
                { id: 'FUNCTION', label: '🔹 Funcs' },
                { id: 'LOGICAL_BLOCK', label: '🔶 Logic' },
              ].map(lvl => (
                <button
                  key={lvl.id}
                  onClick={() => setLevelFilter(lvl.id)}
                  style={{
                    padding: '3px 8px',
                    borderRadius: 5,
                    fontSize: 10.5,
                    fontWeight: 600,
                    cursor: 'pointer',
                    background: levelFilter === lvl.id ? '#1f6feb' : '#21262d',
                    border: `1px solid ${levelFilter === lvl.id ? '#58a6ff' : '#30363d'}`,
                    color: levelFilter === lvl.id ? '#fff' : '#8b949e',
                  }}
                >
                  {lvl.label}
                </button>
              ))}
            </div>
          </div>

          {/* Flow Control Player Bar (Integrated on the Tree) */}
          {flowMode && (
            <div className="anim-slide" style={{ background: '#0d1117', border: '1px solid #1f6feb44', borderRadius: 8, padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#58a6ff', fontWeight: 600 }}>
                  <span>🌊 Flow Playback:</span>
                  <span>
                    {flowData?.paths?.[0]?.steps
                      ? `Step ${flowActiveStep + 1} of ${flowData.paths[0].steps.length}`
                      : 'Pick any function and click "Trace"'}
                  </span>
                </div>

                {flowData?.paths?.[0]?.steps && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <button
                      className="btn"
                      style={{ padding: '2px 7px', fontSize: 11, background: '#21262d', color: '#c9d1d9' }}
                      onClick={() => goToFlowStep(0)}
                      title="Jump to entry point"
                    >
                      ⏮
                    </button>
                    <button
                      className="btn"
                      style={{ padding: '2px 7px', fontSize: 11, background: '#21262d', color: '#c9d1d9' }}
                      onClick={() => goToFlowStep(flowActiveStep - 1)}
                      title="Previous step"
                    >
                      ◀
                    </button>
                    <button
                      className="btn btn-blue"
                      style={{ padding: '2px 10px', fontSize: 11 }}
                      onClick={togglePlayFlow}
                      title={isPlayingFlow ? 'Pause playback' : 'Play flow animation'}
                    >
                      {isPlayingFlow ? '⏸ Pause' : '▶ Play'}
                    </button>
                    <button
                      className="btn"
                      style={{ padding: '2px 7px', fontSize: 11, background: '#21262d', color: '#c9d1d9' }}
                      onClick={() => goToFlowStep(flowActiveStep + 1)}
                      title="Next step"
                    >
                      ▶
                    </button>
                    <button
                      className="btn"
                      style={{ padding: '2px 7px', fontSize: 11, background: '#21262d', color: '#c9d1d9' }}
                      onClick={() => goToFlowStep(flowData.paths[0].steps.length - 1)}
                      title="Jump to target"
                    >
                      ⏭
                    </button>
                    <button
                      className="btn btn-red"
                      style={{ padding: '2px 7px', fontSize: 10, marginLeft: 4 }}
                      onClick={() => setFlowMode(false)}
                      title="Close flow"
                    >
                      ✕
                    </button>
                  </div>
                )}
              </div>

              {/* Step Path Ribbon */}
              {flowData?.paths?.[0]?.steps && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, overflowX: 'auto', paddingBottom: 2 }}>
                  {flowData.paths[0].steps.map((s, idx) => (
                    <button
                      key={idx}
                      onClick={() => goToFlowStep(idx)}
                      style={{
                        padding: '2px 8px',
                        borderRadius: 4,
                        fontSize: 10,
                        fontFamily: 'monospace',
                        fontWeight: idx === flowActiveStep ? 700 : 500,
                        background: idx === flowActiveStep ? '#1f6feb' : '#161b22',
                        border: `1px solid ${idx === flowActiveStep ? '#58a6ff' : '#30363d'}`,
                        color: idx === flowActiveStep ? '#fff' : '#8b949e',
                        cursor: 'pointer',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {idx === 0 ? '🟢 ' : `${idx + 1}. `}{s.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Visual Graph Tree Canvas vs Outline Tree */}
        {viewMode === 'graph' ? (
          <GraphTreeView
            rootNode={rootNode}
            openMap={openMap}
            onToggleOpen={toggleOpen}
            selNode={activeNode}
            onSelectNode={onSelectNode}
            levelFilter={levelFilter}
            searchQuery={searchQuery}
            flowActiveStep={flowMode ? flowActiveStep : null}
            flowStepMap={flowMode ? flowStepMap : {}}
            flowData={flowData}
            onTraceFlow={triggerFlow}
          />
        ) : (
          <div style={{ flex: 1, overflowY: 'auto', padding: '10px 6px', background: '#0d1117' }}>
            {projectTree.map(rootNode => (
              <InteractiveTreeNode
                key={rootNode.id}
                node={rootNode}
                depth={0}
                selNode={activeNode}
                onSelect={onSelectNode}
                openMap={openMap}
                onToggleOpen={toggleOpen}
                levelFilter={levelFilter}
                searchQuery={searchQuery}
                flowActiveStep={flowMode ? flowActiveStep : null}
                flowStepMap={flowMode ? flowStepMap : {}}
                callerHighlightIds={callerHighlightIds}
                calleeHighlightIds={calleeHighlightIds}
                onTraceFlow={triggerFlow}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Right Stage: Node Inspector, Ask AI, and Code Viewer ─────────── */}
      <div style={{ flex: '1 1 46%', display: 'flex', flexDirection: 'column', minWidth: 380, overflow: 'hidden' }}>
        
        {/* Inspector Header */}
        <div style={{ padding: '10px 16px', borderBottom: '1px solid #30363d', background: '#161b22', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
            <span style={{ fontSize: 20 }}>{activeCfg.icon}</span>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: 14, color: '#e6edf3', fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {activeNode?.name || 'Select a Node'}
              </div>
              <div style={{ fontSize: 11, color: '#8b949e', marginTop: 1 }}>
                {activeNode?.level} · {activeNode?.file ? bn(activeNode.file) : 'Project Root'}
                {activeNode?.lineno ? ` :${activeNode.lineno}` : ''}
              </div>
            </div>
          </div>

          {/* Inspector Sub-Tabs */}
          <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
            <button
              onClick={() => setInspectorTab('details')}
              style={{
                padding: '4px 10px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                background: inspectorTab === 'details' ? '#1f6feb22' : 'transparent',
                border: `1px solid ${inspectorTab === 'details' ? '#58a6ff44' : '#30363d'}`,
                color: inspectorTab === 'details' ? '#58a6ff' : '#8b949e',
                cursor: 'pointer',
              }}
            >
              📖 Code &amp; Details
            </button>
            <button
              onClick={() => setInspectorTab('ask_ai')}
              style={{
                padding: '4px 10px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                background: inspectorTab === 'ask_ai' ? '#3fb95022' : 'transparent',
                border: `1px solid ${inspectorTab === 'ask_ai' ? '#3fb95044' : '#30363d'}`,
                color: inspectorTab === 'ask_ai' ? '#3fb950' : '#8b949e',
                cursor: 'pointer',
              }}
            >
              💬 Ask Tree AI
            </button>
          </div>
        </div>

        {/* Inspector Body Content */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          
          {/* ── Sub-Tab 1: Node Details & Source Code ────────────────────────── */}
          {inspectorTab === 'details' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
              {/* Summary & Relation Controls */}
              <div style={{ padding: '12px 16px', borderBottom: '1px solid #21262d', flexShrink: 0, overflowY: 'auto', maxHeight: '42%' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                  <div className="sec-hdr" style={{ margin: 0 }}>Plain-Language AI Summary</div>
                  <AIBadge />
                </div>
                <div style={{ background: '#0d1117', borderRadius: 8, padding: 12, border: '1px solid #21262d', fontSize: 13, color: '#c9d1d9', lineHeight: 1.65 }}>
                  {activeNode?.summary || 'No summary available for this node.'}
                </div>

                {/* Function Action Bar */}
                {activeNode?.level === 'FUNCTION' && (
                  <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                    <button
                      className="btn btn-purple"
                      style={{ padding: '4px 10px', fontSize: 11 }}
                      onClick={() => triggerFlow(activeNode.id)}
                    >
                      🌊 Trace Execution Flow
                    </button>
                    {activeNode.callers?.length > 0 && (
                      <button
                        className="btn"
                        style={{ padding: '4px 10px', fontSize: 11, background: '#21262d', color: '#bc8cff', border: '1px solid #bc8cff44' }}
                        onClick={() => toggleCallerHighlights(activeNode.callers)}
                      >
                        {callerHighlightIds.length > 0 ? 'Clear Callers' : `Show Callers (${activeNode.callers.length})`}
                      </button>
                    )}
                    {activeNode.callees?.length > 0 && (
                      <button
                        className="btn"
                        style={{ padding: '4px 10px', fontSize: 11, background: '#21262d', color: '#3fb950', border: '1px solid #3fb95044' }}
                        onClick={() => toggleCalleeHighlights(activeNode.callees)}
                      >
                        {calleeHighlightIds.length > 0 ? 'Clear Callees' : `Show Callees (${activeNode.callees.length})`}
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Source Code Viewer */}
              <div style={{ flex: 1, overflow: 'hidden', padding: '10px 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div className="sec-hdr" style={{ margin: 0 }}>
                    Source Code
                    {activeNode?.lineno ? <span style={{ color: '#484f58', fontWeight: 400, marginLeft: 8 }}>Lines {activeNode.lineno}–{activeNode.endLineno || activeNode.lineno}</span> : null}
                  </div>
                </div>
                <div style={{ flex: 1, overflow: 'hidden', border: '1px solid #21262d', borderRadius: 8 }}>
                  <CodeViewer
                    source={activeNode?.source || activeNode?.source_snippet}
                    lineno={activeNode?.lineno}
                    endLineno={activeNode?.endLineno}
                    maxH="100%"
                  />
                </div>
              </div>
            </div>
          )}

          {/* ── Sub-Tab 2: Ask Tree AI (Context-aware in-tree chat) ──────────── */}
          {inspectorTab === 'ask_ai' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
              {/* Context Scope Header */}
              <div style={{ padding: '10px 16px', borderBottom: '1px solid #21262d', background: '#161b22', flexShrink: 0 }}>
                <div style={{ fontSize: 11, color: '#8b949e', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>🎯 Current Context Scope:</span>
                  <span style={{ fontFamily: 'monospace', color: '#3fb950', fontWeight: 600 }}>{activeNode?.name || 'Entire Codebase'}</span>
                </div>

                {/* Quick Prompt Chips */}
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                  {[
                    "Explain what this does in plain English",
                    "How does execution flow through this?",
                    "Are there any edge cases or potential bugs?",
                    "Suggest refactoring or performance optimization",
                  ].map(qp => (
                    <button
                      key={qp}
                      onClick={() => sendTreeQuestion(qp)}
                      style={{
                        padding: '3px 8px',
                        borderRadius: 5,
                        fontSize: 10.5,
                        background: '#21262d',
                        border: '1px solid #30363d',
                        color: '#8b949e',
                        cursor: 'pointer',
                        textAlign: 'left',
                      }}
                      className="tree-item"
                    >
                      💡 {qp}
                    </button>
                  ))}
                </div>
              </div>

              {/* Chat Thread */}
              <div style={{ flex: 1, overflowY: 'auto', padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
                {treeChatMsgs.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px 20px', color: '#484f58', fontSize: 12.5 }}>
                    <div style={{ fontSize: 32, marginBottom: 8 }}>💬</div>
                    <div>Ask any question about <strong style={{ color: '#e6edf3' }}>{activeNode?.name || 'this tree node'}</strong>.</div>
                    <div style={{ marginTop: 4, color: '#8b949e' }}>Click a prompt above or type a custom question below.</div>
                  </div>
                ) : (
                  treeChatMsgs.map((m, idx) => (
                    <div key={idx} className="anim-slide" style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                      <div
                        className={m.role === 'user' ? 'bubble-user' : 'bubble-ai'}
                        style={{ maxWidth: '90%', padding: '9px 12px', fontSize: 12.5, lineHeight: 1.6, color: m.role === 'user' ? '#fff' : '#c9d1d9' }}
                      >
                        {m.role === 'ai' && <div style={{ marginBottom: 4 }}><AIBadge /></div>}
                        <div style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>

                        {(m.cited || []).length > 0 && (
                          <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                            {m.cited.map((cf, j) => (
                              <button
                                key={j}
                                onClick={() => {
                                  const found = findNodeInTree(projectTree, cf.func_id);
                                  if (found) onSelectNode(found);
                                }}
                                style={{
                                  fontSize: 10.5,
                                  padding: '2px 8px',
                                  borderRadius: 5,
                                  background: '#58a6ff18',
                                  color: '#58a6ff',
                                  border: '1px solid #58a6ff33',
                                  cursor: 'pointer',
                                  fontFamily: 'monospace',
                                }}
                              >
                                → {cf.name}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
                {treeChatLoading && (
                  <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                    <div className="bubble-ai" style={{ padding: '8px 14px', fontSize: 12, color: '#8b949e', display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Spin sz={11} /> <span className="anim-pulse">AI analyzing code tree context…</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Chat Input */}
              <div style={{ padding: '10px 14px', borderTop: '1px solid #30363d', background: '#161b22', flexShrink: 0 }}>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    className="inp"
                    style={{ fontSize: 12 }}
                    placeholder={`Ask about ${activeNode?.name || 'this tree'}…`}
                    value={treeChatInp}
                    disabled={treeChatLoading}
                    onChange={e => setTreeChatInp(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendTreeQuestion()}
                  />
                  <button
                    onClick={() => sendTreeQuestion()}
                    disabled={treeChatLoading || !treeChatInp.trim()}
                    className="btn btn-solid-blue"
                    style={{ padding: '6px 14px', borderRadius: 8 }}
                  >
                    Send
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Welcome hint ──────────────────────────────────────────────────────────
const WelcomeHint = () => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 20, padding: 32, textAlign: 'center' }}>
    <div style={{ fontSize: 56 }}>🗺️</div>
    <div>
      <div style={{ fontWeight: 700, fontSize: 22, color: '#e6edf3', marginBottom: 6 }}>Welcome to CodeAtlas</div>
      <div style={{ fontSize: 13, color: '#8b949e', lineHeight: 1.7 }}>Upload a Python .zip project to explore the interactive visual Graph Tree.</div>
    </div>
  </div>
);

// ── Detail tab (Optimality + Risk Deep-Dive) ───────────────────────────────
const DetailTab = ({ sid, node, toast }) => {
  const [opt, setOpt] = React.useState(null);
  const [risk, setRisk] = React.useState(null);
  const [lOpt, setLOpt] = React.useState(false);
  const [lRisk, setLRisk] = React.useState(false);

  const doOpt = async () => {
    if (!node?.id) return;
    setLOpt(true);
    setOpt(null);
    try {
      const r = await fetch(`${API}/session/${sid}/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ func_id: node.id })
      });
      const d = await r.json();
      if (d.error) toast('Optimality: ' + d.error, 'error');
      else setOpt(d);
    } catch {
      toast('Optimality check failed', 'error');
    } finally {
      setLOpt(false);
    }
  };

  const doRisk = async () => {
    if (!node?.id) return;
    setLRisk(true);
    setRisk(null);
    try {
      const r = await fetch(`${API}/session/${sid}/risk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ func_id: node.id })
      });
      const d = await r.json();
      if (d.error) toast('Risk: ' + d.error, 'error');
      else setRisk(d);
    } catch {
      toast('Risk check failed', 'error');
    } finally {
      setLRisk(false);
    }
  };

  if (!node || node.level !== 'FUNCTION') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12, color: '#484f58' }}>
        <span style={{ fontSize: 52 }}>⚡</span>
        <div style={{ fontSize: 14, color: '#8b949e' }}>Select a <strong style={{ color: '#3fb950' }}>function</strong> from the tree to run Optimality and Blast Radius checks.</div>
      </div>
    );
  }

  const RatingLabel = { 1: 'Poor', 2: 'Below Avg', 3: 'Average', 4: 'Good', 5: 'Excellent' };
  const RatingColor = { 1: '#f85149', 2: '#f0883e', 3: '#d29922', 4: '#58a6ff', 5: '#3fb950' };
  const rating = opt?.optimality?.rating || 0;
  const riskScore = risk?.risk_score || 0;
  const tier = risk?.risk_tier || 'LOW';
  const tierColor = { HIGH: '#f85149', MEDIUM: '#d29922', LOW: '#3fb950' }[tier] || '#3fb950';

  return (
    <div className="anim-fade" style={{ height: '100%', overflowY: 'auto', padding: 20, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
      {/* Optimality Panel */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
          <div style={{ fontWeight: 600, fontSize: 14 }}>⚡ Function Optimality</div>
          <button className="btn btn-yellow" onClick={doOpt} disabled={lOpt}>
            {lOpt ? <Spin sz={12} /> : '🔍'}{lOpt ? 'Analyzing…' : 'Check Optimality'}
          </button>
        </div>

        {lOpt && <SkeletonCard />}

        {opt && !lOpt && (
          <div className="anim-fade" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#0d1117', borderRadius: 8, padding: 12, border: '1px solid #21262d' }}>
              <div>
                <div style={{ fontSize: 11, color: '#8b949e', marginBottom: 2 }}>Rating</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Stars n={rating} />
                  <span style={{ fontWeight: 700, fontSize: 13, color: RatingColor[rating] || '#8b949e' }}>
                    {RatingLabel[rating] || 'Rated'}
                  </span>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 11, color: '#8b949e', marginBottom: 2 }}>Complexity</div>
                <div style={{ fontSize: 12, fontFamily: 'monospace', color: '#58a6ff' }}>
                  {opt.optimality?.time_complexity || 'O(?)'} time · {opt.optimality?.space_complexity || 'O(?)'} space
                </div>
              </div>
            </div>

            {opt.optimality?.issues?.length > 0 && (
              <div>
                <div className="sec-hdr">Detected Issues</div>
                {opt.optimality.issues.map((iss, i) => (
                  <div key={i} style={{ background: '#0d1117', borderRadius: 6, padding: 10, border: '1px solid #21262d', marginBottom: 6, fontSize: 12 }}>
                    <span style={{ fontWeight: 600, color: '#f0883e' }}>[{iss.type}] </span>
                    <span style={{ color: '#c9d1d9' }}>{iss.description}</span>
                  </div>
                ))}
              </div>
            )}

            {opt.optimality?.refactoring_suggestions?.length > 0 && (
              <div>
                <div className="sec-hdr">Refactoring Suggestions</div>
                {opt.optimality.refactoring_suggestions.map((sug, i) => (
                  <div key={i} style={{ background: '#0d1117', borderRadius: 6, padding: 10, border: '1px solid #21262d', marginBottom: 6, fontSize: 12 }}>
                    <div style={{ color: '#3fb950', marginBottom: 4 }}>💡 {sug.description}</div>
                    {sug.code_example && (
                      <pre style={{ background: '#161b22', padding: 8, borderRadius: 5, fontSize: 11, overflowX: 'auto', fontFamily: 'monospace' }}>
                        <code>{sug.code_example}</code>
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Blast Radius & Risk Panel */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
          <div style={{ fontWeight: 600, fontSize: 14 }}>💥 Blast Radius &amp; Risk Score</div>
          <button className="btn btn-red" onClick={doRisk} disabled={lRisk}>
            {lRisk ? <Spin sz={12} /> : '💥'}{lRisk ? 'Computing…' : 'Check Risk'}
          </button>
        </div>

        {lRisk && <SkeletonCard />}

        {risk && !lRisk && (
          <div className="anim-fade" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ background: '#0d1117', borderRadius: 8, padding: 14, border: '1px solid #21262d' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <span style={{ fontWeight: 700, fontSize: 26, color: tierColor }}>
                  {riskScore.toFixed(1)}<span style={{ fontSize: 13, color: '#8b949e' }}>/10</span>
                </span>
                <span style={{ fontSize: 12, fontWeight: 700, padding: '3px 12px', borderRadius: 6, background: `${tierColor}22`, color: tierColor, border: `1px solid ${tierColor}44` }}>
                  {tier} RISK
                </span>
              </div>
              <div className="prog-bar">
                <div className="gauge-fill" style={{ width: `${riskScore * 10}%`, background: `linear-gradient(90deg,${tierColor}88,${tierColor})` }} />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {[['Functions Affected', risk.dependent_count || 0, '🔹'], ['Files Affected', risk.file_spread || 0, '📄']].map(([l, v, e]) => (
                <div key={l} style={{ background: '#0d1117', borderRadius: 8, padding: 12, border: '1px solid #21262d', textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: '#8b949e', marginBottom: 4 }}>{e} {l}</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: '#e6edf3' }}>{v}</div>
                </div>
              ))}
            </div>

            {risk.blast_radius_narrative && (
              <div style={{ fontSize: 12.5, color: '#c9d1d9', background: '#0d1117', borderRadius: 8, padding: 12, border: '1px solid #21262d', lineHeight: 1.65 }}>
                {risk.blast_radius_narrative}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ── Flow tab (Dedicated Full-Width Multi-Path Execution Explorer) ──────────
const FlowTab = ({ sid, node, toast }) => {
  const [flow, setFlow] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [pi, setPi] = React.useState(0);

  const doFlow = async () => {
    if (!node?.id) return;
    setLoading(true);
    setFlow(null);
    setPi(0);
    try {
      const r = await fetch(`${API}/session/${sid}/flow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ func_id: node.id })
      });
      const d = await r.json();
      if (d.error) toast(d.error, 'error');
      else setFlow(d);
    } catch {
      toast('Flow analysis failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  if (!node || node.level !== 'FUNCTION') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12, color: '#484f58' }}>
        <span style={{ fontSize: 52 }}>🌊</span>
        <div style={{ fontSize: 14, color: '#8b949e' }}>Select a <strong style={{ color: '#3fb950' }}>function</strong> to trace its execution flow</div>
      </div>
    );
  }

  const paths = flow?.paths || [];
  const cur = paths[pi];

  return (
    <div className="anim-fade" style={{ height: '100%', overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>🌊 Execution Flow Paths</div>
          <div style={{ fontSize: 12, color: '#8b949e', marginTop: 2 }}>
            Tracing paths to <span style={{ fontFamily: 'monospace', color: '#58a6ff' }}>{node.name}</span>
          </div>
        </div>
        <button className="btn btn-purple" onClick={doFlow} disabled={loading}>
          {loading ? <Spin sz={12} /> : '🔍'}{loading ? 'Tracing paths…' : 'Trace Execution Flow'}
        </button>
      </div>

      {loading && <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}><SkeletonCard /><SkeletonCard /></div>}

      {flow && !loading && (
        <div className="anim-fade">
          {paths.length > 1 && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 10 }}>
              <span className="sec-hdr" style={{ margin: 0 }}>Paths found:</span>
              {paths.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setPi(i)}
                  style={{
                    padding: '4px 12px',
                    borderRadius: 7,
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: 'pointer',
                    border: `1px solid ${i === pi ? '#58a6ff' : '#30363d'}`,
                    background: i === pi ? '#1f6feb' : '#21262d',
                    color: i === pi ? '#fff' : '#8b949e'
                  }}
                >
                  Path {i + 1}
                </button>
              ))}
              <span style={{ fontSize: 11, color: '#484f58', marginLeft: 'auto' }}>{flow.total_paths} paths</span>
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
                      <div style={{ fontFamily: 'monospace', fontSize: 11.5, fontWeight: 700, color: '#e6edf3', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {step.name}
                      </div>
                      <div style={{ fontSize: 10, color: '#484f58', marginTop: 2 }}>{bn(step.file)}</div>
                      {step.summary_short && (
                        <div style={{ fontSize: 10, color: '#8b949e', marginTop: 5, lineHeight: 1.4 }}>
                          {step.summary_short}
                        </div>
                      )}
                    </div>
                    {i < cur.steps.length - 1 && <span className="flow-arrow">→</span>}
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ── Report tab (Two-Stage Project Report) ──────────────────────────────────
const ReportTab = ({ sid, toast }) => {
  const [rpt, setRpt] = React.useState(null);
  const [loading, setLoading] = React.useState(false);

  const gen = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/session/${sid}/report`, { method: 'POST' });
      const d = await r.json();
      if (d.error) toast(d.error, 'error');
      else setRpt(d);
    } catch {
      toast('Report generation failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  if (!sid) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#484f58', fontSize: 13 }}>Upload a project first</div>;

  return (
    <div className="anim-fade" style={{ height: '100%', overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: '#e6edf3' }}>📊 Two-Stage Project Report</h2>
          <p style={{ fontSize: 12, color: '#8b949e' }}>Deterministic CVE security audit + AI-graded architectural findings</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-solid-blue" onClick={gen} disabled={loading}>
            {loading ? <Spin sz={12} /> : '⚡'}{loading ? 'Generating…' : 'Generate Full Report'}
          </button>
          {rpt && (
            <a href={`${API}/session/${sid}/report/export`} download className="btn" style={{ background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d' }}>
              📥 Export Markdown
            </a>
          )}
        </div>
      </div>

      {loading && <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}><SkeletonCard /><SkeletonCard /></div>}

      {rpt && !loading && (
        <div className="anim-fade" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Executive Summary */}
          <div className="card">
            <div className="sec-hdr">Executive Summary</div>
            <p style={{ fontSize: 13.5, color: '#c9d1d9', lineHeight: 1.7 }}>{rpt.executive_summary || 'Analysis complete.'}</p>
          </div>

          {/* Vulnerabilities & Findings */}
          <div className="card">
            <div className="sec-hdr">Vulnerabilities &amp; Dependencies ({rpt.vulnerabilities?.length || 0})</div>
            {(rpt.vulnerabilities || []).length === 0 ? (
              <div style={{ fontSize: 12, color: '#3fb950' }}>✅ No known CVE vulnerabilities detected in dependencies.</div>
            ) : (
              rpt.vulnerabilities.map((v, i) => (
                <div key={i} style={{ background: '#0d1117', borderRadius: 8, padding: 12, border: '1px solid #21262d', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <SevBadge s={v.severity || 'MEDIUM'} />
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#e6edf3' }}>{v.package}</span>
                  </div>
                  <p style={{ fontSize: 12, color: '#8b949e', marginTop: 4 }}>{v.description}</p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
