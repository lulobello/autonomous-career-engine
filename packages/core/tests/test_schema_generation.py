from pathlib import Path

from autonomous_career_engine.core.schema import check_schemas, render_schemas, write_schemas

CORE_ROOT = Path(__file__).parents[1]


def test_public_schema_registry_is_stable() -> None:
    assert set(render_schemas()) == {
        "candidate-profile.schema.json",
        "canonical-job.schema.json",
    }


def test_rendered_schemas_are_deterministic_json_documents() -> None:
    rendered = render_schemas()

    assert rendered == render_schemas()
    assert all(content.endswith("\n") for content in rendered.values())
    assert '"$schema": "https://json-schema.org/draft/2020-12/schema"' in rendered[
        "candidate-profile.schema.json"
    ]


def test_write_schemas_creates_artifacts_that_check_cleanly(tmp_path: Path) -> None:
    write_schemas(tmp_path)

    assert check_schemas(tmp_path) == []


def test_check_schemas_reports_missing_or_stale_artifacts(tmp_path: Path) -> None:
    write_schemas(tmp_path)
    (tmp_path / "canonical-job.schema.json").write_text("stale\n", encoding="utf-8")

    assert check_schemas(tmp_path) == ["canonical-job.schema.json"]


def test_checked_in_schemas_match_models() -> None:
    assert check_schemas(CORE_ROOT / "schemas" / "v1") == []
