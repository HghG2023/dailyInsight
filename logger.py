import logging
from datetime import datetime
from pathlib import Path

class PathManager:
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.path = Path(__file__).parent / "logs"
        self.path.mkdir(parents=True, exist_ok=True)

    def today_format(self):
        return datetime.now().strftime("%Y-%m-%d")


PM = PathManager()


def get_logger(name: str = "HGRecorder") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 避免重复添加 Handler
    if logger.hasHandlers():
        return logger

    # 日志文件名为当前日期
    log_file = PM.path / f"{PM.today_format()}.log"

    # 创建文件处理器
    file_handler = logging.FileHandler(log_file, encoding = "utf-8")
    file_handler.setLevel(logging.INFO)

    # 设置日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)

    return logger


logger = get_logger()