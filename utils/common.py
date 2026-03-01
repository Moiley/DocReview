import json
import os

import pandas as pd

from config.config import TEMP_DIR
from utils.logger import logger 


def check_lang(file_name):
    if any('\u4e00' <= char <= '\u9fff' for char in file_name):
        return "chinese"
    return "english"


def scan_item_by_lang(language, scan_items):
    remove_items_map = {
        "chinese": {"scanItem1001", "scanItem1002", "scanItem5001", "scanItem5003", "scanItem5004", "scanItem5005", 
                    "scanItem6001", "scanItem6002", "scanItem6003", "scanItem6004", "scanItem12009", "scanItem14003"},
        "english": {"scanItem1001", "scanItem1002", "scanItem5002", "scanItem5003", "scanItem5005", "scanItem6001", 
                    "scanItem6002", "scanItem6004", "scanItem12009", "scanItem12009"}
    }

    if language in remove_items_map:
        new_scan_items = [
            item for item in scan_items 
            if item not in remove_items_map[language]
        ]
    else:
        new_scan_items = scan_items
    return new_scan_items


def remove_prefix(s: str, prefix: str = "<think>\n\n<think>\n\n") -> str:
    """去除字符串前的指定前缀"""
    if s.startswith(prefix):
        return s[len(prefix):]
    return s


def create_dir(path):
    """确保目录存在，不存在则创建"""
    if not os.path.exists(path):
        os.makedirs(path)


def append_json_line(file_path: str, new_data):
    """
    使用JSON Lines格式追加数据(每行一个JSON对象)

    :param file_path: 文件路径
    :param new_data: 要追加的数据(字典)
    """
    with open(file_path, 'a', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False)
        f.write('\n')


def get_alll_subdirectories(path):
    """获取指定目录下的所有子目录"""
    subdirectories = []
    for root, dirs, files in os.walk(path):
        for dirname in dirs:
            subdirectories.append(dirname)
    return subdirectories


def jsonl_to_csv_pandas(file_dir):
    """
    使用pandas将JSONL文件转换为CSV文件

    :param jsonl_file: JSONL文件路径
    :param csv_file: CSV文件路径
    """
    # 读取JSONL文件
    try:
        jsonl_file = os.path.join(file_dir, 'scan_result.json')
        csv_file = os.path.join(file_dir, 'scan_result.csv')
        df = pd.read_json(jsonl_file, lines=True, encoding="utf-8")
        # 写入csv文件
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    except Exception as e:
        logger.error(f"因未发现问题因此不存在问题csv文件: {e}")


def count_jsonl_by_filename(file_path):
    """统计JSONL文件的非空行数"""
    file_name = os.path.join(file_path, 'scan_result.json')
    try:
        df = pd.read_json(file_name, lines=True, encoding="utf-8")
        counts = df['文档名称'].value_counts().to_dict()
        counts['total'] = len(df)
        return counts
    except Exception as e:
        logger.error(f"因未发现问题因此不存在问题csv文件: {e}")
        return None


def jsonl2csv(task_id, chunk_size=None, input_name='report.jsonl', output_name='report.csv'):
    file_path = os.path.join(TEMP_DIR, task_id)
    jsonl_file = os.path.join(file_path, input_name)
    df = pd.read_json(jsonl_file, lines=True, encoding="utf-8")

    output_path = os.path.join(file_path, output_name)
    if chunk_size:
        first_chunk = True
        for chunk in df:
            chunk.to_csv(output_path, mode='a', header=first_chunk, index=False, encoding='utf-8')
            first_chunk = False
            logger.info(f"分块转换已完成，结果写入: {output_path}")
    else:
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"成功转换：{len(df)} 行数据已写入: {output_path}")