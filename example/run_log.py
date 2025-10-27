import zy_log
import time
import logging
import os
from logging import LoggerAdapter  # 导入 LoggerAdapter

# --- 演示特性 1: 动态配置 ---
# 1.1. 通过环境变量设置级别
os.environ['LOG_LEVEL'] = 'DEBUG'  # 覆盖 JSON 中的 INFO 级别

# 1.2. 通过参数传递动态文件名
log_filename = f"run_{time.strftime('%Y%m%d_%H%M%S')}.log"

# 在算法开始时，设置一次日志系统
# 传入动态文件名
zy_log.setup_logging(log_file_override=log_filename)


# --- 演示特性 3: 上下文注入 ---

class ContextLogger(LoggerAdapter):
    """
    一个 LoggerAdapter，用于自动将上下文（如 task_id）注入日志消息。
    """

    def process(self, msg, kwargs):
        # 从 self.extra 中获取上下文
        task_id = self.extra.get('task_id', 'N/A')
        return f"[Task: {task_id}] {msg}", kwargs


# 获取一个基础 logger
base_logger = zy_log.get_logger(__name__)

# 包装它以用于不同的任务
logger_task_A = ContextLogger(base_logger, {'task_id': 'Task-A'})
logger_task_B = ContextLogger(base_logger, {'task_id': 'Task-B'})


def run_task(logger):
    logger.info("任务启动...")
    logger.debug("这是一个详细的调试消息。")
    time.sleep(0.1)
    logger.warning("发生了一个非关键问题。")


# --- 演示特性 2 (异步) 和 4 (Rich 格式化) ---

if __name__ == "__main__":

    # 演示上下文
    logger_task_A.info("启动任务 A...")
    run_task(logger_task_A)

    logger_task_B.info("启动任务 B...")
    run_task(logger_task_B)

    # 演示 Rich 格式化 和 error_and_raise
    base_logger.info("所有任务完成。准备演示异常处理...")
    try:
        # 我们的自定义方法
        base_logger.error_and_raise("这是一个模拟的致命错误！")

    except RuntimeError as e:
        base_logger.critical(f"成功捕获到致命错误: {e}")
        base_logger.info("程序即将退出，异步日志监听器将自动停止。")

    # 您可以检查生成的 .log 文件，例如 'run_20251022_183000.log'