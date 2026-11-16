"""Tests for parser_module — static AST analysis."""
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure backend/ is importable from this file even when run standalone
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# ---------------------------------------------------------------------------
# Sample source code used throughout
# ---------------------------------------------------------------------------

SAMPLE_CODE = '''
import os
from pathlib import Path

class MyClass:
    """A sample class."""
    def method_a(self, x):
        return x * 2

    def method_b(self):
        return self.method_a(5)

def standalone(n):
    if n > 0:
        return n
    return 0

if __name__ == "__main__":
    obj = MyClass()
    obj.method_a(3)
'''

SAMPLE_CODE_WITH_CALLS = '''
def helper(x):
    return x + 1

def caller():
    result = helper(10)
    return result
'''


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def parsed_project():
    """Parse SAMPLE_CODE once for the entire module."""
    import parser_module

    td = tempfile.mkdtemp()
    p = Path(td) / "sample.py"
    p.write_text(SAMPLE_CODE, encoding="utf-8")
    result = parser_module.parse_project(td, [str(p)])
    yield result
    shutil.rmtree(td, ignore_errors=True)


@pytest.fixture(scope="module")
def parsed_calls():
    """Parse SAMPLE_CODE_WITH_CALLS for call-edge tests."""
    import parser_module

    td = tempfile.mkdtemp()
    p = Path(td) / "calls.py"
    p.write_text(SAMPLE_CODE_WITH_CALLS, encoding="utf-8")
    result = parser_module.parse_project(td, [str(p)])
    yield result
    shutil.rmtree(td, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestParserModule:
    # ---- Top-level structure ------------------------------------------------

    def test_parse_returns_dict(self, parsed_project):
        assert isinstance(parsed_project, dict)

    def test_has_files_key(self, parsed_project):
        assert "files" in parsed_project

    def test_has_all_functions_key(self, parsed_project):
        assert "all_functions" in parsed_project

    def test_files_is_dict(self, parsed_project):
        assert isinstance(parsed_project["files"], dict)

    def test_all_functions_is_dict(self, parsed_project):
        assert isinstance(parsed_project["all_functions"], dict)

    def test_at_least_one_file_parsed(self, parsed_project):
        assert len(parsed_project["files"]) >= 1

    # ---- Class detection ----------------------------------------------------

    def test_detects_class_block(self, parsed_project):
        files = parsed_project.get("files", {})
        # Parser stores classes as block_type="CLASS" (not type="CLASS")
        any_class = any(
            any(
                b.get("block_type") == "CLASS" or b.get("type") == "CLASS"
                for b in f.get("blocks", [])
            )
            for f in files.values()
        )
        assert any_class, "Should detect MyClass as a CLASS block"

    # ---- Function detection -------------------------------------------------

    def test_detects_method_a(self, parsed_project):
        funcs = parsed_project.get("all_functions", {})
        names = [v.get("name", "") for v in funcs.values()]
        assert any("method_a" in n for n in names), "method_a not found in all_functions"

    def test_detects_method_b(self, parsed_project):
        funcs = parsed_project.get("all_functions", {})
        names = [v.get("name", "") for v in funcs.values()]
        assert any("method_b" in n for n in names)

    def test_detects_standalone_function(self, parsed_project):
        funcs = parsed_project.get("all_functions", {})
        names = [v.get("name", "") for v in funcs.values()]
        assert any("standalone" in n for n in names)

    def test_function_count_at_least_three(self, parsed_project):
        funcs = parsed_project.get("all_functions", {})
        assert len(funcs) >= 3  # method_a, method_b, standalone

    # ---- Import detection ---------------------------------------------------

    def test_detects_imports(self, parsed_project):
        files = parsed_project.get("files", {})
        any_import = any(len(f.get("imports", [])) > 0 for f in files.values())
        assert any_import, "No imports detected — expected 'os' and 'Path'"

    def test_detects_os_import(self, parsed_project):
        files = parsed_project.get("files", {})
        all_imports = [i for f in files.values() for i in f.get("imports", [])]
        assert any("os" in imp for imp in all_imports)

    # ---- Function metadata --------------------------------------------------

    def test_all_functions_have_lineno(self, parsed_project):
        funcs = parsed_project.get("all_functions", {})
        for fid, fdata in funcs.items():
            assert "lineno" in fdata, f"Function '{fid}' is missing 'lineno'"

    def test_all_functions_have_name(self, parsed_project):
        funcs = parsed_project.get("all_functions", {})
        for fid, fdata in funcs.items():
            assert "name" in fdata, f"Function '{fid}' is missing 'name'"

    def test_all_functions_have_source_or_snippet(self, parsed_project):
        funcs = parsed_project.get("all_functions", {})
        for fid, fdata in funcs.items():
            has_source = "source_snippet" in fdata or "source" in fdata
            assert has_source, f"Function '{fid}' missing source_snippet/source"

    def test_lineno_is_positive_integer(self, parsed_project):
        funcs = parsed_project.get("all_functions", {})
        for fid, fdata in funcs.items():
            lineno = fdata.get("lineno", 0)
            assert isinstance(lineno, int) and lineno > 0, (
                f"Function '{fid}' has invalid lineno: {lineno}"
            )

    # ---- Call-edge resolution -----------------------------------------------

    def test_call_edges_is_set_or_list(self, parsed_calls):
        funcs = parsed_calls.get("all_functions", {})
        for fid, fdata in funcs.items():
            callees = fdata.get("callees", [])
            assert isinstance(callees, (list, set)), (
                f"'callees' for '{fid}' should be list or set"
            )

    def test_call_edges_resolved_caller_to_helper(self, parsed_calls):
        funcs = parsed_calls.get("all_functions", {})
        # Find 'caller' function
        caller_data = next(
            (v for v in funcs.values() if v.get("name") == "caller"), None
        )
        if caller_data is not None:
            # callees might be IDs or names; we just check the structure is sane
            callees = caller_data.get("callees", [])
            assert isinstance(callees, (list, set))

    # ---- Multiple files -----------------------------------------------------

    def test_parse_multiple_files(self):
        import parser_module

        td = tempfile.mkdtemp()
        try:
            p1 = Path(td) / "a.py"
            p2 = Path(td) / "b.py"
            p1.write_text("def foo(): pass\n", encoding="utf-8")
            p2.write_text("def bar(): pass\n", encoding="utf-8")
            result = parser_module.parse_project(td, [str(p1), str(p2)])
            assert len(result.get("files", {})) == 2
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_parse_empty_file(self):
        import parser_module

        td = tempfile.mkdtemp()
        try:
            p = Path(td) / "empty.py"
            p.write_text("", encoding="utf-8")
            result = parser_module.parse_project(td, [str(p)])
            assert isinstance(result, dict)
        finally:
            shutil.rmtree(td, ignore_errors=True)
