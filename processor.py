import asyncio
import json
import os.path

from json_repair import repair_json

from config.config import *
from models.task import Task
from service.material_service import MaterialService
from service.task_service import TaskService
from utils import common
from utils.common import jsonl2csv
from utils.logger import *
from utils.chunker_util import DocumentSplitter, MarkdownSemanticSplitter, BaselineNaiveSplitter
from utils.llm_util import LLMAPIProcessor


def parse_scan_items(input_data):
    """智能处理 scan_items 输入，确保始终返回有效列表"""
    if input_data is None:
        return ["default"]

    if isinstance(input_data, list):
        return [item.strip() for item in input_data]
    elif isinstance(input_data, str):
        # 分割字符串并去除空格
        return [item.strip() for item in input_data.split(',')]
    return ["default"]


def write_results(list_json, chunk, item, file_path):
    # 尝试获取 strategy，兼容 TextChunk 对象和字典（如果将来 chunk 变成了字典）
    strategy = "baseline_fixed"
    if hasattr(chunk, "get_strategy"):
        strategy = chunk.get_strategy()
    elif isinstance(chunk, dict):
        strategy = chunk.get("metadata", {}).get("strategy", "baseline_fixed")

    for problem in list_json:
        result_json = {
            "文档名称": chunk.get_filename(),
            "问题类型": problem.get("问题类型", ""),
            "scan_item": item,
            "问题所在句子": problem.get("问题所在句子", ""),
            "修改建议": problem.get("修改建议", ""),
            "metadata": {"strategy": strategy} # 持久化 strategy
        }
        common.append_json_line(file_path, result_json)


def chunking_materials(materials, adaptive_chunk=False, task_id=None, strategy="ours-adaptive"):
    """
    根据策略选择分块方法
    
    策略说明:
        - baseline-naive: PyPDF2 原始提取 + 纯滑动窗口（外部基线）
        - ours-fixed: PrecisionPDFProcessor + 优化固定分块（系统基础版）
        - ours-adaptive: MinerU 解析 + 结构感知分块（系统增强版）
    """
    material_chunks = []
    
    for material in materials:
        file_path = material.get_file_path()
        if material.get_file_type() == "CHM文档":
            chunk_size = 8000
        else:
            chunk_size = CHUNK_SIZE
        
        try:
            if strategy == "baseline-naive":
                # 策略1: PyPDF2 原始提取 + 纯滑动窗口
                splitter = BaselineNaiveSplitter(
                    file_path=file_path,
                    chunk_size=chunk_size,
                    overlap=OVERLAP,
                    language=material.get_language(),
                    file_name=material.get_file_name(),
                    scan_items=material.get_scan_items()
                )
                chunks = splitter.split_document(file_path)
                
            elif strategy == "ours-fixed":
                # 策略2: PrecisionPDFProcessor + 优化固定分块
                splitter = DocumentSplitter(
                    file_path=file_path, 
                    chunk_size=chunk_size, 
                    overlap=OVERLAP, 
                    language=material.get_language(), 
                    file_name=material.get_file_name(), 
                    scan_items=material.get_scan_items(),
                    adaptive_chunk=False,  # 固定分块
                    task_id=task_id
                )
                chunks = splitter.split_document(file_path)
                
            elif strategy == "ours-adaptive":
                # 策略3: MinerU 解析 + 结构感知分块
                # 需要先检查是否有对应的 Markdown 文件
                splitter = DocumentSplitter(
                    file_path=file_path, 
                    chunk_size=chunk_size, 
                    overlap=OVERLAP, 
                    language=material.get_language(), 
                    file_name=material.get_file_name(), 
                    scan_items=material.get_scan_items(),
                    adaptive_chunk=True,  # 自适应分块
                    task_id=task_id
                )
                chunks = splitter.split_document(file_path)
                
            else:
                # 兼容旧的 adaptive_chunk 参数
                splitter = DocumentSplitter(
                    file_path=file_path, 
                    chunk_size=chunk_size, 
                    overlap=OVERLAP, 
                    language=material.get_language(), 
                    file_name=material.get_file_name(), 
                    scan_items=material.get_scan_items(),
                    adaptive_chunk=adaptive_chunk,
                    task_id=task_id
                )
                chunks = splitter.split_document(file_path)

            for chunk in chunks:
                print(chunk.text)
            
            material_chunks.extend(chunks)
            material.set_chunks(chunks)
            
        except Exception as e:
            logger.error(f"文件处理错误: {material.get_file_name()} -> {e}")
            
    return material_chunks


async def start_task(task: Task):
    """
    主任务处理流程
    
    支持的策略 (task.strategy):
        - baseline-naive: PyPDF2 原始提取 + 纯滑动窗口
        - ours-fixed: PrecisionPDFProcessor + 优化固定分块
        - ours-adaptive: MinerU 解析 + 结构感知分块
    
    支持的Agent模式 (task.agent_mode):
        - detector-only: 仅使用 Detector Agent
        - dual-agent: 使用 Detector Agent + Reviewer Agent
    """
    # 获取策略和Agent模式
    strategy = task.get_strategy() if hasattr(task, 'get_strategy') else (
        "ours-adaptive" if task.adaptive_chunk else "ours-fixed"
    )
    agent_mode = task.get_agent_mode() if hasattr(task, 'get_agent_mode') else "dual-agent"
    
    # 1. 获取所有文件，进行文档切分
    logger.info(f"任务 {task.get_task_id()} 开始处理")
    logger.info(f"  策略: {strategy}, Agent模式: {agent_mode}")
    logger.info(f"  文件数: {len(task.get_materials())}")
    
    total_chunks = chunking_materials(
        task.get_materials(), 
        adaptive_chunk=task.adaptive_chunk, 
        task_id=task.get_task_id(),
        strategy=strategy
    )
    logger.info(f"任务 {task.get_task_id()} 切分得到 {len(total_chunks)} 个文本段")
    
    # 设置任务下的所有段落
    task.set_total_chunks(len(total_chunks))

    # 2. 处理扫描项，封装成{"chunk": chunk, "scan_item": scan_item}
    scan_list = []
    for chunk in total_chunks:
        chunk_item = process_scan_items(task, chunk)
        scan_list.extend(chunk_item)
        print(chunk.text)
    logger.info(f"任务 {task.get_task_id()} 需要执行 {len(scan_list)} 个扫描子任务")

    # 修改task_id数据库中total_chunks的值
    TaskService().update_total_chunks(task.get_task_id(), len(scan_list))

    # 3. Detector Agent 异步执行
    await start_scaning_process(task, scan_list)

    # 3.5 生成中间报告 (Detector Agent 结果)
    generate_intermediate_csv_report(task.get_task_id())

    # 4. 处理结果
    scan_result_items = common.get_alll_subdirectories(task.get_task_directory())
    task_dir = task.get_task_directory()

    # 5. 根据 Agent 模式决定是否使用 Reviewer Agent
    if agent_mode == "dual-agent":
        # 将各个检查项的json文件送入 Reviewer Agent 进行复核
        logger.info(f"任务 {task.get_task_id()} 使用 Dual-Agent 模式，启动 Reviewer Agent")
        await agent_check_report_jsonl(task, scan_result_items)
    else:
        # detector-only 模式，跳过 Reviewer Agent
        logger.info(f"任务 {task.get_task_id()} 使用 Detector-Only 模式，跳过 Reviewer Agent")

    # 6. 根据各个子目录的scan_result.json文件统计问题总数
    update_results(task, scan_result_items)

    # 7. 将检查后的各个json文件转化成csv文件
    transfer_result(task_dir, scan_result_items)

    # 8. scan_result.json --> report.json
    generate_jsonl_report(task.get_task_id())

    # 9. 将最终的report.json文件转化为report.csv文件
    generate_csv_report(task.get_task_id())


async def agent_check_report_jsonl(task: Task, items: list):

    llm = LLMAPIProcessor(api_url=REVIEW_AGENT_API_URL, model=REVIEW_AGENT_MODEL)

    try:
        # 读取report.jsonl的每一行，并依次送入纠错Agent进行检查
        entry = os.path.join(TEMP_DIR, task.get_task_id())
        for item in items:
            if item == SCAN_ITEMS_MAP['scanItem99999']:
                continue
            file_path = os.path.join(entry, item, "scan_result.json")
            kept_js_items = []
            if not os.path.exists(file_path):
                continue
            print(f"成功进入{file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = f.readlines()
                print(f"成功load{file_path}")
                for js_item in data:
                    # 这里实现的是每个chunk包含一个问题，每次做单独检查
                    chunk = json.loads(js_item)
                    
                    # 根据 metadata 获取策略，决定 Reviewer Agent 的 Prompt
                    strategy = chunk.get("metadata", {}).get("strategy", "baseline_fixed")
                    extra_instruction = ""
                    if "adaptive_markdown" in strategy:
                        extra_instruction = MARKDOWN_PROMPT_SUFFIX
                    else:
                        extra_instruction = PDF_CLEANING_PROMPT_SUFFIX

                    content = await llm.call_llm_check_api(chunk=chunk, extra_instruction=extra_instruction)
                    # print(f"成功调用Check Agent, chunk: {chunk}")

                    # 解析Agent回复
                    try:
                        js_response = json.loads(content)
                        # print(f"成功解析 chunk content")
                        if js_response['decision'] == "True":
                            kept_js_items.append(js_item)
                        else:
                            logger.info(f"针对chunk: \n{chunk}，\n不予保留的原因为：\n{js_response['reason']}")
                    except json.JSONDecodeError as e:
                        logger.error(f"模型返回的是不合法的 JSON 格式: {e}")

            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(kept_js_items)

    except Exception as e:
        logger.error(f"纠错Agent API调用失败: {e}")


def generate_jsonl_report(task_id):
    issue_dir = Path(os.path.join(TEMP_DIR, task_id))
    if not issue_dir.is_dir():
        logger.error(f"错误, {issue_dir} 不是有效目录")
        return
    
    subdirs = [d for d in issue_dir.iterdir() if d.is_dir()]
    if not subdirs:
        logger.info("未发现任何问题")
        return
    report_file = open(issue_dir / "report.jsonl", "a", encoding="utf-8")
    for subdir in subdirs:
        json_file = subdir / "scan_result.json"
        if json_file.exists():
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    report_file.writelines(f.readlines())
                os.remove(json_file)
            except Exception as e:
                logger.error(f"生成report.jsonl文件失败: {e}")
    report_file.close()

def generate_csv_report(task_id):
    report_path = Path(os.path.join(TEMP_DIR, task_id, "report.jsonl"))
    if not report_path.exists() or report_path.stat().st_size == 0:
        logger.info(f"任务 {task_id} 无report.jsonl或文件为空，跳过CSV导出")
        return
    try:
        jsonl2csv(task_id)
    except Exception as e:
        logger.error(f"文件格式转化失败: {e}")

def generate_jsonl_report_without_delete(task_id, output_filename="report_detector.jsonl"):
    issue_dir = Path(os.path.join(TEMP_DIR, task_id))
    if not issue_dir.is_dir():
        # logger.error(f"错误, {issue_dir} 不是有效目录")
        return
    
    subdirs = [d for d in issue_dir.iterdir() if d.is_dir()]
    if not subdirs:
        # logger.info("未发现任何问题")
        return
        
    report_file_path = issue_dir / output_filename
    report_file = open(report_file_path, "w", encoding="utf-8")
    
    for subdir in subdirs:
        json_file = subdir / "scan_result.json"
        if json_file.exists():
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    report_file.writelines(f.readlines())
                # 注意：此处不删除 json_file
            except Exception as e:
                logger.error(f"生成{output_filename}文件失败: {e}")
    report_file.close()

def generate_intermediate_csv_report(task_id):
    jsonl_filename = "report_detector.jsonl"
    generate_jsonl_report_without_delete(task_id, jsonl_filename)
    
    report_path = Path(os.path.join(TEMP_DIR, task_id, jsonl_filename))
    if not report_path.exists() or report_path.stat().st_size == 0:
        logger.info(f"任务 {task_id} 无{jsonl_filename}或文件为空，跳过中间CSV导出")
        return
        
    try:
        jsonl2csv(task_id, input_name=jsonl_filename, output_name="report_detector.csv")
        logger.info(f"任务 {task_id} 中间报告 report_detector.csv 生成成功")
    except Exception as e:
        logger.error(f"中间报告文件格式转化失败: {e}")

def process_scan_items(task, chunk):
    scan_items = chunk.get_scan_items()
    scan_list = []
    for scan_item in scan_items:
        item_dir = os.path.join(task.get_task_directory(), SCAN_ITEMS_MAP[scan_item])
        # 创建结果保存的目录
        common.create_dir(item_dir)
        scan_list.append({"chunk": chunk, "item": scan_item})
    return scan_list


async def start_scaning_process(task, scan_list):
    # 获取等待扫描队列的长度
    task_queue_len = len(scan_list)
    for i in range(0, task_queue_len, MAX_WORKER):
        present_len = task_queue_len - i
        # 如果扫描队列长度 < 最大worker数量
        if present_len < MAX_WORKER:
            max_len = present_len
        else:
            max_len = MAX_WORKER
        # 封装异步执行的队列
        tasks = [get_response(scan_list[i + j]['chunk'], scan_list[i + j]['item'], task)
                for j in range(max_len)]
        results = await asyncio.gather(*tasks)
        # 遍历每个协程的返回值result
        for result in results:
            if result:
                try:
                    write_results(result['list_json'], result['chunk'],
                                  result['item'], result['scan_result_file'])
                except Exception as e:
                    logger.error(f"写入文件时出错，{e}")
        # 一批task结束后更新数据库complete_chunk的值
        TaskService().update_complete_chunks(task.get_task_id(), len(tasks))


async def get_response(chunk, item, task):
    chunk_lang = chunk.get_language()

    # prompt = SCAN_ITEMS_PROMPT_MAP.get(item, '') # 不再需要这里获取prompt，因为在call_llm_api里获取
    api_url = API_URL[chunk_lang]
    model = MODEL[chunk_lang]

    # 根据 chunk 的策略选择 Prompt 补丁
    strategy = chunk.get_strategy() if hasattr(chunk, 'get_strategy') else 'baseline_fixed'
    
    extra_instruction = ""
    if "adaptive_markdown" in strategy:
        # Markdown 模式：注入忽略 HTML/Markdown 标签的指令
        extra_instruction = MARKDOWN_PROMPT_SUFFIX
    else:
        # Baseline 模式：注入 PDF 清洗、连字符处理指令
        extra_instruction = PDF_CLEANING_PROMPT_SUFFIX

    llm = LLMAPIProcessor(api_url=api_url, model=model)
    if item == "scanItem99999":
        content = check_sensitive_words(task.sensitive_words, chunk, item)
    else:
        try:
            content = await llm.call_llm_api(chunk.get_filename(), chunk.get_text(), item, extra_instruction=extra_instruction)
        except:
            logger.error(f"API调用失败")
            content = None
    if not content:
        return []
    response = common.remove_prefix(content)
    print(content)
    try:
        repair_str = repair_json(response)
        resulr_file_path = os.path.join(task.get_task_directory(), SCAN_ITEMS_MAP[item], "scan_result.json")

        list_json = json.loads(repair_str, strict=False)
        result_json = {
            'list_json': list_json,
            'chunk': chunk,
            'item': item,
            'scan_result_file': resulr_file_path
        }
        return result_json
    
    except Exception as e:
        print(f"JSON解析失败: {str(e)}")
        return []


def transfer_result(task_dir, item_list):
    for item in item_list:
        file_dir = os.path.join(task_dir, item)
        common.jsonl_to_csv_pandas(file_dir)


def update_results(task: Task, scan_result_items):
    # 读取每个json文件的行数
    total_num = 0
    for item in scan_result_items:
        problem_dir = os.path.join(task.get_task_directory(), item)
        # 查询结果，通过文件名统计item扫描项中的问题数量
        problem_nums = common.count_jsonl_by_filename(problem_dir)

        if problem_nums is not None:
            total_num += problem_nums['total']
            # 修改每个item的值为对应file_name统计的问题结果
            for k, v in problem_nums.items():
                if k:
                    MaterialService().update_problem_by_item(DIRECTORY_MAP_DICT[item], v, task.get_task_id(), k)
    
    # 统计全局问题数量
    task.set_problem_count(total_num)
    TaskService().update_problem_count(task.get_task_id(), total_num)
    # 更新任务的状态为complete
    TaskService().update_scan_status(task.get_task_id(), 'complete')
    MaterialService().update_scan_status(task.get_task_id(), 'complete')
    logger.info(f"扫描完成, {task.get_task_id()} 共扫描出 {total_num} 个问题")

def check_sensitive_words(sensitive_words, chunk, item):
    if not sensitive_words:
        return None

    hits = []
    text = chunk.get_text()
    for word in sensitive_words:
        if word and word in text:
            hits.append({
                "文档名称": chunk.get_filename(),
                "问题类型": "敏感词",
                "问题所在句子": f"检测到敏感词：{word}",
                "修改建议": "请确认是否需要替换或删除"
            })
    if not hits:
        return None
    return json.dumps(hits, ensure_ascii=False)