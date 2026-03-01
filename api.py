import asyncio
import json
import tempfile
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, File, UploadFile, Form, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.responses import JSONResponse, FileResponse

import processor
from config.config import *
from models.task import Task
from processor import parse_scan_items
from results_processor import get_each_item_results, create_zip
from service.material_service import MaterialService
from service.task_service import TaskService
from storage.sqlite_storage import storage
from utils.logger import *

app = FastAPI(title="企业文档智能审校系统", version="1.0.0")

# CORS 跨域支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

thread_pool = ThreadPoolExecutor(max_workers=5)


class TextFile(BaseModel):
    file_name: str
    file_content: str  # 文本内容


@app.get('/v1/result')
def get_result(task_id: str = Query(..., description="任务唯一标识符")):
    """获取任务结果"""
    task_id = str(task_id)
    scan_item_str, status, message, all_problem_count, complete_time = TaskService().get_scan_task(task_id)
    scan_items = scan_item_str.strip().split(",")
    data = []
    total_materials = TaskService().get_materials_by_id(task_id)
    if status == "complete":
        for item in scan_items:
            results = MaterialService().query_item_separated(task_id, item)
            complete_files = len(results)
            file_count = len(results)
            try:
                file_reports, total_problem = get_each_item_results(complete_time, results)
                each_data = {
                    "completed_files": complete_files,
                    "file_count": file_count,
                    "file_reports": file_reports,
                    "problem_type": SCAN_ITEMS_MAP[item],
                    "scan_items": item,
                    "total_problem_count": total_problem
                }
                data.append(each_data)
            except Exception as e:
                logger.error(f"处理结果查询出现异常：{e}")
    message = f"任务进行中，正在处理{total_materials}个文件"
    progress = TaskService().get_progress_by_id(task_id)
    page_number, words_number = TaskService().get_status_by_id(task_id)

    return_data = {
        "all_problem_count": all_problem_count,
        "data": data,
        "message": message,
        "progress": progress,
        "status": status,
        "document_summary": {
            "page_number": page_number,
            "words_number": words_number
        }
    }
    return return_data


@app.get('/v1/download/')
def download_result(
        task_id: str = Query(..., description="任务唯一标识符"),
        scan_item: Optional[str] = Query(None, description="扫描项列表（JSON字符串格式）")
):
    task_dir = Path(f"{TEMP_DIR}/{task_id}")
    if not task_dir.exists():
        raise HTTPException(status_code=404, detail=f"任务目录 {task_dir} 不存在")
    if not task_dir.is_dir():
        raise HTTPException(status_code=400, detail=f"{task_dir} 不是有效目录")

    # 创建临时ZIP文件
    temp_dir = Path(tempfile.mkdtemp())
    zip_filename = f"task_{task_id}_{scan_item or 'all'}.zip"
    zip_path = temp_dir / zip_filename

    try:
        create_zip(task_dir, zip_path, scan_item)

        return FileResponse(
            path=zip_path,
            filename=zip_filename,
            media_type='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename="{zip_filename}"'
            }
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打包失败: {str(e)}")
    finally:
        # FileResponse会自动清理临时文件
        pass


@app.get("/v1/issues")
async def get_issue_list(
        task_id: uuid.UUID = Query(..., description="任务唯一标识符"),
        limit: int = Query(500, gt=0, le=1000, description="每页返回的记录数，最大1000"),
        page: int = Query(1, gt=0, description="页码，从1开始")
):
    task_id = str(task_id)
    report_file = Path(os.path.join(TEMP_DIR, task_id, "report.jsonl"))
    if not report_file.exists():
        return {
            "error": "report不存在",
            "total": 0,
            "page": page,
            "limit": limit,
            "items": []
        }
    items = []
    start_line = (page - 1) * limit
    end_line = start_line + limit
    try:
        with open(report_file, "r", encoding="utf-8") as f:
            f.seek(0)
            for line_num, line in enumerate(f):
                if line_num >= end_line:
                    break
                if line_num >= start_line:
                    try:
                        json_str = json.loads(line.strip())
                        if isinstance(json_str["修改建议"], str):
                            sug = json_str["修改建议"]
                        elif isinstance(json_str["修改建议"], dict):
                            sug = json.dumps(json_str["修改建议"], ensure_ascii=False)
                        json_result = {
                            "type": json_str["scan_item"],
                            "location": json_str["文档名称"],
                            "question": json_str["问题所在句子"],
                            "suggestion": sug
                        }
                        items.append(json_result)
                    except json.JSONDecodeError:
                        logger.error(f"无效的JSON格式：{line.strip()}")
    except Exception as e:
        logger.error(f"文件读取失败：{e}")
    return {
        "items": items
    }


@app.post("/v1/tasks")
async def create_task(
        file: List[UploadFile] = File(default=[], description="多个上传文件"),
        scan_items: str = Form(default="", description="扫描项列表（JSON字符串格式）"),
        rule_files: List[UploadFile] = File(default=[], description="敏感词列表"),
        adaptive_chunk: bool = Form(default=True, description="是否启用自适应分块（已弃用，请使用 strategy 参数）"),
        strategy: str = Form(default="ours-adaptive", description="分块策略: baseline-naive | ours-fixed | ours-adaptive"),
        agent_mode: str = Form(default="dual-agent", description="Agent模式: detector-only | dual-agent")
):
    task_id = ""
    if not file or all(f.filename == '' for f in file):
        return JSONResponse(
            content={
                "message": "未选择文件"
            },
            status_code=400
        )
    try:
        scan_items_input = scan_items
        scan_items = parse_scan_items(scan_items_input)  # 确保返回列表
        task_id = str(uuid.uuid4())

        # 兼容旧的 adaptive_chunk 参数
        if not adaptive_chunk and strategy == "ours-adaptive":
            strategy = "ours-fixed"
        
        # 验证参数
        valid_strategies = ["baseline-naive", "ours-fixed", "ours-adaptive"]
        valid_agent_modes = ["detector-only", "dual-agent"]
        
        if strategy.lower() not in valid_strategies:
            return JSONResponse(
                content={"message": f"无效的策略: {strategy}，可选值: {valid_strategies}"},
                status_code=400
            )
        if agent_mode.lower() not in valid_agent_modes:
            return JSONResponse(
                content={"message": f"无效的Agent模式: {agent_mode}，可选值: {valid_agent_modes}"},
                status_code=400
            )
        
        task = Task(
            task_id=task_id, 
            scan_items=scan_items, 
            materials=[], 
            adaptive_chunk=adaptive_chunk,
            strategy=strategy.lower(),
            agent_mode=agent_mode.lower()
        )
        # 处理敏感词文件
        sensitive_words = []
        if not len(rule_files) == 0:
            for rule in rule_files:
                words = await rule.read()
                try:
                    df = pd.read_excel(BytesIO(words), engine="openpyxl")
                    str_series = df.astype(str)
                    sensitive_words.extend(str_series["敏感词"].tolist())
                except Exception as e:
                    logger.error(f"读取敏感词列表失败：{e}")
            sensitive_words = set(sensitive_words)
        # 保存上传的文件
        task.init_task(file, scan_items, sensitive_words)
        for f in file:
            save_path = os.path.join(TEMP_DIR, task_id, f.filename)
            with open(save_path, "wb") as fi:
                fi.write(await f.read())  # 异步读取内容
        TaskService().save_task(task.task_id, task.status, task.problem_count, task.message,
                                task.create_time, task.complete_time, task.scan_items)
    except Exception as e:
        traceback.print_exc()
        if not task_id == "":
            TaskService().update_scan_status(task_id, "error")
        return JSONResponse(
            content={
                "message": f"创建任务失败: {str(e)}"
            },
            status_code=500
        )
    thread_pool.submit(run_main_agent, task)
    # thread_pool.TaskThreadPool().thread_run(run_main_agent, (task, None))
    return JSONResponse(
        content={
            "message": f"任务已创建，包含{len(file)}个文件",
            "status_url": f"/v1/result?task_id={task_id}",
            "task_id": task_id
        }, status_code=200)


def run_main_agent(task):
    logger.info("进入主服务")
    try:
        asyncio.run(processor.start_task(task))
    except Exception as exc:
        logger.exception(f"任务 {task.get_task_id()} 执行失败: {exc}")
        TaskService().update_scan_status(task.get_task_id(), "error")


@app.get("/v1/tasks/list")
def list_all_tasks():
    """获取所有历史任务列表"""
    try:
        tasks = storage.get_all_tasks()
        return {"tasks": tasks}
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        return {"tasks": []}


# 挂载前端静态文件
import os as _os
_frontend_dir = _os.path.join(_os.path.dirname(__file__), "frontend")
if _os.path.isdir(_frontend_dir):
    app.mount("/app", StaticFiles(directory=_frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8082)