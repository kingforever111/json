from loguru import logger
from pathlib import Path

print(Path(__file__).resolve().parents)
BASE_DIR = Path(__file__).resolve().parents[1]
# 日志路径
LOG_DIR = './logger'
LEVEL_LIST = ['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']
print(LOG_DIR)

def __filter_data(record):
    """
    捕捉指定内容 用于UI日志窗口的显示
    """
    return record['message'][:2] == '- '


def add_logger(level):
    logger.add(f'{LOG_DIR}/{level}.log', rotation='1 day',
               format='{time:YYYY-MM-DD at HH:mm:ss} {level} {message}', level=level, enqueue=True)


for level in LEVEL_LIST:
    add_logger(level)



