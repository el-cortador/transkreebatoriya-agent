"""
Contract-тест соответствия репозитория манифесту и спецификации агента.

Проверяет инварианты в духе agentic-repository/AGENT_SPEC.md:
  - manifest.id совпадает с именем директории репозитория;
  - все пути, объявленные в manifest.yaml, существуют;
  - обязательные core-файлы на месте;
  - в манифесте нет значений секретов (только имена переменных).
"""

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "manifest.yaml"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.exists(), "manifest.yaml не найден в корне репозитория"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_id_matches_directory(manifest):
    assert manifest["id"] == REPO_ROOT.name


def test_manifest_required_fields(manifest):
    for field in ("id", "name", "description", "owner", "runtimes"):
        assert manifest.get(field), f"Обязательное поле manifest.{field} отсутствует или пусто"


def test_manifest_runtime_paths_exist(manifest):
    for runtime_name, runtime in manifest["runtimes"].items():
        docs = runtime.get("docs")
        assert docs, f"runtimes.{runtime_name}.docs не задан"
        assert (REPO_ROOT / docs).is_file(), f"Не существует: {docs}"

        for os_name, install_path in (runtime.get("install") or {}).items():
            assert (REPO_ROOT / install_path).is_file(), (
                f"runtimes.{runtime_name}.install.{os_name}: не существует {install_path}"
            )


def test_supported_runtime_has_readme(manifest):
    for runtime_name, runtime in manifest["runtimes"].items():
        if runtime.get("supported"):
            readme = REPO_ROOT / "runtimes" / runtime_name / "README.md"
            assert readme.is_file(), f"Нет README для поддерживаемого runtime {runtime_name}"


def test_core_files_exist(manifest):
    for rel in (
        "core/README.md",
        "core/instructions.md",
        "core/prompts/postprocess.system.md",
        "core/contracts/pipeline_contract.md",
        "core/contracts/postprocess_contract.md",
        "core/contracts/error_contract.md",
    ):
        assert (REPO_ROOT / rel).is_file(), f"Обязательный core-файл отсутствует: {rel}"


def test_prompt_frontmatter():
    text = (REPO_ROOT / "core" / "prompts" / "postprocess.system.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    assert match, "У промпта отсутствует YAML frontmatter"
    meta = yaml.safe_load(match.group(1))
    assert meta.get("name") == "postprocess.system"
    assert meta.get("version"), "frontmatter промпта должен содержать version"
    assert text[match.end():].strip(), "Тело промпта пустое"


def test_manifest_contains_no_secret_values(manifest):
    """В secrets допустимы только имена переменных (SCREAMING_SNAKE_CASE)."""
    secrets = manifest.get("secrets") or {}
    for group in ("required", "optional"):
        for name in secrets.get(group) or []:
            assert re.fullmatch(r"[A-Z][A-Z0-9_]*", str(name)), (
                f"secrets.{group}: '{name}' не похоже на имя переменной окружения — "
                "в манифесте допустимы только имена, не значения"
            )
