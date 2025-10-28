"""
WePush 配置模块
"""

import os
import logging
from typing import List, Optional
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

def _parse_list(value: Optional[str], default: List[str] = None) -> List[str]:
    """解析逗号分隔的字符串为列表"""
    if not value:
        return default or []
    return [item.strip() for item in value.split(',') if item.strip()]

def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    """解析字符串为布尔值"""
    if not value:
        return default
    return value.lower() in ('true', 'yes', '1', 't', 'y')

# 微信监听配置
WX_TARGET_CHATS = _parse_list(os.getenv('WX_TARGET_CHATS'), [])
WX_LISTEN_ALL_IF_EMPTY = _parse_bool(os.getenv('WX_LISTEN_ALL_IF_EMPTY'), False)
WX_EXCLUDED_CHATS = _parse_list(
    os.getenv('WX_EXCLUDED_CHATS'), 
    ["文件传输助手", "微信团队", "微信支付"]
)

# MaiBot WebSocket 配置
MAIBOT_WS_URL = os.getenv('MAIBOT_WS_URL', 'ws://127.0.0.1:8000/ws')
MAIBOT_TOKEN = os.getenv('MAIBOT_TOKEN', '')

# 平台标识
PLATFORM_ID = os.getenv('PLATFORM_ID', 'wxauto')

# 日志配置
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG_DATE_FORMAT = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')

# 配置信息打印
def print_config_info():
    """打印当前加载的配置信息"""
    logger = logging.getLogger(__name__)
    logger.info("\n=== WePush 配置信息 ===")
    logger.info(f"微信监听目标: {WX_TARGET_CHATS}")
    logger.info(f"监听所有聊天: {WX_LISTEN_ALL_IF_EMPTY}")
    logger.info(f"排除的聊天: {WX_EXCLUDED_CHATS}")
    logger.info(f"MaiBot WebSocket URL: {MAIBOT_WS_URL}")
    logger.info(f"MaiBot Token: {'已设置' if MAIBOT_TOKEN else '未设置'}")
    logger.info(f"平台标识: {PLATFORM_ID}")
    logger.info("==========================\n")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print_config_info()