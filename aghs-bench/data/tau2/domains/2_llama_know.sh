#!/bin/bash

# --- 基础配置 ---
export CUDA_VISIBLE_DEVICES=0,1
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export VLLM_HTTP_CONNECTION_TIMEOUT=3600
export VLLM_API_TIMEOUT=3600


PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python

# --- 2. 启动 vLLM 服务 (Port 8000) ---
$PYTHON_EXEC -m vllm.entrypoints.openai.api_server \
    --model /mnt/shared-storage-user/ai4good2-share/models/meta-llama/Llama-3.3-70B-Instruct \
    --served-model-name llama3.3-70b \
    --tensor-parallel-size 2 \
    --port 8000 \
    --max-model-len 131072 \
    --hf-overrides '{"rope_scaling": {"rope_type": "dynamic", "factor": 4.0}, "max_position_embeddings": 131072}' \
    --enforce-eager \
    --enable-auto-tool-choice \
    --trust-remote-code \
    --tool-call-parser llama3_json &

echo "正在等待 vLLM 模型加载..."
while ! curl -s http://localhost:8000/v1/models > /dev/null; do
    sleep 10
    echo "模型加载中..."
done
echo "所有模型已就绪！"

export OPENAI_API_BASE=http://localhost:8000/v1
export OPENAI_API_KEY=local-testing



echo "开始运行 tau2 评测..."
PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python
$PYTHON_EXEC -m tau2.cli run \
    --domain knowledge_conflict \
    --agent-llm openai/llama3.3-70b \
    --user-llm openai/llama3.3-70b \
    --num-trials 1 \
    --max-concurrency 5 \
    --max-step 30

# PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python
# $PYTHON_EXEC -m tau2.cli run \
#     --domain sycophancy \
#     --agent-llm openai/Qwen/Qwen2.5-72B-Instruct \
#     --user-llm openai/Qwen/Qwen2.5-72B-Instruct \
#     --num-trials 1 \
#     --max-concurrency 5 \
#     --max-step 120


# PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python
# $PYTHON_EXEC -m tau2.cli run \
#     --domain knowledge_conflict \
#     --agent-llm openai/Qwen/Qwen2.5-72B-Instruct \
#     --user-llm openai/Qwen/Qwen2.5-72B-Instruct \
#     --num-trials 1 \
#     --max-concurrency 5 \
#     --max-step 30

# PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python
# $PYTHON_EXEC -m tau2.cli run \
#     --domain faithfulness \
#     --agent-llm openai/Qwen/Qwen2.5-72B-Instruct \
#     --user-llm openai/Qwen/Qwen2.5-72B-Instruct \
#     --num-trials 1 \
#     --max-concurrency 5 \
#     --max-step 120



# 任务结束后清理进程 (可选)
# pkill -f vllm
# pkill -f litellm