import logging
import logging.config
import json
import os
import pkgutil
import atexit
from queue import Queue
from logging.handlers import QueueHandler, QueueListener
import pathlib

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
_listener: QueueListener = None


def setup_logging(
        config_path=None,
        default_level=logging.INFO,  # (保留API, 但现在由 JSON 控制)
        env_key_level='LOG_LEVEL',
        log_file_override=None,
        **kwargs  # 用于捕获 log_filename
):
    global _listener

    # --- [ v0.1.2 关键修复：最后一次调用获胜 ] ---
    # 如果一个 Listener 已经在运行 (来自“意外”的早期调用)，
    if _listener is not None:
        _listener.stop()
        _listener = None
        # (dictConfig 会自动清理旧的 handler)

    # --- [ 锁逻辑结束 ] ---

    logging.setLoggerClass(loggers.AlgorithmicLogger)

    # --- [ v0.1.2 智能容错 ] ---
    if 'log_filename' in kwargs and log_file_override is None:
        log_file_override = kwargs.get('log_filename')
        print(f"WARNING [zy_log]: ... 自动修正为 'log_file_override'。", flush=True)

    if (config_path is not None and ... and log_file_override is None):
        # ... (此处省略了您之前版本的完整容错代码) ...
        print(f"WARNING [zy_log]: ... 自动修正为 log_file_override。", flush=True)
        log_file_override = config_path
        config_path = None
    # --- [ 容错结束 ] ---

    # 1. 加载基础配置
    try:
        config_bytes = pkgutil.get_data(__name__, "config/default_config.json")
        config = json.loads(config_bytes.decode('utf-8'))
    except Exception as e:
        logging.basicConfig()
        logging.warning(f"加载默认配置失败: {e}。使用 basicConfig。")
        return

    # 2. 动态覆盖
    env_level = os.getenv(env_key_level)
    final_root_level = env_level or config['loggers']['']['level']  # e.g., INFO
    config['loggers']['']['level'] = final_root_level.upper()

    if log_file_override:
        config['handlers_templates']['file']['filename'] = log_file_override

    # 2.3. 自动创建日志目录
    final_log_file_path = config['handlers_templates']['file']['filename']
    try:
        log_path = pathlib.Path(final_log_file_path)
        log_dir = log_path.parent
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"CRITICAL [zy_log]: 无法创建日志目录 {log_dir}。错误: {e}", flush=True)

    # 3. [关键] 重构配置字典，为异步做准备
    final_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': config['formatters'],
        'handlers': {},  # 最终的 Handlers
        'loggers': config['loggers']
    }

    # (1) 创建 File Handler 的 *配置*
    file_cfg = config['handlers_templates']['file']
    file_handler_config = {
        'class': file_cfg['class'],
        'level': file_cfg['level'],  # (例如 DEBUG)
        'formatter': file_cfg['formatter'],
        'filename': file_cfg['filename'],
        'maxBytes': file_cfg['maxBytes'],
        'backupCount': file_cfg['backupCount'],
        'encoding': file_cfg['encoding'],
    }

    # (2) 创建 Console Handler 的 *配置*
    console_cfg = config['handlers_templates']['console_rich']
    console_handler_config = {
        'class': console_cfg['class'],
        'level': final_root_level,  # (例如 INFO)
        'rich_tracebacks': console_cfg['rich_tracebacks'],
        'tracebacks_show_locals': console_cfg['tracebacks_show_locals'],
    }

    # 4. [核心] 恢复异步 I/O (QueueListener)

    log_queue = Queue(-1)

    # (1) [新] 配置根 Logger *只* 使用 QueueHandler
    final_config['loggers']['']['handlers'] = ['queue']
    final_config['handlers']['queue'] = {
        'class': 'logging.handlers.QueueHandler',
        'queue': log_queue,
    }

    # (2) [新] 使用 dictConfig 应用“前端”设置
    try:
        logging.config.dictConfig(final_config)
    except ValueError as e:
        logging.basicConfig()
        logging.error(f"dictConfig 失败: {e}。是否缺少 'rich' 库？")
        return

    # (3) [新] 手动创建后台线程 (QueueListener)
    # 它将日志分发给 *真正* 的 Handlers

    # (实例化 File Handler)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=file_handler_config['filename'],
        maxBytes=file_handler_config['maxBytes'],
        backupCount=file_handler_config['backupCount'],
        encoding=file_handler_config['encoding']
    )
    file_handler.setFormatter(logging.Formatter(
        fmt=config['formatters']['standard_file']['format'],
        datefmt=config['formatters']['standard_file']['datefmt']
    ))
    file_handler.setLevel(file_handler_config['level'])  # (例如 DEBUG)

    # (实例化 Console Handler)
    console_handler = RichHandler(
        level=console_handler_config['level'],  # (例如 INFO)
        rich_tracebacks=console_handler_config['rich_tracebacks'],
        tracebacks_show_locals=console_handler_config['tracebacks_show_locals']
    )

    # (创建 Listener)
    _listener = QueueListener(log_queue, file_handler, console_handler, respect_handler_level=True)

    # 5. 启动
    _listener.start()
    atexit.register(_listener.stop)

    # --- [ v0.1.2 新功能：智能滚屏分隔符 ] ---
    try:
        init_logger = logging.getLogger("zy_log.init")
        pid = os.getpid()

        # 1. [new] 检查是否需要“滚屏” (即，是否在续写)
        if os.path.exists(final_log_file_path) and os.path.getsize(final_log_file_path) > 0:
            # 只有在续写时，才打印滚屏
            # 传递一个 *有内容* 的滚屏消息，以避免空日志
            init_logger.info("\n" * 48 + "\n" + ("-" * 20) + " (新运行开始于此) " + ("-" * 20))

        # 2. [new] 总是打印横幅 (必须是 *多条* 日志)
        init_logger.info("=" * 70)
        init_logger.info(f"  zy_log: 日志系统已为新运行启动 (PID: {pid})")
        init_logger.info(f"  Config: {final_log_file_path} | Level: {final_root_level}")
        init_logger.info("=" * 70)

    except Exception:
        pass































