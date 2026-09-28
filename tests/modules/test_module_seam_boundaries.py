"""Canh ranh giới module (ARCHITECTURE §0.2, §1.2) bằng cách quét mã nguồn.

Quét AST thay vì tin vào việc đọc lại: một lần import vượt ranh giới là đỏ ngay,
kể cả khi nó nằm trong thân hàm để né vòng import.
"""

from __future__ import annotations

import ast
from pathlib import Path

MODULES_ROOT = Path("app/modules")
FRAMEWORKS = ("fastapi", "beanie", "motor", "pymongo", "pydantic", "starlette")


def _imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
    return found


def _owner(path: Path) -> str:
    return path.relative_to(MODULES_ROOT).parts[0]


def test_khong_module_nao_import_ruot_cua_module_khac() -> None:
    """Module khác chỉ được vào qua barrel `app.modules.<x>`, không vào tầng bên trong."""
    crossings: list[str] = []
    for path in sorted(MODULES_ROOT.rglob("*.py")):
        owner = _owner(path)
        for name in _imports(path):
            parts = name.split(".")
            if len(parts) > 3 and parts[:2] == ["app", "modules"] and parts[2] != owner:
                crossings.append(f"{path}: {name}")
    assert crossings == [], "vượt ranh giới §1.2:\n" + "\n".join(crossings)


def test_domain_khong_biet_framework() -> None:
    """Tầng domain chỉ dataclass/enum/hàm thuần — không Beanie, không FastAPI, không Pydantic."""
    leaks: list[str] = []
    for path in sorted(MODULES_ROOT.glob("*/domain/**/*.py")):
        for name in _imports(path):
            if name.split(".")[0] in FRAMEWORKS or name.startswith("app.core.pagination"):
                leaks.append(f"{path}: {name}")
    assert leaks == [], "domain import framework (§0.2):\n" + "\n".join(leaks)


def test_core_khong_import_modules() -> None:
    """Chiều phụ thuộc luôn là module -> core."""
    leaks = [
        f"{path}: {name}"
        for path in sorted(Path("app/core").rglob("*.py"))
        for name in _imports(path)
        if name.startswith("app.modules")
    ]
    assert leaks == []


def test_bai_quet_thay_ca_import_trong_than_ham() -> None:
    tree = ast.parse("def f():\n    from app.modules.guest.domain.entities import Guest\n")
    names = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    assert names == {"app.modules.guest.domain.entities"}
