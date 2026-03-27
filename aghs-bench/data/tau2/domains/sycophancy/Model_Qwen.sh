#!/bin/bash

export CUDA_VISIBLE_DEVICES=0,1
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export OPENAI_API_BASE=http://localhost:8000/v1
export OPENAI_API_KEY=local-testing

PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/Qwen/bin/python

$PYTHON_EXEC -m vllm.entrypoints.openai.api_server \
    --model /mnt/shared-storage-user/ai4good2-share/models/Qwen/models-Qwen-Qwen3.5-35B-A3B  \
    --served-model-name qwen3.5-35b \
    --tensor-parallel-size 2 \
    --port 8000 \
    --max-model-len 131072 \
    --enforce-eager \
    --enable-auto-tool-choice \
    --trust-remote-code \
    --tool-call-parser hermes > /mnt/shared-storage-user/lvyaxing/Jie/Agent_Honesty/aghs-bench/data/tau2/domains/sycophancy/log/1_Qwen.log 2>&1 &

echo "正在等待模型加载 (预计 2-5 分钟)..."
# 循环检查 8000 端口是否连通
while ! curl -s http://localhost:8000/v1/models > /dev/null; do
    sleep 10
    echo "模型加载中，请稍候..."
done
echo "vLLM 服务已就绪！"

echo "开始运行 tau2 评测..."
$PYTHON_EXEC -m tau2.cli run \
    --domain sycophancy \
    --agent-llm openai/qwen3.5-35b \
    --user-llm openai/qwen3.5-35b \
    --num-trials 1