# zy_log: 一个为算法项目定制的、专业的、异步的日志系统

[![PyPI Version](https://badge.fury.io/py/zy_log.svg)](https://badge.fury.io/py/zy_log) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个功能强大的 Python 日志包，专为计算密集型和算法项目设计。它通过异步 I/O 确保日志记录不会阻塞您的主计算线程，并使用 `rich` 提供美观的控制台输出和异常堆栈。

## 核心功能

* **异步非阻塞**: 所有日志 I/O (文件/控制台) 都在一个单独的后台线程中处理。
* **Rich 集成**: 自动的控制台颜色、美观的格式化和清晰的异常堆栈追踪。
* **动态配置**: 可通过参数或环境变量 (`LOG_LEVEL`) 轻松覆盖配置。
* **致命错误处理**: 提供 `logger.error_and_raise()` 方法，在记录致命错误后立即抛出异常，实现“快速失败”(Fail-Fast)。

## 安装

```bash
pip install zy_log
```

## 快速使用

您只需要在您算法的**主入口文件** (`main.py`) 中初始化一次，然后在任何子模块中调用 `get_logger` 即可。

### 1. 初始化 (在 `main.py` 中)

这是最关键的一步。

```python
# main.py
import zy_log
import os
import time
from your_project import run_my_core_algo

# --- 日志系统初始化 (仅一次) ---
# 推荐：动态指定日志文件名，并设置环境变量
log_filename = f"run_{time.strftime('%Y%m%d_%H%M%S')}.log"
os.environ['LOG_LEVEL'] = 'INFO' # 生产环境
# os.environ['LOG_LEVEL'] = 'DEBUG' # 调试时

zy_log.setup_logging(log_file_override=log_filename)
# --- 初始化完成 ---

# 获取主模块的 logger
logger = zy_log.get_logger(__name__)

logger.info(f"算法启动，日志将记录到: {log_filename}")

# 运行您的核心算法
try:
    run_my_core_algo()
    logger.info("算法运行成功结束。")
except Exception as e:
    logger.critical(f"算法主流程意外崩溃: {e}", exc_info=True)

```

### 2. 在任意子模块中使用

在您的任何算法子模块中：

```python
# your_project/core_algo.py
import zy_log
import time

# [关键] 直接获取 logger，它已经被 main.py 配置好了
logger = zy_log.get_logger(__name__)

def run_my_core_algo():
    
    # 1. 记录正常流程 (Normal)
    logger.info("开始加载数据模型...")
    
    # 2. 记录警告 (Warning)
    logger.warning("检测到 5% 的缺失值，将使用均值填充。")
    
    # 3. 记录致命错误 (Error)
    try:
        if "关键数据" is None:
            # 这会记录一个红色的 Error 日志，然后抛出 RuntimeError
            logger.error_and_raise("关键数据为 None，算法无法继续！")
            
    except RuntimeError as e:
        logger.error(f"算法因致命错误中断: {e}")
        raise # 必须重新抛出，让上层知道

```

## 贡献

欢迎提交 PR 或 Issue。

## 许可证

本项目使用 [MIT License](LICENSE) 授权。