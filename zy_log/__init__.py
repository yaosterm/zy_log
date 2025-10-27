"""
zy_log: A professional, asynchronous logging system customized for algorithm projects.

This package provides an advanced logging configuration interface (setup_logging) and one

Customized Logger (get_logger), this Logger contains a special

The 'error_and_raise' method is used to immediately interrupt the algorithm execution after recording an error.

Core functions

-setup_logging: Initialize the logging system.

-get_logger: Obtain a configured Logger instance.

For complete usage, please refer to the documentation strings of 'setup_logging' and 'get_logger'.

:Author: yao zhou
:Version: 0.1.0
"""

import logging
from .core import setup_logging
from .loggers import AlgorithmicLogger

logging.setLoggerClass(AlgorithmicLogger)

def get_logger(name: str) -> AlgorithmicLogger:
    """
    获取一个 Logger 实例。

    因为我们已经调用了 logging.setLoggerClass()，
    这个函数将自动返回一个 AlgorithmicLogger 实例。
    """
    logger_instance = logging.getLogger(name)
    if not isinstance(logger_instance, AlgorithmicLogger):
        logger_instance.__class__ = AlgorithmicLogger
    return logger_instance

# 控制 'from zy_log import *' 的行为
__all__ = [
    "setup_logging",
    "get_logger",
    "AlgorithmicLogger"
]