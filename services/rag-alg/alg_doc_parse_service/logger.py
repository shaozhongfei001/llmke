import logging
import os
import sys
import traceback
from contextvars import ContextVar
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# 日志记录需要的请求id
request_id: ContextVar[str | None] = ContextVar('request_id', default=None)


def request_id_filter(record: logging.LogRecord):
    record.request_id = request_id.get()
    return True


# 涉及多线程的时候需要给线程内部的logger调用设置正确的reqeust_id
def set_request_id(_request_id: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            request_id.set(_request_id)
            return func(*args, **kwargs)

        return wrapper

    return decorator


log_path = Path('logs')
os.makedirs(log_path, exist_ok=True)

format_str = (f'[PID: {os.getpid()}] %(levelname)s [REQUEST ID: %(request_id)s] [%(asctime)s] '
              f'[%(name)s:%(filename)s:%(lineno)s:%(funcName)s] %(message)s')
formatter = logging.Formatter(format_str)

# 用于定时保存日志文件的Handler
# TODO rollover时间有问题 不是午夜
log_everything_path = log_path / 'everything'
os.makedirs(log_everything_path, exist_ok=True)
log_everything_handler = TimedRotatingFileHandler(
    filename=log_everything_path / f'everything-{os.getpid()}.log',
    when='MIDNIGHT',
    interval=1,
    encoding='utf-8',
    backupCount=7
)
log_everything_handler.setLevel('DEBUG')
log_everything_handler.setFormatter(formatter)

# 单独保存所有的ERROR级别以上的日志
log_error_path = log_path / 'error'
os.makedirs(log_error_path, exist_ok=True)
log_error_handler = TimedRotatingFileHandler(
    filename=log_error_path / f'error-{os.getpid()}.log',
    when='MIDNIGHT',
    interval=1,
    encoding='utf-8',
    backupCount=7
)
log_error_handler.setLevel('ERROR')
log_error_handler.setFormatter(formatter)

# 控制台的Handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

# 配置logger
logger = logging.getLogger('alg_doc_parse_service')

# 设置日志等级
logger.setLevel('DEBUG')

# 避免重复添加 handler
logger.handlers.clear()

# 添加handler和filter
logger.addHandler(log_everything_handler)
logger.addHandler(log_error_handler)
logger.addHandler(stream_handler)
logger.addFilter(request_id_filter)


# 为所有 logger 调用附加 traceback
old_factory = logging.getLogRecordFactory()


def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)

    exc_type, exc_value, exc_tb = sys.exc_info()
    if exc_type and record.levelno >= logging.ERROR:
        # 保留 raise from 的异常链
        tb = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        record.msg = f"{record.msg}\nTraceback (most recent call last):\n{tb}"

    return record


logging.setLogRecordFactory(record_factory)
