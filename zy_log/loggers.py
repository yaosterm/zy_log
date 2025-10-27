import logging


class AlgorithmicLogger(logging.Logger):
    """
    自定义 Logger 类，增加了用于算法的特定方法。
    """
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

    def error_and_raise(self, msg, *args, **kwargs):
        """
        记录一个 ERROR 级别的日志，然后立即抛出一个 RuntimeError。
        这用于算法中不可恢复的致命错误。
        """
        # 1. 记录日志 (现在将由 rich 美观地打印 Traceback)
        # 注意：为了让 rich 正确捕获异常上下文，我们最好在这里传递 exc_info
        kwargs.setdefault('exc_info', True)
        self.error(msg, *args, **kwargs)

        # 2. 抛出异常
        raise RuntimeError(msg)


# 告诉 logging 模块，当调用 getLogger 时，使用我们的自定义类
logging.setLoggerClass(AlgorithmicLogger)