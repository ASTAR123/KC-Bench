#!/bin/bash

# --- 基础配置 ---
export CUDA_VISIBLE_DEVICES=0,1
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export VLLM_HTTP_CONNECTION_TIMEOUT=3600
export VLLM_API_TIMEOUT=3600


PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/qwen35/bin/python
LITELLM_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/litellm


# --- 1. 自动生成 LiteLLM 配置文件 (注入禁用思考参数) ---
cat <<EOF > ./litellm_config.yaml
model_list:
  - model_name: Qwen/Qwen35B
    litellm_params:
      model: openai/Qwen/Qwen35B
      api_base: http://localhost:8000/v1
      timeout: 3600
      api_key: local-testing
      # 重点：在这里注入禁用思考模式的参数
      extra_body:
        chat_template_kwargs:
          enable_thinking: false
EOF

# --- 2. 启动 vLLM 服务 (Port 8000) ---
$PYTHON_EXEC -m vllm.entrypoints.openai.api_server \
    --model /mnt/shared-storage-user/ai4good2-share/models/Qwen/Qwen3.5-35B-A3B  \
    --served-model-name Qwen/Qwen35B \
    --tensor-parallel-size 2 \
    --port 8000 \
    --max-model-len 131072 \
    --hf-overrides '{"rope_scaling": {"rope_type": "dynamic", "factor": 4.0}, "max_position_embeddings": 131072}' \
    --enforce-eager \
    --enable-auto-tool-choice \
    --trust-remote-code \
    --tool-call-parser hermes &

echo "正在等待 vLLM 模型加载..."
while ! curl -s http://localhost:8000/v1/models > /dev/null; do
    sleep 10
    echo "模型加载中..."
done
echo "所有模型已就绪！"

# --- 3. 启动 LiteLLM 代理 (Port 4000) ---
# 它会将 tau2 的请求转发给 8000，并自动加上禁用思考的参数
echo "启动 LiteLLM 聚合服务..."
$LITELLM_EXEC --config ./litellm_config.yaml --port 4000 &

echo "正在等待 LiteLLM 代理启动..."
sleep 5

# --- 4. 运行 tau2 评测 (指向代理端口 4000) ---
export OPENAI_API_BASE=http://localhost:4000/v1
export OPENAI_API_KEY=local-testing

echo "开始运行 tau2 评测 (已禁用 Thinking)..."
$PYTHON_EXEC -m tau2.cli run \
    --domain knowledge_conflict \
    --agent-llm openai/Qwen/Qwen35B \
    --user-llm openai/Qwen/Qwen35B \
    --num-trials 300 \
    --max-concurrency 5 \
    --max-step 30

# 任务结束后清理进程 (可选)
# pkill -f vllm
# pkill -f litellm