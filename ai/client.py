# ai/client.py
from typing import Dict, List, Any, Optional
import asyncio
import httpx
import json
from loguru import logger

from core.config import settings


class OpenAIClient:
    """大型语言模型API客户端，支持通用接口"""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        """初始化客户端"""
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_API_URL
        self.model = model or settings.OPENAI_MODEL
        self.max_retries = 3
        self.timeout = 60

    async def generate(self, prompt: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """调用模型生成文本"""
        if parameters is None:
            parameters = {}

        default_params = {
            "model": self.model,
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 1.0
        }

        params = {**default_params, **parameters}

        # 构建请求
        request_body = {
            "model": params["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": params["temperature"],
            "max_tokens": params["max_tokens"],
            "top_p": params["top_p"]
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.debug(f"Calling OpenAI API with model: {self.model}")

        # 重试逻辑
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=request_body,
                        headers=headers
                    )

                    if response.status_code == 200:
                        result = response.json()
                        response_text = result["choices"][0]["message"]["content"]
                        return response_text
                    else:
                        # 处理错误
                        error_msg = f"API error: {response.status_code} - {response.text}"
                        logger.error(error_msg)

                        if attempt == self.max_retries - 1:
                            raise Exception(error_msg)
                        # 如果不是最后一次尝试，等待后重试
                        await asyncio.sleep(2 ** attempt)  # 指数退避
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                logger.error(f"API request failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"API request failed: {str(e)}")
                await asyncio.sleep(2 ** attempt)

        raise Exception("All API call attempts failed")

    async def batch_generate(self, prompts: List[str],
                             parameters: Optional[Dict[str, Any]] = None) -> List[str]:
        """批量调用模型生成文本"""
        results = []
        for prompt in prompts:
            # 简单的串行处理，可以优化为并行
            result = await self.generate(prompt, parameters)
            results.append(result)
        return results

    async def extract_json(self, prompt: str,
                           parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """调用模型并尝试提取JSON响应"""
        # 增强提示，强调需要JSON格式
        json_prompt = f"{prompt}\n\n请只返回有效的JSON格式数据，不要有任何其他文本。"

        if parameters is None:
            parameters = {"temperature": 0.2}  # 降低温度以获得更确定的输出
        else:
            parameters = {**parameters, "temperature": min(parameters.get("temperature", 1.0), 0.2)}

        response_text = await self.generate(json_prompt, parameters)

        # 尝试解析JSON
        try:
            # 查找响应中的JSON部分
            json_pattern = response_text

            # 提取可能的JSON块（由 ``` 包围）
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_pattern = json_match.group(1)

            # 尝试解析
            result = json.loads(json_pattern)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}\n响应文本: {response_text}")

            # 第二次尝试，明确要求修复JSON格式
            fix_prompt = f"""
            您之前提供的响应不是有效的JSON格式。原始响应:

            {response_text}

            请修复并仅返回有效的JSON格式，不要有任何其他文本或解释。
            """

            try:
                fixed_response = await self.generate(fix_prompt, {"temperature": 0.1})

                # 尝试再次提取JSON块
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', fixed_response)
                if json_match:
                    fixed_response = json_match.group(1)

                return json.loads(fixed_response)
            except Exception:
                # 如果仍然失败，返回空字典
                logger.error("JSON修复失败，返回空结果")
                return {}