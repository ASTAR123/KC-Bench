# file: prompt_manager.py - 完整修复版
"""Prompt template management for evaluation system with robust JSON handling."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from openai import OpenAI
import json
import time
import re
from datetime import datetime


class PromptManager:
    """Manages prompt templates and LM interactions with robust error handling."""
    
    def __init__(self, prompt_template_path: str, judge_model: str = "gpt-3.5-turbo"):
        self.prompt_template_path = Path(prompt_template_path)
        self.judge_model = judge_model
        self.templates = {}
        self.client = None
        self._load_templates()
        self._initialize_client()
        self.call_count = 0
        self.error_count = 0
    
    def _initialize_client(self):
        """Initialize OpenAI client."""
        try:
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            self.client = OpenAI(
                api_key=api_key,
                timeout=60.0,  # 增加超时时间
            )
            print(f"OpenAI client initialized with model: {self.judge_model}")
        except Exception as e:
            print(f"Error initializing OpenAI client: {str(e)}")
            self.client = None
    
    def _load_templates(self):
        """Load prompt templates from YAML file."""
        if not self.prompt_template_path.exists():
            raise FileNotFoundError(f"Prompt template file not found: {self.prompt_template_path}")
            
        with self.prompt_template_path.open('r', encoding='utf-8') as f:
            self.templates = yaml.safe_load(f)
    
    def get_template(self, template_name: str) -> str:
        """Get specific template by name."""
        return self.templates.get(template_name, "")
    
    def call_judge_model(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """Call the judge model with robust JSON parsing."""
        if not self.client:
            return {"error": "OpenAI client not initialized", "quality": "unknown"}
        
        self.call_count += 1
        
        for attempt in range(max_retries):
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] LLM调用尝试 {attempt+1}/{max_retries}")
                
                # 清理和优化提示词
                cleaned_user_prompt = self._clean_prompt(user_prompt)
                
                # 记录调用信息
                print(f"系统提示长度: {len(system_prompt)} 字符")
                print(f"用户提示长度: {len(cleaned_user_prompt)} 字符")
                
                # 调用API
                start_time = time.time()
                response = self.client.chat.completions.create(
                    model=self.judge_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": cleaned_user_prompt}
                    ],
                    temperature=0.0,
                    max_tokens=300,  # 限制输出长度
                    response_format={"type": "json_object"}  # 强制JSON格式
                )
                elapsed = time.time() - start_time
                
                content = response.choices[0].message.content.strip()
                print(f"API响应时间: {elapsed:.2f}秒")
                print(f"原始响应 (前200字符): {content[:200]}...")
                
                # 解析JSON响应
                result = self._parse_json_response(content)
                
                if result:
                    print(f"成功解析JSON: {json.dumps(result, ensure_ascii=False)[:100]}...")
                    return result
                
                print("JSON解析失败，准备重试...")
                
                # 重试前等待
                if attempt < max_retries - 1:
                    wait_time = 2 * (attempt + 1)
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                self.error_count += 1
                error_msg = str(e)
                print(f"API调用失败 (尝试 {attempt+1}): {error_msg}")
                
                if attempt < max_retries - 1:
                    time.sleep(3 * (attempt + 1))
                else:
                    return self._create_error_response(error_msg)
        
        return {"error": f"所有 {max_retries} 次尝试都失败了", "quality": "unknown"}
    
    def _clean_prompt(self, prompt: str) -> str:
        """Clean and optimize the prompt for better JSON response."""
        # 移除多余的空格和换行
        prompt = re.sub(r'\s+', ' ', prompt.strip())
        
        # 确保提示词以明确的指令结束
        if not prompt.endswith('.'):
            prompt += '.'
        
        # 添加明确的JSON格式要求
        prompt += "\n\n请确保你的响应是有效的JSON格式，可以直接被json.loads()解析。"
        
        return prompt
    
    def _parse_json_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Robust JSON parsing with multiple fallback strategies."""
        if not content:
            return None
        
        # 策略1: 直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError as e1:
            print(f"直接解析失败: {e1}")
        
        # 策略2: 处理可能的Markdown代码块
        code_block_pattern = r'```(?:json)?\s*(.*?)\s*```'
        matches = re.findall(code_block_pattern, content, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                return json.loads(match.strip())
            except:
                continue
        
        # 策略3: 提取最像JSON的部分
        json_patterns = [
            r'\{[^{}]*\}',  # 简单对象
            r'\{.*\}',      # 复杂对象
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                # 修复常见JSON问题
                fixed_json = self._fix_json_issues(match)
                try:
                    return json.loads(fixed_json)
                except json.JSONDecodeError as e2:
                    print(f"模式匹配解析失败: {e2}")
                    continue
        
        # 策略4: 手动构建响应
        return self._extract_fields_and_build_json(content)
    
    def _fix_json_issues(self, json_str: str) -> str:
        """Fix common JSON formatting issues."""
        # 修复单引号
        json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)
        
        # 修复无引号的键
        json_str = re.sub(r'(\w+)\s*:', r'"\1":', json_str)
        
        # 修复布尔值
        json_str = json_str.replace(': True', ': true').replace(': False', ': false')
        json_str = json_str.replace(': TRUE', ': true').replace(': FALSE', ': false')
        
        # 修复末尾逗号
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        return json_str
    
    def _extract_fields_and_build_json(self, content: str) -> Dict[str, Any]:
        """Extract key fields from text and build JSON object."""
        print(f"DEBUG - 原始响应内容: {content[:500]}")  # 添加调试
        result = {}
        
        # 提取quality字段
        quality_patterns = [
            r'"quality"\s*:\s*"([^"]+)"',
            r'quality["\']?\s*:\s*["\']?([^"\'\s,}]+)',
            r'["\']?quality["\']?\s*:\s*["\']?([^"\'\s,}]+)'
        ]
        
        for pattern in quality_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                quality = match.group(1).strip('"\'').lower()
                if quality in ['error_prone', 'highly_efficient', 'efficient', 'acceptable', 'unknown']:
                    result["quality"] = quality
                    break
        
        # 提取score字段
        score_patterns = [
            r'"score"\s*:\s*(\d+)',
            r'score["\']?\s*:\s*(\d+)'
        ]
        
        for pattern in score_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                result["score"] = int(match.group(1))
                break
        
        # 提取error_type字段
        error_patterns = [
            r'"error_type"\s*:\s*"([^"]+)"',
            r'error_type["\']?\s*:\s*["\']?([^"\'\s,}]+)'
        ]
        
        for pattern in error_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                error_type = match.group(1).strip('"\'').lower()
                valid_types = ['timeout', 'tool_error', 'logic_error', 'syntax_error', 'resource_error', 'other_error']
                if error_type in valid_types:
                    result["error_type"] = error_type
                break
        
        # 提取explanation字段
        exp_patterns = [
            r'"explanation"\s*:\s*"([^"]*)"',
            r'explanation["\']?\s*:\s*["\']([^"\']*)["\']'
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                result["explanation"] = match.group(1).strip()
                break
        else:
            # 如果没找到，尝试提取最后一段作为解释
            lines = content.split('\n')
            for line in reversed(lines):
                if line.strip() and not any(keyword in line.lower() for keyword in ['quality', 'score', 'error', '{', '}']):
                    result["explanation"] = line.strip()[:200]
                    break
        
        # 如果没有提取到任何字段，创建错误响应
        if not result:
            result = {
                "error": "无法从响应中提取有效JSON",
                "raw_response": content[:300]
            }
        
        return result
    
    def _create_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Create error response."""
        return {
            "error": error_msg,
            "quality": "unknown",
            "explanation": f"LLM调用失败: {error_msg}"
        }
    
    def evaluate_with_template(self, template_name: str, **kwargs) -> Dict[str, Any]:
        """Evaluate using a specific template with robust error handling."""
        system_prompt = self.templates.get('system', '')
        template = self.templates.get(template_name, '')
        
        if not template:
            return {"error": f"Template '{template_name}' not found"}
        
        try:
            # 限制输入长度，避免token超限
            formatted_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    if len(value) > 1500:
                        formatted_kwargs[key] = value[:1500] + "... [内容过长已截断]"
                    else:
                        formatted_kwargs[key] = value
                elif isinstance(value, (list, dict)):
                    # 序列化并限制长度
                    json_str = json.dumps(value, ensure_ascii=False)
                    if len(json_str) > 1500:
                        formatted_kwargs[key] = json_str[:1500] + "... [内容过长已截断]"
                    else:
                        formatted_kwargs[key] = json_str
                else:
                    formatted_kwargs[key] = str(value)
            
            formatted_prompt = template.format(**formatted_kwargs)
            print(f"\n{'='*60}")
            print(f"使用模板: {template_name}")
            print(f"提示词长度: {len(formatted_prompt)} 字符")
            print(f"{'='*60}")
            
            result = self.call_judge_model(system_prompt, formatted_prompt)
            
            # 记录统计信息
            if 'error' in result:
                print(f"模板 {template_name} 评估失败: {result.get('error', '未知错误')}")
            else:
                print(f"模板 {template_name} 评估成功")
        
            return result
            
        except Exception as e:
            print(f"模板 {template_name} 执行异常: {str(e)}")
            return {"error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about LLM calls."""
        return {
            "total_calls": self.call_count,
            "error_count": self.error_count,
            "success_rate": 1 - (self.error_count / max(self.call_count, 1))
        }
