#!/bin/bash
export CUDA_VISIBLE_DEVICES=0,1
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export OPENAI_API_BASE=http://localhost:8000/v1
export OPENAI_API_KEY=local-testing
export VLLM_HTTP_CONNECTION_TIMEOUT=3600
export VLLM_API_TIMEOUT=3600

PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python

$PYTHON_EXEC -m vllm.entrypoints.openai.api_server \
    --model /mnt/shared-storage-user/ai4good2-share/models/meta-llama/Llama-3.3-70B-Instruct \
    --served-model-name llama3.3-70b \
    --tensor-parallel-size 2 \
    --port 8000 \
    --max-model-len 131072 \
    --hf-overrides '{"rope_scaling": {"rope_type": "dynamic", "factor": 4.0}, "max_position_embeddings": 131072}' \
    --enforce-eager \
    --enable-auto-tool-choice \
    --tool-call-parser llama3_json > /mnt/shared-storage-user/lvyaxing/Jie/Agent_Honesty/aghs-bench/data/tau2/domains/sycophancy/log/1_Llama.log 2>&1 &

while ! curl -s http://localhost:8000/health > /dev/null; do
    sleep 10
    echo "正在等待 API 健康检查通过..."
done

echo "开始运行 tau2 评测..."
$PYTHON_EXEC -m tau2.cli run \
    --domain knowledge_conflict \
    --agent-llm openai/llama3.3-70b \
    --user-llm openai/llama3.3-70b \
    --num-trials 1 \
    --max-concurrency 8 \
    --max-step 30







# $PYTHON_EXEC -m tau2.cli run \
#     --domain sycophancy \
#     --agent-llm openai/llama3.3-70b \
#     --user-llm openai/llama3.3-70b \
#     --num-trials 1 \
#     --max-concurrency 10 \
#     --max-step 100

# $PYTHON_EXEC -m tau2.cli run \
#     --domain deception \
#     --agent-llm openai/llama3.3-70b \
#     --user-llm openai/llama3.3-70b \
#     --num-trials 1 \
#     --max-concurrency 10 \
#     --max-step 100
