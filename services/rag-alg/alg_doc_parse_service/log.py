import os
import sys
import logging

from contextvars import ContextVar
from loguru import logger


LOG_LEVEL = logging.getLevelName(os.environ.get("LOG_LEVEL", "DEBUG"))
LOG_DIR = "./logs/parse"
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

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def register_logger():
    os.makedirs(LOG_DIR, exist_ok=True)
    intercept_handler = InterceptHandler()
    logging.root.setLevel(LOG_LEVEL)

    noisy_loggers = {
        "nacos": logging.WARNING,
        "nacos.client": logging.WARNING,
    }

    seen = set()
    for name in [
        *logging.root.manager.loggerDict.keys(),
        "gunicorn",
        "gunicorn.access",
        "gunicorn.error",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
    ]:
        if name not in seen:
            seen.add(name.split(".")[0])
            logging.getLogger(name).handlers = [intercept_handler]

    for name, level in noisy_loggers.items():
        nacos_logger = logging.getLogger(name)
        nacos_logger.setLevel(level)
        nacos_logger.propagate = False

    logger.configure(handlers=[{"sink": sys.stdout, "level": LOG_LEVEL}])

    logger.add(
        os.path.join(LOG_DIR, "info_{time:%Y-%m-%d}.log"),
        level="INFO",
        colorize=False,
        rotation="00:00",
        retention="7 days",
        backtrace=False,
        diagnose=False,
        encoding="utf-8",
        format="{time} {level} {message} | PID:{process} | TID: {thread}",
        catch=False,
        enqueue=True,
    )
    logger.add(
        os.path.join(LOG_DIR, "error_{time:%Y-%m-%d}.log"),
        level="ERROR",
        colorize=False,
        rotation="00:00",
        retention="15 days",
        backtrace=False,
        diagnose=False,
        encoding="utf-8",
        format="{time} {level} {message} | PID:{process} | TID: {thread}",
        catch=False,
        enqueue=True,
    )


register_logger()


