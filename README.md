# $KC$-Bench: Evaluating Conversational Agents under Knowledge Conflict

  

$KC$-Bench is a simulation framework designed to evaluate Large Language Model (LLM) agents in environments characterized by knowledge conflict. Built upon the $\tau^2$-bench dual-control architecture, it tests an agent's ability to prioritize correct, real-time information over conflicting internal parametric knowledge.

  

---

  

## 🆕 What's New

  

### ⚠️ Knowledge Conflict Scenarios

  

$KC$-Bench introduces specialized tasks where external tool outputs intentionally contradict common knowledge in model training data or user-provided incorrect information, in order to test the agent's reasoning and grounding capabilities.
We have designed tasks and databases in three areas: retail, personal assistant, and region. In retail, we examine the knowledge conflicts between user input and the database. In personal assistant, we investigate the internal conflicts within the database. And in region, we explore the conflicts between user input and common sense which is from model training data.

  Each domain specifies:

- A **policy** that the agent must follow
- A set of **tools** that the agent can use
- A set of **tasks** to evaluate the agent's performance
- Optionally: a set of **user tools** for the user simulator

**Available domains**: `region` · `retail` · `personalAssistant`

---

  

## 🚀 Quick Start

  

### 1. Installation

  

Ensure you have Python 3.10 or higher installed.

  

```bash

# Clone the repository

git clone https://github.com/ASTAR123/KC-Bench

cd KC-Bench

  

# Create and activate environment

python -m venv .venv

source .venv/bin/activate

  

# Install in editable mode

pip install -e .

```

  

### 2. Configuration

  

Set up your LLM API keys by copying the example environment file:

  

```bash

cp .env.example .env

```

  

Edit `.env` to include your provider keys (OpenAI, Anthropic, etc.).

  

---

  

## 3. Run Evaluation

  


To run a knowledge conflict evaluation in the region domain:

  

```bash

kc run \

--domain region \

--agent-llm gpt-4o \

--user-llm gpt-4o \

--num-trials 1

```

  To run a knowledge conflict evaluation in the retail domain:

  

```bash

kc run \

--domain retail \

--agent-llm gpt-4o \

--user-llm gpt-4o \

--num-trials 1

```

  To run a knowledge conflict evaluation in the personal assistant domain:

  

```bash

kc run \

--domain personalAssistant \

--agent-llm gpt-4o \

--user-llm gpt-4o \

--num-trials 1

```

  

Results will be stored in:

  

```text

data/KC-Bench/simulations/

```

  

---

  

## 🛠️ Command Line Interface

  

## `tau2 run` — Run Evaluations


Run agent evaluations across different communication modes.

### Basic Usage

```shell
tau2 run \
  --domain <domain> \
  --agent-llm <llm_name> \
  --user-llm <llm_name> \
  --num-trials <trial_count> \
  --num-tasks <task_count>
```
### Common Options

| Option              | Description                                                                     |
| ------------------- | ------------------------------------------------------------------------------- |
| `--domain`, `-d`    | Domain to evaluate: `region`, `retail`, `personalAssistant`                     |
| `--agent-llm`       | LLM model for the agent                                                         |
| `--user-llm`        | LLM model for the user simulator                                                |
| `--agent-llm-args`  | JSON dict of extra args for agent LLM (e.g. `'{"temperature": 0.5}'`)           |
| `--user-llm-args`   | JSON dict of extra args for user LLM                                            |
| `--agent`           | Agent implementation to use (default: `llm_agent`)                              |
| `--user`            | User simulator implementation to use (default: `user_simulator`)                |
| `--num-trials`      | Number of evaluation trials (default: `1`)                                      |
| `--num-tasks`       | Number of tasks to evaluate (omit for all tasks)                                |
| `--task-ids`        | Specific task IDs to evaluate                                                   |
| `--task-split-name` | Task split to use (default: `base`)                                             |
| `--task-set-name`   | Task set to use (default: domain default)                                       |
| `--max-steps`       | Maximum simulation steps (default: `200`)                                       |
| `--max-errors`      | Maximum consecutive tool errors allowed (default: `10`)                         |
| `--max-concurrency` | Maximum concurrent simulations (default: `3`)                                   |
| `--seed`            | Random seed for reproducibility (default: `300`)                                |
| `--save-to`         | Custom output directory name (saved under `data/simulations/`)                  |
| `--log-level`       | Log level (default: `ERROR`)                                                    |
| `--verbose-logs`    | Save detailed logs (LLM calls, audio, ticks)                                    |
| `--audio-debug`     | Save per-tick audio files and timing analysis (requires `--audio-native`)       |
| `--llm-log-mode`    | LLM log mode when `--verbose-logs` is on: `all` or `latest` (default: `latest`) |
| `--max-retries`     | Max retries for failed tasks (default: `3`)                                     |
| `--retry-delay`     | Delay in seconds between retries (default: `1.0`)                               |

You can find all `tau2` commands and options in [CLI Reference](docs/cli_reference.md)

## `tau2 view` — View Results


Browse and analyze simulation results(defaults to `data/simulations/`).

```shell
tau2 view
```


  

---


## 📝 Citation

  

If you use $KC$-Bench in your research, please cite this repository and the original $\tau^2$-bench framework:

  
### Our KC-Bench

```bibtex

@misc{kc-bench2026,

title={KC-Bench: A Dynamic Interactive Benchmark for Evaluating Knowledge Conflicts in LLM Agents},

author={ASTAR123},

year={2026},

publisher={GitHub},

journal={GitHub Repository},

howpublished={\url{https://github.com/ASTAR123/KC-Bench}}

}

```
### Core τ-Bench

[](https://github.com/sierra-research/tau2-bench#core-tau-bench)

```bibtex
@misc{barres2025tau2,
      title={$\tau^2$-Bench: Evaluating Conversational Agents in a Dual-Control Environment}, 
      author={Victor Barres and Honghua Dong and Soham Ray and Xujie Si and Karthik Narasimhan},
      year={2025},
      eprint={2506.07982},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2506.07982}, 
}

@misc{yao2024tau,
      title={$\tau$-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains}, 
      author={Shunyu Yao and Noah Shinn and Pedram Razavi and Karthik Narasimhan},
      year={2024},
      eprint={2406.12045},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2406.12045}, 
}
```