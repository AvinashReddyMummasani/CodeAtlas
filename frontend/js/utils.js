// js/utils.js — Shared utilities, tree builder, and constants for CodeAtlas frontend
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
  PROJECT:       { icon: '📦', color: '#f0883e', label: 'Project' },
  FILE:          { icon: '📄', color: '#58a6ff', label: 'File' },
  BLOCK:         { icon: '🔷', color: '#bc8cff', label: 'Class / Block' },
  FUNCTION:      { icon: '🔹', color: '#3fb950', label: 'Function' },
  LOGICAL_BLOCK: { icon: '🔶', color: '#d29922', label: 'Logic' },
};

// ── Build hierarchical 5-level tree from function_tree ────────────────────
function buildTree(ft) {
  if (!ft?.files) return [];

  const fileEntries = Object.entries(ft.files);
  let totalClasses = 0;
  let totalFuncs = 0;
  let totalLogic = 0;
  let entryPointsCount = 0;

  const fileNodes = fileEntries.map(([fp, fn]) => {
    const blocksRaw = fn.blocks || {};
    const funcsRaw = fn.functions || {};
    const logicRaw = fn.logical_blocks || {};

    const blocksList = Array.isArray(blocksRaw) ? blocksRaw : Object.values(blocksRaw);
    const funcsList = Array.isArray(funcsRaw) ? funcsRaw : Object.values(funcsRaw);
    const logicList = Array.isArray(logicRaw) ? logicRaw : Object.values(logicRaw);

    if (fn.entry_point) entryPointsCount++;

    // Map classes (BLOCK level)
    const classMap = {};
    const moduleBlocks = [];

    blocksList.forEach(b => {
      const bname = b.name || b.block_id || 'Block';
      totalClasses++;
      const node = {
        id: b.block_id || `${fp}::${bname}`,
        name: b.block_type === 'CLASS' || b.name ? `class ${bname}` : bname,
        rawName: bname,
        level: 'BLOCK',
        block_type: b.block_type || 'CLASS',
        file: fp,
        lineno: b.lineno,
        endLineno: b.end_lineno,
        source: b.source_snippet || b.source || '',
        summary: b.summary || `Class ${bname}`,
        children: []
      };
      if (b.block_type === 'CLASS' || (b.name && !b.name.includes('@'))) {
        classMap[bname] = node;
      } else {
        moduleBlocks.push(node);
      }
    });

    // Map functions & methods (FUNCTION level)
    const standaloneFuncs = [];

    funcsList.forEach(f => {
      totalFuncs++;
      const fid = f.func_id || f.id || `${fp}::${f.name}`;
      const fname = f.name || fid.split('::').pop();
      const fln = f.lineno || 0;
      const fend = f.end_lineno || (fln + 100);

      // Map logical blocks inside this function
      const funcLogicBlocks = [];
      logicList.forEach(lb => {
        const lbln = lb.lineno || 0;
        if (lbln >= fln && lbln <= fend) {
          totalLogic++;
          const lbid = lb.block_id || `${fp}::${lb.type}@${lbln}`;
          funcLogicBlocks.push({
            id: lbid,
            name: `${lb.type || 'LOGIC'} @ L${lbln}`,
            rawName: lb.type || 'LOGIC',
            level: 'LOGICAL_BLOCK',
            file: fp,
            lineno: lbln,
            endLineno: lb.end_lineno || lbln,
            source: lb.source_snippet || '',
            summary: lb.summary || `${lb.type} statement at line ${lbln}`,
            children: []
          });
        }
      });

      const fnode = {
        id: fid,
        name: `def ${fname}`,
        rawName: fname,
        level: 'FUNCTION',
        class_ctx: f.class_ctx || null,
        file: fp,
        lineno: fln,
        endLineno: f.end_lineno,
        source: f.source_snippet || f.source || '',
        summary: f.summary || `Function ${fname}`,
        callers: f.callers || [],
        callees: f.callees || [],
        children: funcLogicBlocks
      };

      if (f.class_ctx && classMap[f.class_ctx]) {
        classMap[f.class_ctx].children.push(fnode);
      } else {
        standaloneFuncs.push(fnode);
      }
    });

    const fileChildren = [
      ...Object.values(classMap),
      ...standaloneFuncs,
      ...moduleBlocks
    ];

    return {
      id: fp,
      name: bn(fp),
      rawName: bn(fp),
      level: 'FILE',
      file: fp,
      source: fn.source || '',
      summary: fn.summary || `Python file ${bn(fp)} with ${funcsList.length} functions.`,
      entry_point: fn.entry_point || false,
      imports: fn.imports || [],
      children: fileChildren
    };
  });

  // Extract a representative project name
  const samplePath = fileEntries[0]?.[0] || 'project';
  const pathParts = samplePath.replace(/\\/g, '/').split('/');
  const projectName = pathParts.length > 1 ? pathParts[0] : 'Codebase Root';

  // Upper Logical Level — Project Root Node
  const projectRootNode = {
    id: 'PROJECT_ROOT',
    name: `Project: ${projectName}`,
    rawName: projectName,
    level: 'PROJECT',
    file: '',
    summary: `Python Project containing ${fileNodes.length} files, ${totalClasses} classes, ${totalFuncs} functions, and ${totalLogic} logical blocks. Entry points detected: ${entryPointsCount || 'standard script'}.`,
    entry_point: true,
    stats: {
      files: fileNodes.length,
      classes: totalClasses,
      functions: totalFuncs,
      logicBlocks: totalLogic,
      entryPoints: entryPointsCount
    },
    children: fileNodes
  };

  return [projectRootNode];
}

// ── Flatten tree to array with depths for search / indexing ───────────────
function flattenTree(nodes, depth = 0, result = []) {
  if (!nodes) return result;
  for (const n of nodes) {
    result.push({ ...n, depth });
    if (n.children && n.children.length > 0) {
      flattenTree(n.children, depth + 1, result);
    }
  }
  return result;
}

// ── Find node in tree by ID ───────────────────────────────────────────────
function findNodeInTree(nodes, targetId) {
  if (!nodes || !targetId) return null;
  for (const n of nodes) {
    if (n.id === targetId) return n;
    if (n.children && n.children.length > 0) {
      const found = findNodeInTree(n.children, targetId);
      if (found) return found;
    }
  }
  return null;
}

// ── Get array of ancestor IDs for auto-expanding to a node ────────────────
function getNodeAncestors(nodes, targetId, currentPath = []) {
  if (!nodes || !targetId) return [];
  for (const n of nodes) {
    if (n.id === targetId) return currentPath;
    if (n.children && n.children.length > 0) {
      const res = getNodeAncestors(n.children, targetId, [...currentPath, n.id]);
      if (res.length > 0) return res;
    }
  }
  return [];
}
