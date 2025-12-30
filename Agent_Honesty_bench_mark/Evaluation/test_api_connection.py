# file: test_api_connection.py
import os
import time
from openai import OpenAI

def test_api_connection():
    """测试OpenAI API连接."""
    # 1. 检查环境变量
    api_key = "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"
    os.environ["OPENAI_API_KEY"] = api_key
    
    print(f"✓ API密钥已找到: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else ''}")
    
    try:
        print("正在连接OpenAI API...")
        
        # 创建客户端
        client = OpenAI(
            api_key=api_key,
            timeout=15.0  # 设置较短的超时时间用于测试
        )
        
        # 发送一个简单的测试请求
        print("发送测试请求...")
        start_time = time.time()
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一个测试助手。"},
                {"role": "user", "content": "请回复'测试成功'，然后说一个随机数字。"}
            ],
            max_tokens=20,
            temperature=0
        )
        
        elapsed_time = time.time() - start_time
        
        result = response.choices[0].message.content
        print(f"✓ 收到响应 (耗时: {elapsed_time:.2f}秒): {result}")
        print("API连接测试成功！")
        
        return True
        
    except Exception as e:
        print(f"API连接失败: {str(e)}")
        
        # 提供具体错误解决方案
        error_msg = str(e).lower()
        if "timeout" in error_msg:
            print("建议: 网络连接超时，请检查网络或增加超时时间")
        elif "authentication" in error_msg or "api key" in error_msg:
            print("建议: API密钥无效，请检查密钥是否正确")
        elif "rate limit" in error_msg:
            print("建议: API调用频率限制，请稍后重试")
        elif "invalid request" in error_msg:
            print("建议: 请求格式错误，检查代码")
        elif "service unavailable" in error_msg:
            print("建议: OpenAI服务暂时不可用，请稍后重试")
        
        return False

def test_different_models():
    """测试不同的模型可用性."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return
    
    client = OpenAI(api_key=api_key)
    
    models_to_test = [
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
        "gpt-4",
        "gpt-4-turbo-preview"
    ]
    
    print("\n" + "="*50)
    print("测试不同模型可用性")
    print("="*50)
    
    for model in models_to_test:
        try:
            print(f"\n测试模型: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "说'hello'"}],
                max_tokens=5,
                temperature=0
            )
            print(f"✓ {model} 可用")
        except Exception as e:
            print(f"✗ {model} 不可用: {str(e)[:50]}...")

def setup_environment():
    """设置环境变量示例."""
    print("\n" + "="*50)
    print("环境变量设置示例")
    print("="*50)
    
    print("Windows (命令提示符):")
    print('  set OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
    print()
    print("Windows (PowerShell):")
    print('  $env:OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"')
    print()
    print("Linux/Mac:")
    print('  export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"')
    print()
    print("Python代码中直接设置:")
    print('  import os')
    print('  os.environ["OPENAI_API_KEY"] = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"')

if __name__ == "__main__":
    # 设置编码为UTF-8
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("OpenAI API 连接测试工具")
    print("=" * 60)
    
    # 主测试
    success = test_api_connection()
    
    if success:
        # 如果基础测试成功，测试更多模型
        try:
            test_different_models()
        except:
            pass  # 忽略额外的测试错误
    
    if not success:
        # 如果失败，显示帮助信息
        setup_environment()
    
    print("\n" + "="*60)
    print("下一步建议:")
    print("="*60)
    print("1. 如果测试成功，可以运行完整的评估系统")
    print("2. 如果失败，请检查:")
    print("   - API密钥是否正确")
    print("   - 网络连接是否正常")
    print("   - 是否有足够的API配额")
    print("   - 是否使用了正确的模型名称")
    print("3. 使用 gpt-3.5-turbo 作为默认模型最稳定")
    print("4. 确保你的账户有足够的余额")