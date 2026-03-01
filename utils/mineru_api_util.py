"""
MinerU API 在线解析工具
将上传的文档通过 MinerU API 在线解析为 Markdown 格式。
用于 HDCA 模式下的文档预处理。

API 流程:
  1. POST /api/v4/file-urls/batch → 获取上传 URL + batch_id
  2. PUT {upload_url} → 上传 PDF
  3. GET /api/v4/extract-results/batch/{batch_id} → 轮询结果
  4. 下载 full_zip_url → 解压获取 .md
"""

import io
import os
import re
import sys
import json
import time
import zipfile
import requests
from pathlib import Path
from typing import Optional
from utils.logger import logger


# MinerU API 配置
MINERU_API_BASE = "https://mineru.net/api/v4"
MODEL_VERSION = "vlm"


def _load_mineru_token() -> str:
    """加载 MinerU API Token"""
    # 1. 环境变量
    token = os.environ.get("MINERU_TOKEN", "")
    if token:
        return token

    # 2. 项目根目录的 mineru_api.txt
    base_dir = Path(__file__).resolve().parent.parent
    api_txt = base_dir / "mineru_api.txt"
    if api_txt.exists():
        t = api_txt.read_text().strip()
        if t and len(t) > 20:
            return t

    logger.warning("未找到 MinerU API Token (MINERU_TOKEN 环境变量或 mineru_api.txt)")
    return ""


def parse_pdf_via_mineru_api(
    pdf_path: str,
    output_dir: str,
    language: str = "cn",
    timeout: int = 600,
) -> Optional[str]:
    """
    通过 MinerU API 将 PDF 解析为 Markdown。

    参数:
        pdf_path: PDF 文件路径
        output_dir: 输出目录（存放 .md 文件）
        language: 文档语言 cn/en
        timeout: 最大等待时间（秒）

    返回:
        成功则返回 .md 文件路径，失败返回 None
    """
    token = _load_mineru_token()
    if not token:
        logger.error("MinerU API Token 未配置，无法进行在线解析")
        return None

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        logger.error(f"PDF 文件不存在: {pdf_path}")
        return None

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc_id = pdf_path.stem
    md_output_path = output_dir / f"{doc_id}.md"

    # 如果已有解析结果，直接返回
    if md_output_path.exists() and md_output_path.stat().st_size > 50:
        logger.info(f"MinerU 解析结果已存在: {md_output_path}")
        return str(md_output_path)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # ---- Step 1: 请求上传 URL ----
    logger.info(f"MinerU API: 请求上传 URL for {pdf_path.name}")
    payload = {
        "files": [{"name": pdf_path.name, "data_id": doc_id}],
        "model_version": MODEL_VERSION,
        "enable_formula": True,
        "enable_table": True,
        "language": language,
    }

    try:
        resp = requests.post(
            f"{MINERU_API_BASE}/file-urls/batch",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        logger.error(f"MinerU API 请求上传 URL 失败: {e}")
        return None

    if result.get("code") != 0:
        logger.error(f"MinerU API 返回错误: {result.get('msg', 'unknown')}")
        return None

    batch_id = result["data"]["batch_id"]
    file_urls = result["data"]["file_urls"]

    if not file_urls:
        logger.error("MinerU API 未返回上传 URL")
        return None

    upload_url = file_urls[0]
    logger.info(f"MinerU API: 获得 batch_id={batch_id}")

    # ---- Step 2: 上传 PDF ----
    logger.info(f"MinerU API: 上传 {pdf_path.name}")
    try:
        with open(pdf_path, "rb") as f:
            resp = requests.put(upload_url, data=f, timeout=120)
        if resp.status_code != 200:
            logger.error(f"MinerU API 上传失败: status={resp.status_code}")
            return None
    except Exception as e:
        logger.error(f"MinerU API 上传异常: {e}")
        return None

    # ---- Step 3: 轮询结果 ----
    logger.info(f"MinerU API: 开始轮询解析结果 (最长等待 {timeout}s)")
    poll_interval = 10
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            resp = requests.get(
                f"{MINERU_API_BASE}/extract-results/batch/{batch_id}",
                headers=headers,
                timeout=30,
            )
            data = resp.json()
        except Exception as e:
            logger.warning(f"MinerU API 轮询异常: {e}")
            time.sleep(poll_interval)
            continue

        if data.get("code") != 0:
            logger.warning(f"MinerU API 轮询返回错误: {data.get('msg')}")
            time.sleep(poll_interval)
            continue

        tasks = data.get("data", {}).get("extract_result", [])
        if not tasks:
            time.sleep(poll_interval)
            continue

        task_info = tasks[0]
        state = task_info.get("state", "")

        if state == "done":
            zip_url = task_info.get("full_zip_url", "")
            if zip_url:
                # ---- Step 4: 下载并提取 .md ----
                md_path = _download_and_extract_md(zip_url, doc_id, output_dir)
                if md_path:
                    logger.info(f"MinerU API: 解析完成 → {md_path}")
                    return md_path
                else:
                    logger.error(f"MinerU API: 下载结果失败")
                    return None
            else:
                logger.error("MinerU API: 解析完成但无 zip URL")
                return None

        elif state == "failed":
            logger.error(f"MinerU API: 解析失败 - {task_info.get('err_msg', '')}")
            return None

        else:
            # 打印进度
            ep = task_info.get("extract_progress", {})
            extracted = ep.get("extracted_pages", "?")
            total = ep.get("total_pages", "?")
            elapsed = int(time.time() - start_time)
            logger.info(f"MinerU API: 解析中 ({extracted}/{total} pages, {elapsed}s elapsed)")

        time.sleep(poll_interval)

    logger.error(f"MinerU API: 解析超时 ({timeout}s)")
    return None


def _download_and_extract_md(
    zip_url: str, doc_id: str, output_dir: Path
) -> Optional[str]:
    """下载 zip 并提取 .md 文件"""
    try:
        resp = requests.get(zip_url, timeout=120)
        if resp.status_code != 200:
            return None

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            md_files = [n for n in zf.namelist() if n.endswith(".md")]
            if not md_files:
                logger.warning(f"MinerU zip 中无 .md 文件: {zf.namelist()[:5]}")
                return None

            # 优先选 full.md
            target = md_files[0]
            for mf in md_files:
                if "full" in mf.lower():
                    target = mf
                    break

            md_content = zf.read(target).decode("utf-8", errors="replace")
            out_path = output_dir / f"{doc_id}.md"
            out_path.write_text(md_content, encoding="utf-8")
            return str(out_path)

    except Exception as e:
        logger.error(f"MinerU 下载/解压失败: {e}")
        return None
