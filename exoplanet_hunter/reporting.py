import json
from pathlib import Path

from pydantic import BaseModel


def save_json_report(report: BaseModel, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
    return str(path.as_posix())
