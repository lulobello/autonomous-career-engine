import argparse
import json
from pathlib import Path

from pydantic import BaseModel

from .models.candidate import CandidateProfile
from .models.job import CanonicalJob

PUBLIC_SCHEMAS: dict[str, tuple[type[BaseModel], str]] = {
    "candidate-profile.schema.json": (
        CandidateProfile,
        "https://github.com/lulobello/autonomous-career-engine/schemas/v1/candidate-profile.schema.json",
    ),
    "canonical-job.schema.json": (
        CanonicalJob,
        "https://github.com/lulobello/autonomous-career-engine/schemas/v1/canonical-job.schema.json",
    ),
}

STRUCTURAL_SCHEMA_COMMENT = (
    "Structural validation layer only; cross-record references, identifier uniqueness, "
    "and cross-value ordering require the semantic rules documented in packages/core/README.md."
)


def render_schemas() -> dict[str, str]:
    rendered: dict[str, str] = {}
    for filename, (model, schema_id) in PUBLIC_SCHEMAS.items():
        schema = model.model_json_schema(mode="serialization")
        schema["$id"] = schema_id
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$comment"] = STRUCTURAL_SCHEMA_COMMENT
        rendered[filename] = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    return rendered


def write_schemas(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in render_schemas().items():
        (output_dir / filename).write_text(content, encoding="utf-8")


def check_schemas(output_dir: Path) -> list[str]:
    mismatches: list[str] = []
    for filename, expected in render_schemas().items():
        path = output_dir / filename
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            mismatches.append(filename)
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate public core JSON Schemas")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parents[3] / "schemas" / "v1",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        mismatches = check_schemas(args.output_dir)
        if mismatches:
            parser.error(f"schema artifacts are stale: {', '.join(mismatches)}")
        return 0
    write_schemas(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
