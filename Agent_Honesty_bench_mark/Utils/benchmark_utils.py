from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml


def load_benchmark_tasks(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Load Benchmark tasks based on configuration."""
    benchmark_config = config.get("Benchmark", {})
    benchmark_path = benchmark_config.get("path", "./Benchmark")

    tasks: List[Dict[str, Any]] = []

    # Check if Benchmark directory exists
    if not os.path.exists(benchmark_path):
        print(f"Warning: Benchmark directory {benchmark_path} does not exist")
        return tasks

    # Try to load task definition files
    if os.path.isfile(benchmark_path):
        task_files = [benchmark_path]
    else:
        task_files = []
        for file in os.listdir(benchmark_path):
            if file.endswith((".yaml", ".yml", ".json", ".jsonl")):
                task_files.append(os.path.join(benchmark_path, file))

    for task_file in task_files:
        source_path = Path(task_file)
        dataset_name = source_path.stem
        try:
            with open(task_file, "r", encoding="utf-8") as f:
                if task_file.endswith(".json"):
                    task_data = json.load(f)
                elif task_file.endswith(".jsonl"):
                    task_data = [json.loads(line) for line in f if line.strip()]
                else:
                    task_data = yaml.safe_load(f)

                def _tag_task(item: Dict[str, Any]) -> Dict[str, Any]:
                    item["_source_file"] = str(source_path)
                    item["_dataset"] = dataset_name
                    return item

                if isinstance(task_data, list):
                    tasks.extend(_tag_task(item) for item in task_data if isinstance(item, dict))
                elif isinstance(task_data, dict):
                    tasks.append(_tag_task(task_data))
        except Exception as exc:
            print(f"Warning: Error loading task file {task_file}: {exc}")

    return tasks
