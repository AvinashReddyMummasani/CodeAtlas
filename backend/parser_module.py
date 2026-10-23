"""
parser_module.py — Static AST parser for CodeAtlas.

Public API
----------
parse_project(session_dir, py_files) -> dict
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from typing import Any, Optional

import networkx as nx

# ---------------------------------------------------------------------------
# ID helpers
# ---------------------------------------------------------------------------

def _func_id(filepath: str, class_ctx: Optional[str], name: str) -> str:
    """Canonical function/method identifier: ``filepath::ClassName.method``."""
    if class_ctx:
        return f"{filepath}::{class_ctx}.{name}"
    return f"{filepath}::{name}"


def _block_id(filepath: str, block_type: str, lineno: int) -> str:
    return f"{filepath}::{block_type}@{lineno}"


# ---------------------------------------------------------------------------
# Source-snippet helper
# ---------------------------------------------------------------------------

def _source_snippet(source_lines: list[str], lineno: int, end_lineno: int) -> str:
    """Return the source lines for *lineno*–*end_lineno* (1-based, inclusive)."""
    snippet_lines = source_lines[lineno - 1 : end_lineno]
    return textwrap.dedent("".join(snippet_lines))


# ---------------------------------------------------------------------------
# AST visitors
# ---------------------------------------------------------------------------

class _FileVisitor(ast.NodeVisitor):
    """
    Single-pass visitor that collects everything CodeAtlas needs from one file.
    """

    def __init__(self, filepath: str, source: str) -> None:
        self.filepath = filepath
        self.source = source
        self.source_lines: list[str] = source.splitlines(keepends=True)

        # Outputs
        self.imports: list[str] = []
        self.top_level_names: list[str] = []
        self.blocks: list[dict] = []           # CLASS / MODULE_BLOCK
        self.functions: list[dict] = []        # FUNCTION granularity
        self.logical_blocks: list[dict] = []   # LOGICAL_BLOCK inside functions
        self.call_edges: list[tuple[str, str]] = []  # (caller_id, raw_callee_name)
        self.entry_point: bool = False

        # Walking state
        self._class_stack: list[str] = []
        self._function_stack: list[str] = []   # stack of func_ids
        self._inside_function: bool = False

    # ------------------------------------------------------------------
    # Imports
    # ------------------------------------------------------------------

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Classes — BLOCK level
    # ------------------------------------------------------------------

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if not self._inside_function:
            self.top_level_names.append(node.name)
            end_lineno = getattr(node, "end_lineno", node.lineno)
            block_info: dict[str, Any] = {
                "level": "BLOCK",
                "block_type": "CLASS",
                "name": node.name,
                "lineno": node.lineno,
                "end_lineno": end_lineno,
                "source_snippet": _source_snippet(
                    self.source_lines, node.lineno, end_lineno
                ),
                "block_id": _block_id(self.filepath, f"CLASS.{node.name}", node.lineno),
            }
            self.blocks.append(block_info)

        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    # ------------------------------------------------------------------
    # Functions — FUNCTION level
    # ------------------------------------------------------------------

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        class_ctx = self._class_stack[-1] if self._class_stack else None
        fid = _func_id(self.filepath, class_ctx, node.name)

        if not self._inside_function:
            self.top_level_names.append(node.name)

        end_lineno = getattr(node, "end_lineno", node.lineno)

        # Args
        args_list: list[str] = []
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            args_list.append(arg.arg)
        if node.args.vararg:
            args_list.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            args_list.append(f"**{node.args.kwarg.arg}")

        # Decorators
        decorators: list[str] = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(f"{ast.unparse(dec)}")
            else:
                decorators.append(ast.unparse(dec))

        # Docstring
        docstring: Optional[str] = ast.get_docstring(node)

        snippet = _source_snippet(self.source_lines, node.lineno, end_lineno)

        func_info: dict[str, Any] = {
            "level": "FUNCTION",
            "func_id": fid,
            "name": node.name,
            "file": self.filepath,
            "class_ctx": class_ctx,
            "lineno": node.lineno,
            "end_lineno": end_lineno,
            "args": args_list,
            "decorators": decorators,
            "docstring": docstring,
            "source_snippet": snippet,
            "callers": [],   # filled in second pass
            "callees": [],   # filled in second pass
        }
        self.functions.append(func_info)

        # Detect entry points
        if node.name == "main":
            self.entry_point = True

        # Recurse into the function body to gather calls and logical blocks
        prev_inside = self._inside_function
        self._inside_function = True
        self._function_stack.append(fid)

        _LogicalBlockCollector(
            self.filepath,
            self.source_lines,
            self.logical_blocks,
        ).visit_body(node.body)

        _CallCollector(fid, self.call_edges).visit(node)

        self._function_stack.pop()
        self._inside_function = prev_inside

        # Do NOT call generic_visit — we already visited the body above
        # (avoids double-counting nested functions)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    # ------------------------------------------------------------------
    # Module-level blocks (top-level For / While / If / Try / With)
    # not inside a class or function — MODULE_BLOCK granularity
    # ------------------------------------------------------------------

    def _maybe_add_module_block(self, node: ast.stmt, label: str) -> None:
        if not self._inside_function and not self._class_stack:
            end_lineno = getattr(node, "end_lineno", node.lineno)
            self.blocks.append(
                {
                    "level": "BLOCK",
                    "block_type": f"MODULE_{label}",
                    "name": f"{label}@{node.lineno}",
                    "lineno": node.lineno,
                    "end_lineno": end_lineno,
                    "source_snippet": _source_snippet(
                        self.source_lines, node.lineno, end_lineno
                    ),
                    "block_id": _block_id(
                        self.filepath, f"MODULE_{label}", node.lineno
                    ),
                }
            )

    def visit_For(self, node: ast.For) -> None:
        self._maybe_add_module_block(node, "FOR")
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._maybe_add_module_block(node, "WHILE")
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self._maybe_add_module_block(node, "WITH")
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._maybe_add_module_block(node, "ASYNCWITH")
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._maybe_add_module_block(node, "TRY")
        self.generic_visit(node)

    def visit_TryStar(self, node: ast.TryStar) -> None:  # type: ignore[attr-defined]
        self._maybe_add_module_block(node, "TRY")
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        # Detect ``if __name__ == "__main__":`` pattern
        if not self._inside_function:
            if _is_dunder_main(node):
                self.entry_point = True
            self._maybe_add_module_block(node, "IF")
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Logical block collector (inside a function body)
# ---------------------------------------------------------------------------

_LOGICAL_BLOCK_TYPES = (
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.If,
    ast.Try,
    ast.With,
    ast.AsyncWith,
)

try:
    _LOGICAL_BLOCK_TYPES = _LOGICAL_BLOCK_TYPES + (ast.TryStar,)  # type: ignore[assignment]
except AttributeError:
    pass


class _LogicalBlockCollector(ast.NodeVisitor):
    """Collect LOGICAL_BLOCK nodes at any depth inside a function."""

    def __init__(
        self,
        filepath: str,
        source_lines: list[str],
        output: list[dict],
    ) -> None:
        self.filepath = filepath
        self.source_lines = source_lines
        self.output = output

    def visit_body(self, stmts: list[ast.stmt]) -> None:
        for stmt in stmts:
            self.visit(stmt)

    def _record(self, node: ast.stmt, label: str) -> None:
        end_lineno = getattr(node, "end_lineno", node.lineno)
        self.output.append(
            {
                "level": "LOGICAL_BLOCK",
                "type": label,
                "lineno": node.lineno,
                "end_lineno": end_lineno,
                "source_snippet": _source_snippet(
                    self.source_lines, node.lineno, end_lineno
                ),
                "block_id": _block_id(self.filepath, label, node.lineno),
            }
        )

    def visit_For(self, node: ast.For) -> None:
        self._record(node, "FOR")
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._record(node, "ASYNCFOR")
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._record(node, "WHILE")
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self._record(node, "IF")
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._record(node, "TRY")
        self.generic_visit(node)

    def visit_TryStar(self, node: ast.TryStar) -> None:  # type: ignore[attr-defined]
        self._record(node, "TRY")
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self._record(node, "WITH")
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._record(node, "ASYNCWITH")
        self.generic_visit(node)

    # Stop descent into nested function/class defs (they are separate scopes)
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: ARG002
        pass

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: ARG002
        pass

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: ARG002
        pass


# ---------------------------------------------------------------------------
# Call collector (inside a single function)
# ---------------------------------------------------------------------------

class _CallCollector(ast.NodeVisitor):
    """Walk a function node and emit (caller_id, raw_callee_name) edges."""

    def __init__(self, caller_id: str, edges: list[tuple[str, str]]) -> None:
        self.caller_id = caller_id
        self.edges = edges

    def visit_Call(self, node: ast.Call) -> None:
        callee_name: Optional[str] = None
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee_name = node.func.attr
        if callee_name:
            self.edges.append((self.caller_id, callee_name))
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _is_dunder_main(node: ast.If) -> bool:
    """Return True for ``if __name__ == "__main__":`` or the reversed form."""
    test = node.test
    if not isinstance(test, ast.Compare):
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    left, right = test.left, test.comparators[0]
    def _is_name(n: ast.expr) -> bool:
        return isinstance(n, ast.Name) and n.id == "__name__"
    def _is_main(n: ast.expr) -> bool:
        return isinstance(n, ast.Constant) and n.value == "__main__"
    return (_is_name(left) and _is_main(right)) or (
        _is_name(right) and _is_main(left)
    )


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def parse_project(session_dir: str, py_files: list[str]) -> dict:
    """
    Parse every Python file in *py_files* (paths relative to *session_dir*)
    and return a unified project-level analysis dict.

    Parameters
    ----------
    session_dir : Root directory of the extracted session.
    py_files    : List of relative .py paths (as returned by save_upload).

    Returns
    -------
    {
      "files":        {filepath: {level, imports, blocks, functions,
                                  logical_blocks, source, entry_point}},
      "call_graph":   {caller_id: [callee_ids, ...]},   # adjacency list
      "entry_points": [func_id, ...],
      "syntax_errors":{filepath: error_msg},
      "all_functions":{func_id: {name, file, class_ctx, lineno, end_lineno,
                                  source_snippet, docstring, callers, callees}},
      "all_blocks":   {block_id: {...}},
    }
    """
    base = Path(session_dir)

    files_result: dict[str, Any] = {}
    syntax_errors: dict[str, str] = {}
    all_functions: dict[str, Any] = {}
    all_blocks: dict[str, Any] = {}
    entry_points: list[str] = []

    # Raw call edges collected across all files: list of (caller_id, raw_callee_name)
    raw_edges: list[tuple[str, str]] = []

    # Build a mapping from bare function name -> list of func_ids (for resolution)
    name_to_ids: dict[str, list[str]] = {}

    # -----------------------------------------------------------------------
    # Pass 1 — parse every file
    # -----------------------------------------------------------------------
    for rel_path in py_files:
        abs_path = base / rel_path
        try:
            source = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            syntax_errors[rel_path] = f"Cannot read file: {exc}"
            continue

        try:
            tree = ast.parse(source, filename=rel_path)
        except SyntaxError as exc:
            syntax_errors[rel_path] = str(exc)
            continue

        visitor = _FileVisitor(rel_path, source)
        visitor.visit(tree)

        # Detect entry points: file named main.py
        is_entry = (
            visitor.entry_point
            or Path(rel_path).stem == "main"
        )

        files_result[rel_path] = {
            "level": "FILE",
            "path": rel_path,
            "imports": visitor.imports,
            "top_level_names": visitor.top_level_names,
            "blocks": visitor.blocks,
            "functions": visitor.functions,
            "logical_blocks": visitor.logical_blocks,
            "source": source,
            "entry_point": is_entry,
        }

        # Accumulate all_functions
        for func_info in visitor.functions:
            fid = func_info["func_id"]
            all_functions[fid] = {k: v for k, v in func_info.items()}
            # Index name -> [ids] for edge resolution
            name_to_ids.setdefault(func_info["name"], []).append(fid)
            if is_entry and func_info["name"] == "main":
                entry_points.append(fid)

        # Accumulate all_blocks
        for blk in visitor.blocks:
            all_blocks[blk["block_id"]] = blk
        for lbl in visitor.logical_blocks:
            all_blocks[lbl["block_id"]] = lbl

        # Collect raw call edges
        raw_edges.extend(visitor.call_edges)

        # Entry point: ``if __name__ == "__main__"`` block (file-level)
        if is_entry and rel_path not in entry_points:
            # add file as entry marker when no explicit "main" function found
            pass

    # -----------------------------------------------------------------------
    # Pass 2 — build call graph with networkx
    # -----------------------------------------------------------------------
    G: nx.DiGraph = nx.DiGraph()
    G.add_nodes_from(all_functions.keys())

    for caller_id, raw_callee in raw_edges:
        # Resolve callee name to func_ids
        resolved_callees = name_to_ids.get(raw_callee, [])
        for callee_id in resolved_callees:
            if callee_id != caller_id:
                G.add_edge(caller_id, callee_id)

    # -----------------------------------------------------------------------
    # Pass 3 — annotate callers / callees in all_functions
    # -----------------------------------------------------------------------
    for fid in all_functions:
        callees = list(G.successors(fid))
        callers = list(G.predecessors(fid))
        all_functions[fid]["callees"] = callees
        all_functions[fid]["callers"] = callers

    # -----------------------------------------------------------------------
    # Build adjacency-list call_graph dict
    # -----------------------------------------------------------------------
    call_graph: dict[str, list[str]] = {
        node: list(G.successors(node)) for node in G.nodes
    }

    # -----------------------------------------------------------------------
    # Collect entry points: any file named main.py or containing ``main``
    # -----------------------------------------------------------------------
    for rel_path, fdata in files_result.items():
        if fdata["entry_point"]:
            for func_info in fdata["functions"]:
                if func_info["name"] == "main":
                    ep_id = func_info["func_id"]
                    if ep_id not in entry_points:
                        entry_points.append(ep_id)

    return {
        "files": files_result,
        "call_graph": call_graph,
        "entry_points": entry_points,
        "syntax_errors": syntax_errors,
        "all_functions": all_functions,
        "all_blocks": all_blocks,
    }
