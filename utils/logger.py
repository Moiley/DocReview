import logging 

import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


def setup_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    """
    配置并返回一个日志记录器

    Args:
        name: 日志记录器的名称(一般使用__name__)
        log_dir: 日志文件的保存目录

    Returns:
        logging.Logger: 配置好的日志记录器对象
    """
    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 如果已经配置过处理器，则不再重复配置
    if logger.handlers:
        return logger

    # 日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 2. 文件处理器(按天分割)
    log_file = Path(log_dir) / f'{datetime.now().strftime("%Y-%m-%d")}.log'
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=1024 * 1024 * 10, # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # 3. 错误日志单独记录
    error_file_handler = RotatingFileHandler(
        filename=Path(log_dir) / f'{datetime.now().strftime("%Y-%m-%d")}_error.log',
        maxBytes=1024 * 1024 * 5, # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.WARNING)
    error_file_handler.setFormatter(formatter)

    # 添加处理器到记录器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_file_handler)

    return logger


logger = setup_logger(__name__)