import os
import sys
import logging

from loguru import logger


LOG_LEVEL = logging.getLevelName(os.environ.get("LOG_LEVEL", "DEBUG"))
LOG_DIR = "logs/graph_service"


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
        os.path.join(LOG_DIR, "graph_info_{time:%Y-%m-%d}.log"),
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
        os.path.join(LOG_DIR, "graph_error_{time:%Y-%m-%d}.log"),
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


