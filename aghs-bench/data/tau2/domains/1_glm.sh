#!/bin/bash

export VLLM_HTTP_CONNECTION_TIMEOUT=3600
export VLLM_API_TIMEOUT=3600

# --- 基础配置 ---
PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python
LITELLM_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/litellm
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1

cat <<EOF > ./litellm_config.yaml
model_list:
  - model_name: glm
    litellm_params:
      model: openai/glm
      api_base: http://localhost:8000/v1
      api_key: local-testing
      timeout: 3600

  - model_name: Qwen/Qwen2.5-72B-Instruct
    litellm_params:
      model: openai/Qwen/Qwen2.5-72B-Instruct
      api_base: http://localhost:8001/v1
      api_key: local-testing
      timeout: 3600

router_settings:
  routing_strategy: simple-shuffle
  cooldown_time: 0
  num_retries: 3
EOF

CUDA_VISIBLE_DEVICES=0,1 $PYTHON_EXEC -m vllm.entrypoints.openai.api_server \
    --model /mnt/shared-storage-user/ai4good2-share/models/zai-org/GLM-4.5-Air  \
    --served-model-name glm \
    --tensor-parallel-size 2 \
    --port 8000 \
    --max-model-len 131072 \
    --hf-overrides '{"rope_scaling": {"rope_type": "dynamic", "factor": 4.0}, "max_position_embeddings": 131072}' \
    --enforce-eager \
    --enable-auto-tool-choice \
    --tool-call-parser glm45 &


CUDA_VISIBLE_DEVICES=2,3 $PYTHON_EXEC -m vllm.entrypoints.openai.api_server \
    --model /mnt/shared-storage-user/ai4good2-share/models/Qwen/Qwen2.5-72B-Instruct  \
    --served-model-name Qwen/Qwen2.5-72B-Instruct \
    --tensor-parallel-size 2 \
    --port 8001 \
    --max-model-len 131072 \
    --hf-overrides '{"rope_scaling": {"rope_type": "dynamic", "factor": 4.0}, "max_position_embeddings": 131072}' \
    --enforce-eager \
    --enable-auto-tool-choice \
    --trust-remote-code \
    --tool-call-parser hermes > /mnt/shared-storage-user/lvyaxing/Jie/Agent_Honesty/aghs-bench/data/tau2/domains/log/1_Qwen.log 2>&1 &


echo "正在等待两个模型加载..."
while ! curl -s http://localhost:8000/v1/models > /dev/null || ! curl -s http://localhost:8001/v1/models > /dev/null; do
    sleep 10
    echo "模型加载中..."
done
echo "所有模型已就绪！"

echo "启动 LiteLLM 聚合服务..."
$LITELLM_EXEC --config ./litellm_config.yaml --port 4000 &

while ! curl -s http://localhost:4000/health > /dev/null; do
    sleep 2
    echo "正在等待 LiteLLM 代理启动..."
done
echo "所有服务已就绪！代理地址: http://localhost:4000"

export OPENAI_API_BASE=http://localhost:4000/v1
export OPENAI_API_KEY=local-testing

# 示例：Agent 用 Llama，User 用 GLM
$PYTHON_EXEC -m tau2.cli run \
    --domain deception \
    --agent-llm openai/glm \
    --user-llm openai/Qwen/Qwen2.5-72B-Instruct \
    --num-trials 1 \
    --max-concurrency 10 \
    --max-step 120

$PYTHON_EXEC -m tau2.cli run \
    --domain sycophancy \
    --agent-llm openai/glm \
    --user-llm openai/Qwen/Qwen2.5-72B-Instruct \
    --num-trials 1 \
    --max-concurrency 10 \
    --max-step 120