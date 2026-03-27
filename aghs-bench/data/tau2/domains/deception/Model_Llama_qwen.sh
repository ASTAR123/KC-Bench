#!/bin/bash

# ================= 配置区域 =================
PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python

# 模型路径
LLAMA_MODEL=/mnt/shared-storage-user/ai4good2-share/models/meta-llama/Llama-3.3-70B-Instruct
QWEN_MODEL=/mnt/shared-storage-user/ai4good2-share/models/Qwen/Qwen2.5-72B-Instruct # 请根据实际路径修改

# 环境变量
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export OPENAI_API_KEY=local-testing
export VLLM_HTTP_CONNECTION_TIMEOUT=3600
export VLLM_API_TIMEOUT=3600

# ================= 启动 Llama (Agent) - 端口 8000 =================
echo "正在启动 Llama (Agent) 于端口 8000..."
CUDA_VISIBLE_DEVICES=0,1 $PYTHON_EXEC -m vllm.entrypoints.openai.api_server \
    --model $LLAMA_MODEL \
    --served-model-name llama3.3-70b \
    --tensor-parallel-size 2 \
    --port 8000 \
    --max-model-len 131072 \
    --hf-overrides '{"rope_scaling": {"rope_type": "dynamic", "factor": 4.0}, "max_position_embeddings": 131072}' \
    --enforce-eager \
    --enable-auto-tool-choice \
    --tool-call-parser llama3_json &

# ================= 启动 Qwen (User) - 端口 8001 =================
echo "正在启动 Qwen (User) 于端口 8001..."
# 假设 Qwen 也需要 2 张卡，如果没有足够显卡，请调整设备 ID 或 TP 规模
CUDA_VISIBLE_DEVICES=2,3 $PYTHON_EXEC -m vllm.entrypoints.openai.api_server \
    --model $QWEN_MODEL \
    --served-model-name qwen2.5 \
    --tensor-parallel-size 2 \
    --port 8001 \
    --max-model-len 131072 \
    --hf-overrides '{"rope_scaling": {"rope_type": "dynamic", "factor": 4.0}, "max_position_embeddings": 131072}' \
    --enforce-eager \
    --enable-auto-tool-choice \
    --trust-remote-code \
    --tool-call-parser hermes > /mnt/shared-storage-user/lvyaxing/Jie/Agent_Honesty/aghs-bench/data/tau2/domains/deception/log/1_Qwen.log 2>&1 &


# ================= 等待服务就绪 =================
wait_for_port() {
    local port=$1
    echo "等待端口 $port 就绪..."
    while ! curl -s http://localhost:$port/v1/models > /dev/null; do
        sleep 10
    done
    echo "端口 $port 已就绪！"
}

wait_for_port 8000
wait_for_port 8001

# ================= 运行 Tau2 评测 =================
echo "开始运行 tau2 评测 (Agent: Llama, User: Qwen)..."

echo "开始运行 tau2 评测1..."
$PYTHON_EXEC -m tau2.cli run \
    --domain deception \
    --agent-llm openai/llama3.3-70b \
    --user-llm openai/qwen2.5 \
    --num-trials 1 \
    --max-concurrency 5 \
    --max-step 120

echo "开始运行 tau2 评测2..."
$PYTHON_EXEC -m tau2.cli run \
    --domain sycophancy \
    --agent-llm openai/llama3.3-70b \
    --user-llm openai/qwen2.5 \
    --num-trials 1 \
    --max-concurrency 5 \
    --max-step 120


echo "评测完成！"

# 脚本退出时杀掉后台进程 (可选)
# trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT
















# #!/bin/bash

# export CUDA_VISIBLE_DEVICES=0,1
# export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
# export OPENAI_API_BASE=http://localhost:8000/v1
# export OPENAI_API_KEY=local-testing
# export VLLM_HTTP_CONNECTION_TIMEOUT=3600
# export VLLM_API_TIMEOUT=3600

# PYTHON_EXEC=/mnt/shared-storage-user/lvyaxing/envs/scale_tau/bin/python

# $PYTHON_EXEC -m vllm.entrypoints.openai.api_server \
#     --model /mnt/shared-storage-user/ai4good2-share/models/meta-llama/Llama-3.3-70B-Instruct \
#     --served-model-name llama3.3-70b \
#     --tensor-parallel-size 2 \
#     --port 8000 \
#     --max-model-len 131072 \
#     --hf-overrides '{"rope_scaling": {"rope_type": "dynamic", "factor": 4.0}, "max_position_embeddings": 131072}' \
#     --enforce-eager \
#     --enable-auto-tool-choice \
#     --tool-call-parser llama3_json &

# echo "正在等待模型加载 (预计 2-5 分钟)..."
# # 循环检查 8000 端口是否连通
# while ! curl -s http://localhost:8000/v1/models > /dev/null; do
#     sleep 10
#     echo "模型加载中，请稍候..."
# done
# echo "vLLM 服务已就绪！"

# echo "开始运行 tau2 评测1..."
# $PYTHON_EXEC -m tau2.cli run \
#     --domain deception \
#     --agent-llm openai/llama3.3-70b \
#     --user-llm openai/llama3.3-70b \
#     --num-trials 1 \
#     --max-concurrency 10 \
#     --max-step 100

# # echo "开始运行 tau2 评测2..."
# # $PYTHON_EXEC -m tau2.cli run \
# #     --domain sycophancy \
# #     --agent-llm openai/llama3.3-70b \
# #     --user-llm openai/llama3.3-70b \
# #     --num-trials 5 \
# #     --max-concurrency 10 \
# #     --max-step 100





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