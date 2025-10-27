import logging
import logging.config
import json
import os
import pkgutil
import atexit
from queue import Queue
from logging.handlers import QueueHandler, QueueListener

# 确保我们的自定义类被注册
from . import loggers

# rich 是一个必需的依赖，如果它不存在，我们应该在 setup.py/pyproject.toml 中处理
try:
    from rich.logging import RichHandler
except ImportError:
    print("错误: 'rich' 库未安装。请运行 'pip install rich'", flush=True)
    # 使用一个基础的 StreamHandler 作为后备
    from logging import StreamHandler as RichHandler

# 用于存储 Listener，以便程序退出时安全停止
_listener = None


def setup_logging(
        config_path=None,
        default_level=logging.INFO,
        env_key_level='LOG_LEVEL',
        log_file_override=None
):
    """
        配置异步、动态的日志系统。

        这是一个功能完备的日志初始化函数，它会配置异步的 QueueListener，
        使用 rich 进行控制台美化，并允许通过环境变量和参数进行动态覆盖。

        :param config_path: (可选) 自定义 JSON/YAML 配置文件的路径。
        :type config_path: str or None

        :param default_level: (可选) 如果未找到配置，使用的默认日志级别。
        :type default_level: int

        :param env_key_level: (可选) 用于覆盖日志级别的环境变量名称。
        :type env_key_level: str

        :param log_file_override: (可选) 强制指定日志文件名，覆盖所有配置。
        :type log_file_override: str or None

        :return: 无
        :rtype: None

        :raises IOError: 如果配置文件路径存在但无法读取。

        **用法示例 (Usage Example):**

        .. code-block:: python

            import zy_log
            import os

            # 1. 简单启动 (使用默认配置)
            zy_log.setup_logging()

            # 2. 动态文件名
            log_file = f"run_{time.strftime('%Y%m%d')}.log"
            zy_log.setup_logging(log_file_override=log_file)

            # 3. 通过环境变量设置级别
            os.environ['LOG_LEVEL'] = 'DEBUG'
            zy_log.setup_logging()

        """
    global _listener

    # 确保我们的 Logger 类被使用
    logging.setLoggerClass(loggers.AlgorithmicLogger)

    # 1. 加载基础配置 (从文件或默认)
    config = None
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        try:
            config_bytes = pkgutil.get_data(__name__, "config/default_config.json")
            if config_bytes:
                config = json.loads(config_bytes.decode('utf-8'))
            else:
                raise IOError("无法加载默认日志配置。")
        except Exception as e:
            logging.basicConfig(level=default_level)
            logging.warning(f"加载日志配置失败: {e}。使用 basicConfig。")
            return

    # 2. 动态/环境变量覆盖

    # 2.1. 覆盖日志级别
    env_level = os.getenv(env_key_level)
    final_console_level = env_level or config['handlers_templates']['console_rich']['level']

    # 2.2. 覆盖文件路径
    if log_file_override:
        config['handlers_templates']['file']['filename'] = log_file_override

    # 3. 实例化 Handlers
    try:
        # 3.1. 控制台 Handler (Rich)
        console_handler = RichHandler(
            level=final_console_level,
            rich_tracebacks=config['handlers_templates']['console_rich'].get('rich_tracebacks', True),
            tracebacks_show_locals=config['handlers_templates']['console_rich'].get('tracebacks_show_locals', True)
        )

        # 3.2. 文件 Handler (Rotating)
        file_config = config['handlers_templates']['file']
        file_formatter = logging.Formatter(
            fmt=config['formatters']['standard_file']['format'],
            datefmt=config['formatters']['standard_file']['datefmt']
        )
        file_handler = logging.handlers.RotatingFileHandler(
            filename=file_config['filename'],
            maxBytes=file_config['maxBytes'],
            backupCount=file_config['backupCount'],
            encoding=file_config['encoding']
        )
        file_handler.setLevel(file_config['level'])
        file_handler.setFormatter(file_formatter)

    except Exception as e:
        logging.basicConfig(level=default_level)
        logging.error(f"实例化 Handlers 失败: {e}。使用 basicConfig。")
        return

    # 4. [核心] 设置异步非阻塞 I/O
    # 创建一个无限大小的队列
    log_queue = Queue(-1)

    # 创建 QueueHandler，这是 *唯一* 附加到根 Logger 的 Handler
    # 它会立即将日志消息放入队列，主线程不会阻塞
    queue_handler = QueueHandler(log_queue)

    # 创建 QueueListener，它在 *单独的线程* 中运行
    # 它监听 log_queue，并将消息分发给 *真正* 的 Handlers (console 和 file)
    _listener = QueueListener(log_queue, console_handler, file_handler, respect_handler_level=True)

    # 配置根 Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 根 Logger 级别必须足够低
    root_logger.handlers.clear()  # 清除任何现有的 handlers
    root_logger.addHandler(queue_handler)  # 只添加队列 Handler

    # 5. 启动
    _listener.start()

    # 注册一个退出处理程序，以确保在程序关闭时停止 Listener 线程
    atexit.register(_listener.stop)

    # print("异步日志系统已初始化。") # 调试