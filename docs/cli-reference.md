
# CLI Reference

  

The `kc` command provides a unified interface for all τ-bench functionality. Use `kc <command> --help` to see full details for any command.

  

Run `kc intro` (or just `kc`) to see an overview of available domains, commands, and a quick-start guide directly in the terminal.

  

## `kc run` — Run Evaluations

  

Run agent evaluations across different communication modes.

  

### Basic Usage

  

```bash

kc run \

--domain <domain> \

--agent-llm <llm_name> \

--user-llm <llm_name> \

--num-trials <trial_count> \

--num-tasks <task_count>

```

  

### Common Options

  

| Option | Description |

|--------|-------------|

| `--domain`, `-d` | Domain to evaluate: `airline`, `retail`, `telecom`, `mock`, `banking_knowledge` |

| `--agent-llm` | LLM model for the agent |

| `--user-llm` | LLM model for the user simulator |

| `--agent-llm-args` | JSON dict of extra args for agent LLM (e.g. `'{"temperature": 0.5}'`) |

| `--user-llm-args` | JSON dict of extra args for user LLM |

| `--agent` | Agent implementation to use (default: `llm_agent`) |

| `--user` | User simulator implementation to use (default: `user_simulator`) |

| `--num-trials` | Number of evaluation trials (default: `1`) |

| `--num-tasks` | Number of tasks to evaluate (omit for all tasks) |

| `--task-ids` | Specific task IDs to evaluate |

| `--task-split-name` | Task split to use (default: `base`) |

| `--task-set-name` | Task set to use (default: domain default) |

| `--max-steps` | Maximum simulation steps (default: `200`) |

| `--max-errors` | Maximum consecutive tool errors allowed (default: `10`) |

| `--max-concurrency` | Maximum concurrent simulations (default: `3`) |

| `--seed` | Random seed for reproducibility (default: `300`) |

| `--save-to` | Custom output directory name (saved under `data/simulations/`) |

| `--log-level` | Log level (default: `ERROR`) |

| `--max-retries` | Max retries for failed tasks (default: `3`) |

| `--retry-delay` | Delay in seconds between retries (default: `1.0`) |

  

### Examples

  

```bash

# Standard text evaluation

kc run --domain retail --agent-llm gpt-4.1 --user-llm gpt-4.1 --num-trials 1 --num-tasks 5

```

  
  

---

  

## `kc play` — Interactive Play Mode

  

Experience τ-bench interactively from either perspective.

  

```bash

kc play

```

  

Play mode allows you to:

- **Play as Agent**: Manually control the agent's responses and tool calls

- **Play as User**: Control the user while an LLM agent handles requests (available in domains with user tools like telecom)

- **Understand tasks** by walking through scenarios step-by-step

- **Test strategies** before implementing them in code

- **Choose task splits** to practice on training data or test on held-out tasks

  

---

  

## `kc view` — View Results

  

Browse and analyze simulation results.

  

```bash

kc view

```

  

| Option | Description |

|--------|-------------|

| `--dir` | Directory containing simulation files (defaults to `data/simulations/`) |

| `--file` | Path to a specific results file to view |

| `--only-show-failed` | Only show failed tasks |

| `--only-show-all-failed` | Only show tasks that failed in all trials |

| `--expanded-ticks` | Show expanded tick view (for full-duplex simulations) |

  

---

  

## `kc domain` — View Domain Documentation

  

View domain policy and API documentation.

  

```bash

kc domain <domain>

```

  

---

  

## `kc check-data` — Check Data Configuration

  

Verify that your data directory is properly configured.

  

```bash

kc check-data

```