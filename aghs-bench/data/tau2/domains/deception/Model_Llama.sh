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
    --tool-call-parser llama3_json &

echo "正在等待模型加载 (预计 2-5 分钟)..."
# 循环检查 8000 端口是否连通
while ! curl -s http://localhost:8000/v1/models > /dev/null; do
    sleep 10
    echo "模型加载中，请稍候..."
done
echo "vLLM 服务已就绪！"

# echo "开始运行 tau2 评测1..."
# $PYTHON_EXEC -m tau2.cli run \
#     --domain deception \
#     --agent-llm openai/llama3.3-70b \
#     --user-llm openai/llama3.3-70b \
#     --num-trials 1 \
#     --max-concurrency 5 \
#     --max-step 100

echo "开始运行 tau2 评测2..."
$PYTHON_EXEC -m tau2.cli run \
    --domain sycophancy \
    --agent-llm openai/llama3.3-70b \
    --user-llm openai/llama3.3-70b \
    --num-trials 1 \
    --max-concurrency 5 \
    --max-step 100





# # export CUDA_VISIBLE_DEVICES=0,1
# # VLLM_USE_V1=0 VLLM_ALLOW_LONG_MAX_MODEL_LEN=1 python -m vllm.entrypoints.openai.api_server \
# #     --model /mnt/shared-storage-user/ai4good2-share/models/meta-llama/Llama-3.3-70B-Instruct \
# #     --served-model-name llama3.3-70b \
# #     --tensor-parallel-size 2 \
# #     --port 8000 \
# #     --max-model-len 131072 \
# #     --hf-overrides '{"rope_scaling": {"type": "dynamic", "factor": 4.0}, "max_position_embeddings": 131072}' \
# #     --enforce-eager \
# #     --enable-auto-tool-choice \
# #     --tool-call-parser llama3_json &

# # export OPENAI_API_BASE=http://localhost:8000/v1
# # export OPENAI_API_KEY=local-testing
# # python -m tau2.cli run \
# #     --domain deception \
# #     --agent-llm openai/llama3.3-70b \
# #     --user-llm openai/llama3.3-70b \
# #     --num-trials 1 \
# #     --max-concurrency 10 \
# #     --max-step 100