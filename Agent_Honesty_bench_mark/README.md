# Agent Sandbox and Evaluation - User Guide

## Overview

This is an intelligent agent sandbox and evaluation system based on smolagents, supporting various model types and tools for task execution and performance assessment.

## Features

- **Multi-model Support**: Supports open-source models (Transformers, VLLM) and closed-source models (OpenAI API).
- **Tool System**: Dynamically loads custom tools from the Toolkit directory.
- **Task Execution**: Loads and executes tasks from the Benchmark directory.
- **Multiple Execution Modes**: Supports interactive and batch processing modes.
- **Result Saving**: Automatically saves execution results to a specified directory.

## Usage

### 1. Basic Execution

```bash
# Run with default configuration file

python main.py

# Specify a configuration file

python main.py --config my_config.yaml
```

### 2. Interactive Mode

```bash
# Enter interactive mode to manually input tasks

python main.py --interactive
```

### 3. Execute Specific Task

```bash
# Run a single task

python main.py --task "Please calculate what 1+1 equals"
```

### 4. Batch Processing Mode

```bash
# Run all tasks in the Benchmark directory

python main.py
```

### 5. Run τ-Bench Domains

We have ported the τ-bench airline and retail domains (agents, toolkit, environment data, and benchmark tasks) into this framework. Use the provided configs to run them end-to-end:

```bash
python main.py --config config_tau_airline.yaml   # airline tasks
python main.py --config config_tau_retail.yaml    # retail tasks
```

Each τ-bench task file already references the cloned environment resources, so per-task sandboxes are set up automatically before the agent starts interacting with the tools.

## Configuration File Explanation

### config.yaml Structure

```yaml
Benchmark:
  path: ./Benchmark # Task definition directory
  type: "single-agent multi-round task" # Task type
Toolkit:
  path: ./Toolkit # Tool definition directory
  loader: ./Toolkit/load_tools.py # Tool loading script
Model:
  type: "open-source" # Model type: open-source or closed-source
  name: "hkgai-v1" # Model name
  temperature: 0 # Temperature parameter
  max_new_tokens: 12800 # Maximum number of new tokens
# Open-source model configuration
open_source_details:
  transformer_framework: "transformers"
# Closed-source model configuration
closed_source_details:
  api_url: "https://api.openai.com/v1/completions"
  api_key: "your_api_key"
Output:
  log_dir: ./results/logs # Log directory
  save_dir: ./results/outputs # Result save directory
```

## Directory Structure

```
Project Root Directory/
├── main.py # Main program
├── config.yaml # Configuration file
├── Benchmark/ # Task definition directory
│ ├── tasks.yaml # Task file (YAML format)
│ └── tasks.json # Task file (JSON format)
├── Toolkit/ # Tool definition directory
│ ├── load_tools.py # Tool loading script
│ └── custom_tools.py # Custom tool
├── Environment/ # Environment configuration directory
└── results/ # Result output directory
    ├── logs/ # Log files
    └── outputs/ # Execution results
```

## Tool Development

### Creating Custom Tools

1. Create a tool file in the `Toolkit/` directory.
2. Register the tool in `load_tools.py`.
3. Tools must inherit the `smolagents.Tool` class.

Example:

```python
# Toolkit/custom_tools.py

from smolagents import Tool

class CalculatorTool(Tool):

    def __init__(self):
        super().__init__(
            name="calculator",
            description="Perform basic mathematical calculations",
            inputs={
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to be calculated"
                }
            }
        )

    def forward(self, expression: str):
        try:
            result = eval(expression)
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {e}"

# Toolkit/load_tools.py

from custom_tools import CalculatorTool

def load_tools():
    return [CalculatorTool()]
```

## Task Definition

### YAML Format Task File

```yaml
- description: "Calculate 1+1"
  expected_result: "2"
  category: "math"
- description: "Search for today's weather"
  expected_result: "Weather information"
  category: "search"
```

### JSON Format Task File

```json
[
  {
    "description": "Calculate 1+1",
    "expected_result": "2",
    "category": "math"
  },
  {
    "description": "Search for today's weather",
    "expected_result": "Weather information",
    "category": "search"
  }
]
```

## Output Results

Execution results are saved in JSON format, including:

```json
{
  "task_id": 1,
  "task": {
    "description": "Calculate 1+1",
    "expected_result": "2"
  },
  "result": "Result: 2",
  "timestamp": "2024-01-01T12:00:00",
  "benchmark_type": "single-agent multi-round task"
}
```

## Error Handling