# $KC$-Bench: Evaluating Conversational Agents under Knowledge Conflict

$KC$-Bench is a simulation framework designed to evaluate Large Language Model (LLM) agents in environments characterized by knowledge conflict. Built upon the $\tau^2$-bench dual-control architecture, it tests an agent's ability to prioritize correct, real-time information over conflicting internal parametric knowledge.

---

## 🆕 What's New

### ⚠️ Knowledge Conflict Scenarios

$KC$-Bench introduces specialized tasks where external tool outputs intentionally contradict common knowledge in model training data or user wrong input to test the agent's reasoning and grounding capabilities.


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

## 2. Configuration

Set up your LLM API keys by copying the example environment file:

```bash
cp .env.example .env
```

Edit `.env` to include your provider keys (OpenAI, Anthropic, etc.).

---

## 3. Run Evaluation

To run a test evaluation on 5 tasks in the airline domain:

```bash
kc run \
  --domain knowledge_conflict \
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

The `kc-bench` command serves as the primary entry point:

| Command | Description |
|---|---|
| `kc run` | Execute the benchmark across specified domains. |
| `kc-bench view` | Browse and analyze simulation trajectories. |

---

## 📂 Project Structure

```text
src/kc/domains/     # Core logic for different service domains (Airline, Retail, etc.)
data/KC-Bench/domains/    # Environment data and task definitions
```

---

## 📝 Citation

If you use $KC$-Bench in your research, please cite this repository and the original $\tau^2$-bench framework:

```bibtex
@misc{kc-bench2026,
      title={KC-Bench: A Dynamic Interactive Benchmark for Evaluating Knowledge Conflicts in LLM Agents},
      author={ASTAR123},
      year={2026},
      publisher={GitHub},
      journal={GitHub Repository},
      howpublished={\url{https://github.com/sierra-research/tau2-bench}}
}
```