import os
import shutil
import tempfile
import zipfile
from typing import Optional

from fastapi import HTTPException
from pathlib import Path

from config.config import TEMP_DIR, SCAN_ITEMS_MAP


def get_each_item_results(complete_time, results):
    file_reports = []
    total_problem = 0
    for result in results:
        file_name, file_type, status, message, item_count = result
        file_reports.append({
            "file_name": file_name,
            "file_type": file_type,
            "message": message,
            "problem_count": item_count,
            "status": status,
            "timestamp": complete_time
        })
        total_problem += item_count
    return file_reports, total_problem


def create_zip(source_dir: Path, output_zip: Path, scan_item: Optional[str] = None):
    """
    创建ZIP压缩包
    
    参数：
        source_dip: 源目录路径
        output_zip: 输出的ZIP文件路径
        scan_item: 可选扫描项名称
    """
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if scan_item:
                # 处理指定扫描项的情况
                if scan_item not in SCAN_ITEMS_MAP:
                    raise ValueError(f"无效的扫描项: {scan_item}")

                item_path = source_dir / SCAN_ITEMS_MAP[scan_item] / "scan_result.csv"
                if not item_path.exists():
                    raise FileNotFoundError(f"无错误的扫描项，故不生成扫描报告")

                if item_path.is_file():
                    # 如果是文件，直接添加
                    zipf.write(item_path, item_path.name)
                else:
                    # 如果是目录，递归添加所有文件
                    for root, dirs, files in os.walk(item_path):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = os.path.relpath(file_path, start=source_dir)
                            zipf.write(file_path, arcname)
            else:
                # 处理未指定扫描项的情况
                # 1. 添加result.csv文件（如果存在）
                result_csv = source_dir / "report.csv"
                if result_csv.exists():
                    zipf.write(result_csv, "文本扫描任务报告.csv")

                # 2. 添加所有子目录
                for item in source_dir.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        for root, dirs, files in os.walk(item):
                            for file in files:
                                file_path = Path(root) / file
                                arcname = os.path.relpath(file_path, start=source_dir)
                                zipf.write(file_path, arcname)
        return output_zip
    except Exception as e:
        if output_zip.exists():
            output_zip.unlink()
        raise e