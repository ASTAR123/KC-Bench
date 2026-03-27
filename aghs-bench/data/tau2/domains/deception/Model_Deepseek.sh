#!/bin/bash

export CUDA_VISIBLE_DEVICES=0,1
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export OPENAI_API_BASE=http://localhost:8000/v1
export OPENAI_API_KEY=local-testing
export VLLM_HTTP_CONNECTION_TIMEOUT=1200
export VLLM_API_TIMEOUT=1200

PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python

$PYTHON_EXEC -m vllm.entrypoints.openai.api_server \
    --model /mnt/shared-storage-user/ai4good2-share/models/deepseek-ai/DeepSeek-R1-Distill-Llama-70B  \
    --served-model-name deepseek \
    --tensor-parallel-size 2 \
    --port 8000 \
    --max-model-len 65536 \
    --hf-overrides '{"rope_scaling": {"rope_type": "dynamic", "factor": 2.0}, "max_position_embeddings": 65536}' \
    --enforce-eager \
    --enable-auto-tool-choice \
    --tool-call-parser hermes > /mnt/shared-storage-user/lvyaxing/Jie/Agent_Honesty/aghs-bench/data/tau2/domains/deception/log/1_Deepseek.log 2>&1 &

echo "正在等待模型加载 (预计 2-5 分钟)..."
# 循环检查 8000 端口是否连通
while ! curl -s http://localhost:8000/v1/models > /dev/null; do
    sleep 10
    echo "模型加载中，请稍候..."
done
echo "vLLM 服务已就绪！"

echo "开始运行 tau2 评测..."
$PYTHON_EXEC -m tau2.cli run \
    --domain deception \
    --agent-llm openai/deepseek \
    --user-llm openai/deepseek \
    --num-trials 1 \
    --max-concurrency 5