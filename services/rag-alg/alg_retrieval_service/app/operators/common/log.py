import os
import sys
import logging

from loguru import logger


LOG_LEVEL = logging.getLevelName(os.environ.get("LOG_LEVEL", "DEBUG"))
LOG_DIR = "./logs"
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # find caller from where originated the logged message
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def register_logger():
    """注册日志到loguru，由loguru统一管理日志的格式、旋转、错误等"""
    # [定义日志路径]
    os.makedirs(LOG_DIR, exist_ok=True)
    intercept_handler = InterceptHandler()
    # logging.basicConfig(handlers=[intercept_handler], level=LOG_LEVEL)
    # logging.root.handlers = [intercept_handler]
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


    # 日志旋转、大小限制、更替等参数均支持多种配置,详情请参考文档
    # [logger参数文档: https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger]
    # 请务必设置colorize=False,避免在不同系统上由于颜色标签的写入造成问题
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
        enqueue=True
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
        enqueue=True
    )


register_logger()
