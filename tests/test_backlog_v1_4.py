from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "docs" / "backlog" / "2026-05-17_backlog_rag-optimization_v1.4.md"
CHANGELOG = ROOT / "CHANGELOG.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_backlog_v1_4_exists_and_has_required_contract_sections() -> None:
    text = _read(BACKLOG)

    required_fragments = [
        "— v1.4",
        "**Версия:** v1.4",
        "2026-05-17_backlog_rag-optimization_v1.3.md",
        "### 0.6. Актуальный статус задач (v1.4)",
        "## 15. 🗄 Архив (Sprint 3)",
        "| ID | Задача | Приоритет | Статус | Зависимости | Обоснование | DoD |",
        "| BL-47 | Research: ARM Installer, Cloud TZ Access & Documentation Update Flow | P1 | ⏳ Waiting | BL-43, BL-45 |",
        "| **v1.4** | **2026-05-20** | **BL-46:** Archive BL-34..BL-45, add BL-47 research.",
    ]
    for fragment in required_fragments:
        assert fragment in text


def test_backlog_v1_4_archives_completed_sprint_3_tasks() -> None:
    text = _read(BACKLOG)

    for task_id in range(34, 46):
        assert f"| BL-{task_id} |" in text

    required_artifacts = [
        "../audit/2026-05-19_bl-34_architecture-consistency-audit_v1.md",
        "../audit/2026-05-20_bl-43-smoke-e2e-report_v1.md",
        "../user_guide/README.md",
        "../runbooks/arm-deployment-ivan.md",
    ]
    for artifact in required_artifacts:
        assert artifact in text


def test_changelog_mentions_bl46_backlog_update() -> None:
    text = _read(CHANGELOG)

    assert "DOCUMENTATION: BL-46 backlog branch update to v1.4" in text
