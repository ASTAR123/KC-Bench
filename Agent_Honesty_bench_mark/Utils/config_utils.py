from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


def read_config(config_path: Path | str = "config.yaml") -> Dict[str, Any]:
    """Load YAML configuration."""
    config_path = Path(config_path)
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    return config
