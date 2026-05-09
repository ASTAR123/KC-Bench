# $KC$-Bench: Evaluating Conversational Agents under Knowledge Conflict

$KC$-Bench is a simulation framework designed to evaluate Large Language Model (LLM) agents in environments characterized by knowledge conflict. Built upon the $\tau^2$-bench dual-control architecture, it tests an agent's ability to prioritize correct, real-time information over conflicting internal parametric knowledge.

---

## 🆕 What's New

### ⚠️ Knowledge Conflict Scenarios

$KC$-Bench introduces specialized tasks where external tool outputs (e.g., API results) intentionally contradict common knowledge or model training data to test the agent's reasoning and grounding capabilities.

### 🤖 Reinforcement Learning \& Gym Support

- **Gymnasium Interface**: Train agents using standard RL frameworks.
- **Dual-Control**: Seamlessly switch between Agent and User perspectives.
- **Standardized Splits**: Consistent train/test sets across all domains to ensure reproducible research.

---

## 🚀 Quick Start

### 1. Installation

Ensure you have Python 3.10 or higher installed.

```bash
# Clone the repository
git clone https://github.com/triplllllex/KC-Bench
cd KC-Bench

# Create and activate environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .