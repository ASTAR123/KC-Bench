#!/bin/bash
export CUDA_VISIBLE_DEVICES=0,1
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export OPENAI_API_BASE=http://localhost:8000/v1
export OPENAI_API_KEY=local-testing
export VLLM_HTTP_CONNECTION_TIMEOUT=3600
export VLLM_API_TIMEOUT=3600
export TIKTOKEN_ENCODINGS_BASE=/mnt/shared-storage-user/lvyaxing/tiktoken_encodings
export TIKTOKEN_RS_CACHE_DIR=/mnt/shared-storage-user/lvyaxing/tiktoken_encodings


PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python

$PYTHON_EXEC -m vllm.entrypoints.openai.api_server \
    --model /mnt/shared-storage-user/ai4good2-share/models/openai/gpt-oss-120b  \
    --served-model-name gpt \
    --tensor-parallel-size 2 \
    --port 8000 \
    --enforce-eager \
    --enable-auto-tool-choice \
    --trust-remote-code \
    --tool-call-parser openai &

echo "正在等待模型加载 (预计 2-5 分钟)..."
# 循环检查 8000 端口是否连通
while ! curl -s http://localhost:8000/v1/models > /dev/null; do
    sleep 10
    echo "模型加载中，请稍候..."
done
echo "vLLM 服务已就绪！"

PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python
$PYTHON_EXEC -m tau2.cli run \
    --domain knowledge_conflict \
    --agent-llm openai/gpt \
    --user-llm openai/gpt \
    --num-trials 20 \
    --max-concurrency 10 \
    --max-step 30






#!/bin/bash
# export CUDA_VISIBLE_DEVICES=0,1
# export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
# export OPENAI_API_BASE=http://localhost:8000/v1
# export OPENAI_API_KEY=local-testing
# export VLLM_HTTP_CONNECTION_TIMEOUT=3600
# export VLLM_API_TIMEOUT=3600
# export TIKTOKEN_ENCODINGS_BASE=/mnt/shared-storage-user/lvyaxing/tiktoken_encodings
# export TIKTOKEN_RS_CACHE_DIR=/mnt/shared-storage-user/lvyaxing/tiktoken_encodings


# PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python

# $PYTHON_EXEC -m vllm.entrypoints.openai.api_server \
#     --model /mnt/shared-storage-user/ai4good2-share/models/openai/gpt-oss-120b  \
#     --served-model-name gpt \
#     --tensor-parallel-size 2 \
#     --port 8000 \
#     --enforce-eager \
#     --enable-auto-tool-choice \
#     --trust-remote-code \
#     --tool-call-parser openai &

# echo "正在等待模型加载 (预计 2-5 分钟)..."
# # 循环检查 8000 端口是否连通
# while ! curl -s http://localhost:8000/v1/models > /dev/null; do
#     sleep 10
#     echo "模型加载中，请稍候..."
# done
# echo "vLLM 服务已就绪！"

# PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python
# $PYTHON_EXEC -m tau2.cli run \
#     --domain knowledge_conflict \
#     --agent-llm openai/gpt \
#     --user-llm openai/gpt \
#     --num-trials 1 \
#     --max-concurrency 10 \
#     --max-step 30