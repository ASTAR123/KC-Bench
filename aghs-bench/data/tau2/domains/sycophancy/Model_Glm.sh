#!/bin/bash

export CUDA_VISIBLE_DEVICES=0,1
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export OPENAI_API_BASE=http://localhost:8000/v1
export OPENAI_API_KEY=local-testing
export VLLM_HTTP_CONNECTION_TIMEOUT=3600
export VLLM_API_TIMEOUT=3600

PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python

$PYTHON_EXEC -m vllm.entrypoints.openai.api_server \
    --model /mnt/shared-storage-user/ai4good2-share/models/zai-org/GLM-4.5-Air  \
    --served-model-name glm \
    --tensor-parallel-size 2 \
    --port 8000 \
    --max-model-len 131072 \
    --hf-overrides '{"rope_scaling": {"rope_type": "dynamic", "factor": 4.0}, "max_position_embeddings": 131072}' \
    --enforce-eager \
    --enable-auto-tool-choice \
    --tool-call-parser glm45 > /mnt/shared-storage-user/lvyaxing/Jie/Agent_Honesty/aghs-bench/data/tau2/domains/sycophancy/log/1_Glm.log 2>&1 &

echo "正在等待模型加载 (预计 2-5 分钟)..."
# 循环检查 8000 端口是否连通
while ! curl -s http://localhost:8000/v1/models > /dev/null; do
    sleep 10
    echo "模型加载中，请稍候..."
done
echo "vLLM 服务已就绪！"

echo "开始运行 tau2 评测..."
$PYTHON_EXEC -m tau2.cli run \
    --domain knowledge_conflict \
    --agent-llm openai/glm \
    --user-llm openai/glm \
    --num-trials 10 \
    --max-concurrency 5 \
    --max-step 30