import json
import os
from typing import Any, Dict, Optional

import aiohttp
import requests

from config.config import API_URL, MAX_TOKEN, MODEL, SCAN_ITEMS_MAP, SCAN_ITEMS_PROMPT_MAP, SLICE_SIZE
from utils.errors import APIError
from utils.logger import logger, setup_logger


DEFAULT_API_KEY = os.getenv("LLM_API_KEY", "")


class LLMAPIProcessor:
    def __init__(
        self,
        api_url: str,
        max_token: int = MAX_TOKEN,
        slice_size: int = SLICE_SIZE,
        model: str = "qwen2.5-72b-instruct",
        api_key: Optional[str] = DEFAULT_API_KEY,
        timeout: int = 200,
        extra_headers: Optional[Dict[str, str]] = None,
    ):
        self.logger = setup_logger(self.__class__.__name__)
        self.api_url = api_url
        self.max_token = max_token
        self.slice_size = slice_size
        self.model = model
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        if extra_headers:
            self.headers.update(extra_headers)

    @staticmethod
    def _extract_content(result: Dict[str, Any]) -> Optional[str]:
        try:
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None

    async def call_llm_api(self, file_name, chunk, scanItem, extra_instruction=""):
        print("-----------------------")
        """调用大模型API"""
        system_instruction = SCAN_ITEMS_PROMPT_MAP.get(scanItem, '')

        # 如果 Prompt 中包含特定标记，或者为空，直接返回空数组
        if not system_instruction or "SKIP_EXECUTION" in system_instruction:
            self.logger.info(f"ScanItem {scanItem} hit skip flag. Returning empty result directly.")
            return "[]"  # 直接返回 JSON 格式的空数组字符串
        
        # 构建完整的规则说明
        full_instruction = system_instruction
        if extra_instruction:
            full_instruction += f"\n{extra_instruction}"

        payload = {
            "model": self.model,
            "temperature": 0.1,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "n": 1,
            "stream": False,
            "max_tokens": min(self.max_token, 8192),
            "messages": [
                # for dual-agent
                {
                    "role": "system",
                    "content": "你是一名耐心细致且严格遵循既定规则的企业文档纠错专家，你的职责是**严格依据已有指令和规则对文本内容进行纠错，并尽可能多地发现有效错误并提出修改建议**。"
                },
                # for detector-only
                # {
                #     "role": "system",
                #     "content": "你是一名严格遵循规则的企业文档校对专家。你的核心原则：1.只报告100%确定的客观错误；2.绝对禁止将中文翻译成英文；3.严格遵守每个检查项的职责边界，不越界处理其他类型的问题；4.宁可漏报也不误报。"
                # },

                {
                    "role": "user",
                    "content": f"""
                            你作为严格遵循指令的文本纠错专家，必须完全按照以下规则执行检查任务：                           

                            # 强制指令:
                            1. 必须严格按JSON数组格式输出
                            2. 必须遵守豁免范围条款
                            3. 必须满足处理规则所有条件才执行修改                            

                            # 输入参数：
                            - 文件名：{file_name}
                            - 检查项：{scanItem}
                            
                            # 系统指令：{full_instruction}                            

                            # 豁免范围（禁止对以下相关内容进行修改！）
                            1. 专有名词：['机机账号','人机账号','运维面','管理面','运营面','租户面','工步','账户','账号','PWAF','aPaaS','APIC','SDK','IaaS','SMNALL','单击','点击','局点','后台','前台','宽配套','普罗包','三方件','FlexusL']
                            2. 代码段/命令行/参数格式/URL地址
                            3. 版权信息
                            4. 参数名称
                            5. 英文单词大小写

                            # 输出规范（严格格式）
                            [
                                {{
                                    "文档名称": "",
                                    "问题类型": "",
                                    "问题所在句子": "",
                                    "修改建议": "必须给出可执行的修改方案和原因。"
                                }}
                            ]

                            注意：如无任何修改项，必须返回空数组[]，并禁止返回解释性文字！如果[问题所在句子]和[修改建议]一致，则直接返回空数组[]！
                            需要检查的文本片段如下：""" + "\n" + chunk
                }
            ]
        }

        for attempt in range(3):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                            url=self.api_url,
                            json=payload,
                        headers=self.headers,
                    ) as response:
                        result_text = await response.text()
                        if response.status != 200:
                            raise APIError(f"HTTP {response.status}: {result_text}")
                        data = json.loads(result_text)
                        content = self._extract_content(data)
                        if content is None:
                            raise APIError("模型返回内容为空或结构异常")
                        return content
            except Exception as exc:
                self.logger.error(f"API调用失败：{exc}，正在重试第{attempt + 1}次")
        raise APIError("API调用失败，3次重试")

    async def call_llm_check_api(self, chunk, extra_instruction=""):
        print("-----------------------")

        # json文件单行解析
        scan_item = chunk.get("scan_item")
        sentence = chunk.get("问题所在句子")
        suggestion = chunk.get("修改建议")

        # 原本发现的问题以及对应的处理要求
        problem = SCAN_ITEMS_MAP.get(scan_item)
        tackle_principle = SCAN_ITEMS_PROMPT_MAP.get(scan_item)
        
        # 组装额外指令
        rule_prompt = ""
        if extra_instruction:
            rule_prompt = f"\n{extra_instruction}"

        # 调用大模型API
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "n": 1,
            "stream": False,
            "max_tokens": min(self.max_token, 8192),
            "messages": [
                {
                    "role": "system",
                    "content": f"""
                        # 角色与职责
                        你是一名专业、细致的文本质量审核校验专家，你的核心职责是严格依照提供的规则对生成的文本纠错方案进行最终审核，并确保每一条修改都精准、合规且必要。

                        # 任务背景
                        一名文档纠错人员发现了一个潜在的文本问题，并提出了修改建议。现在需要你来对这个方案进行二次审核，并决定是否最终采纳。       
                    """
                },
                {
                    "role": "user",
                    "content": f"""
                        # 评估材料（常规场景核心输入）
                        你将收到以下四项信息：
                        1.  问题所在句子: 这是包含潜在错误的原始句子。
                            ```
                            {sentence}
                            ```
                        2.  识别出的问题: 系统识别出的具体问题类型。
                            ```
                            {problem}
                            ```
                        3.  系统修改建议: 系统提出的完整修改方案。
                            ```
                            {suggestion}
                            ```
                        4.  对应的修改原则: 针对[识别出的问题]，必须严格遵守的修改准则。
                            ```
                            {tackle_principle}
                            ```
                        
                        {rule_prompt}

                        # 豁免范围（禁止对以下相关内容进行修改！）
                        1. 专有名词：['机机账号','人机账号','运维面','管理面','运营面','租户面','工步','账户','账号','PWAF','aPaaS','APIC','SDK','IaaS','SMNALL','单击','点击','局点','后台','前台','宽配套','普罗包','三方件','FlexusL']
                        2. 代码段/命令行/参数格式/URL地址
                        3. 版权信息
                        4. 参数名称
                        5. 英文单词大小写

                        # 判断标准
                        1. **检查必要性**：[修改建议]是否对于句义的正确性是不可或缺的更改？如果[修改建议]中不建议对问题所在句子进行修改，则直接给出"False"的决定;如果该错误属于**非事实性错误（即修改前后并不影响语句本义）**，则也直接给出"False"的决定。
                        2. **检查一致性**: [修改建议] 是否严格遵循了[修改原则] 的所有要求？是否对**豁免范围**内的内容进行了修改？
                        3. **检查准确性**: [修改建议] 是否针对 [问题类型] 进行了必要的修正？注意：如果确定是错误，那么改变原句语义是被允许的；但禁止对无误内容进行润色！
                        4. **最终决策**: 综合以上三点，给出 "True"(表示保留) 或 "False"(表示不保留) 的决定。

                        # 输出指令（严格遵循格式）
                        请将你的最终审核结论以严格的JSON格式输出。JSON对象应包含`decision`和`reason`两个键。
                        你的最终回复请不要包含"```json"和任何其他额外字符，仅返回JSON。

                        {{
                        "decision": "True" 或 "False",
                        "reason": "清晰、简洁地解释你的判断依据。"
                        }}
                    """
                }
            ]
        }

        for attempt in range(3):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                    url=self.api_url,
                    json=payload,
                        headers=self.headers,
                    ) as response:
                        result_text = await response.text()
                        if response.status != 200:
                            raise APIError(f"HTTP {response.status}: {result_text}")
                        data = json.loads(result_text)
                        content = self._extract_content(data)
                        if content is None:
                            raise APIError("模型返回内容为空或结构异常")
                return content
            except Exception as exc:
                self.logger.error(f"LLM校验调用失败({attempt + 1}/3): {exc}")

        raise APIError("API调用失败，3次重试")
                    