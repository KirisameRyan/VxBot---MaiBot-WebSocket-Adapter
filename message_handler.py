import asyncio
import json
import logging
import hashlib
import time
import re
import base64
from typing import Dict, Optional, Any
from maim_message import (
    BaseMessageInfo, UserInfo, GroupInfo, FormatInfo, MessageBase, Seg,
    Router, RouteConfig, TargetConfig
)
from config import MAIBOT_WS_URL, MAIBOT_TOKEN, PLATFORM_ID

logger = logging.getLogger(__name__)

class MaiBotMessageHandler:
    def __init__(self, wechat_listener=None):
        self.router = None
        self.platform = PLATFORM_ID
        self.is_connected = False
        self.wechat_listener = wechat_listener
        self.message_counter = 0
        
    async def initialize(self):
        """初始化 WebSocket 连接"""
        try:
            route_config = RouteConfig(
                route_config={
                    self.platform: TargetConfig(
                        url=MAIBOT_WS_URL,
                        token=MAIBOT_TOKEN if MAIBOT_TOKEN else None,
                    )
                }
            )
            
            self.router = Router(route_config)
            self.router.register_class_handler(self._handle_maibot_response)
            
            logger.info(f"初始化 MaiBot WebSocket 连接: {MAIBOT_WS_URL}")
            return True
            
        except Exception as e:
            logger.error(f"初始化 MaiBot 连接失败: {str(e)}")
            return False
    
    async def start(self):
        """启动 WebSocket 连接"""
        if not self.router:
            success = await self.initialize()
            if not success:
                return False
        
        try:
            # 在后台运行路由器
            asyncio.create_task(self.router.run())
            await asyncio.sleep(2)
            self.is_connected = True
            logger.info("MaiBot WebSocket 连接已建立")
            return True
        except Exception as e:
            logger.error(f"启动 MaiBot 连接失败: {str(e)}")
            self.is_connected = False
            return False
    
    async def stop(self):
        """停止 WebSocket 连接"""
        if self.router:
            await self.router.stop()
        self.is_connected = False
        logger.info("MaiBot WebSocket 连接已停止")
    
    def _build_message_info(self, chat_name: str, message_data: Dict) -> BaseMessageInfo:
        """构建消息元数据"""
        sender = message_data['sender']
        content = message_data['content']
        
        # 生成更可靠的消息ID
        self.message_counter += 1
        message_id_source = f"{sender}_{chat_name}_{time.time()}_{self.message_counter}"
        message_id = hashlib.md5(message_id_source.encode()).hexdigest()
        
        # 用户信息
        user_id = hashlib.md5(sender.encode()).hexdigest()
        user_info = UserInfo(
            platform=self.platform,
            user_id=user_id,
            user_nickname=sender
        )
        
        # 群组信息（如果是群聊）
        group_info = None
        is_group_chat = chat_name != sender
        if is_group_chat:
            group_id = hashlib.md5(chat_name.encode()).hexdigest()
            group_info = GroupInfo(
                platform=self.platform,
                group_id=group_id,
                group_name=chat_name
            )
            # 在群聊中添加用户群昵称
            user_info.user_cardname = sender
        
        # 格式信息
        format_info = FormatInfo(
            content_format=["text"],
            accept_format=["text", "emoji", "image"]
        )
        
        return BaseMessageInfo(
            platform=self.platform,
            message_id=message_id,
            time=time.time(),
            user_info=user_info,
            group_info=group_info,
            format_info=format_info,
            template_info=None,
            additional_config=None
        )
    
    def _build_message_segment(self, content: str) -> Seg:
        """构建消息内容段"""
        return Seg(
            type="text",
            data=content
        )
    
    async def send_to_maibot(self, chat_name: str, message_data: Dict) -> bool:
        """发送消息到 MaiBot Core"""
        if not self.is_connected or not self.router:
            logger.error("WebSocket 未连接，无法发送消息")
            return False
        
        try:
            # 过滤系统消息和自己发送的消息
            if (message_data.get('type') in ['sys', 'self'] or 
                message_data.get('sender') == 'Self' or
                "以下为新消息" in message_data.get('content', '') or
                "新消息" in message_data.get('content', '')):
                return False
            
            # 构建消息
            message_info = self._build_message_info(chat_name, message_data)
            message_segment = self._build_message_segment(message_data['content'])
            
            message = MessageBase(
                message_info=message_info,
                message_segment=message_segment,
                raw_message=None
            )
            
            # 发送消息
            await self.router.send_message(message)
            logger.info(f"消息已发送到 MaiBot Core: {chat_name} - {message_data['sender']}: {message_data['content'][:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"发送消息到 MaiBot Core 失败: {str(e)}")
            return False
    
    async def _handle_maibot_response(self, message):
        """处理从 MaiBot Core 返回的消息"""
        try:
            # 检查消息类型，可能是字典或 MessageBase 对象
            if isinstance(message, dict):
                logger.info(f"收到 MaiBot Core 回复 (字典格式)")
                # 从字典中提取消息内容
                content = self._extract_content_from_dict(message)
                target_chat = self._get_target_chat_from_dict(message)
                
                # 检查是否有图片
                image_data = self._extract_image_from_dict(message)
                if image_data:
                    logger.info("检测到图片消息")
                    if self.wechat_listener:
                        await self.wechat_listener.send_wechat_image(target_chat, image_data)
                    return
                
                if not content:
                    logger.warning("无法从字典中提取消息内容")
                    return
                
                if not target_chat:
                    logger.warning("无法从字典中确定目标聊天")
                    return
                
            elif hasattr(message, 'message_segment'):
                logger.info(f"收到 MaiBot Core 回复 (MessageBase格式)")
                # 提取消息内容
                content = self._extract_content(message.message_segment)
                target_chat = self._get_target_chat(message.message_info)
                
                # 检查是否有图片
                image_data = self._extract_image_from_segment(message.message_segment)
                if image_data:
                    logger.info("检测到图片消息")
                    if self.wechat_listener:
                        await self.wechat_listener.send_wechat_image(target_chat, image_data)
                    return
                
                if not content:
                    logger.warning("无法提取消息内容")
                    return
                
                if not target_chat:
                    logger.warning("无法确定目标聊天")
                    return
            else:
                logger.error(f"未知的消息格式: {type(message)}")
                return
            
            logger.info(f"准备发送回复到微信: {target_chat} - {content}")
            
            # 通过微信监听器发送消息
            if self.wechat_listener:
                await self.wechat_listener.send_wechat_message(target_chat, content)
            else:
                logger.error("微信监听器未设置，无法发送回复")
            
        except Exception as e:
            logger.error(f"处理 MaiBot 回复失败: {str(e)}")

    def _extract_content_from_dict(self, message_dict: dict) -> str:
        """从字典格式的消息中提取文本内容"""
        try:
            message_segment = message_dict.get('message_segment', {})
            
            if isinstance(message_segment, dict):
                if message_segment.get('type') == "text":
                    return message_segment.get('data', '')
                elif message_segment.get('type') == "seglist":
                    contents = []
                    for seg in message_segment.get('data', []):
                        if isinstance(seg, dict) and seg.get('type') == "text":
                            contents.append(seg.get('data', ''))
                    return "".join(contents)
            
            return ""
        except Exception as e:
            logger.error(f"从字典提取消息内容失败: {str(e)}")
            return ""

    def _extract_image_from_dict(self, message_dict: dict) -> str:
        """从字典格式的消息中提取图片数据"""
        try:
            message_segment = message_dict.get('message_segment', {})
            
            if isinstance(message_segment, dict):
                if message_segment.get('type') == "image":
                    return message_segment.get('data', '')
                elif message_segment.get('type') == "seglist":
                    for seg in message_segment.get('data', []):
                        if isinstance(seg, dict) and seg.get('type') == "image":
                            return seg.get('data', '')
            
            return ""
        except Exception as e:
            logger.error(f"从字典提取图片数据失败: {str(e)}")
            return ""

    def _extract_image_from_segment(self, message_segment) -> str:
        """从消息段中提取图片数据"""
        try:
            if hasattr(message_segment, 'type'):
                if message_segment.type == "image":
                    return message_segment.data
                elif message_segment.type == "seglist":
                    for seg in message_segment.data:
                        if isinstance(seg, Seg) and seg.type == "image":
                            return seg.data
            return ""
        except Exception as e:
            logger.error(f"提取图片数据失败: {str(e)}")
            return ""

    def _get_target_chat_from_dict(self, message_dict: dict) -> str:
        """从字典格式的消息信息中获取目标聊天"""
        try:
            message_info = message_dict.get('message_info', {})
            group_info = message_info.get('group_info', {})
            user_info = message_info.get('user_info', {})
            
            # 优先使用群组信息
            if group_info and group_info.get('group_name'):
                group_name = group_info.get('group_name')
                # 处理特殊的群组名称格式
                if 'Chat Window at' in str(group_name):
                    match = re.search(r'for ([^>]+)', str(group_name))
                    if match:
                        return match.group(1).strip()
                return str(group_name)
            
            # 其次使用用户信息
            elif user_info and user_info.get('user_nickname'):
                return user_info.get('user_nickname')
            elif user_info and user_info.get('user_cardname'):
                return user_info.get('user_cardname')
            else:
                logger.warning(f"无法从消息字典中获取目标聊天: {message_info}")
                return ""
                
        except Exception as e:
            logger.error(f"从字典获取目标聊天失败: {str(e)}")
            return ""

    def _extract_content(self, message_segment: Seg) -> str:
        """从消息段中提取文本内容"""
        try:
            if hasattr(message_segment, 'type'):
                if message_segment.type == "text":
                    return message_segment.data
                elif message_segment.type == "seglist":
                    contents = []
                    for seg in message_segment.data:
                        if isinstance(seg, Seg):
                            content = self._extract_content(seg)
                            if content:
                                contents.append(content)
                    return "".join(contents)
            return ""
        except Exception as e:
            logger.error(f"提取消息内容失败: {str(e)}")
            return ""

    def _get_target_chat(self, message_info: BaseMessageInfo) -> str:
        """根据消息信息获取目标聊天"""
        try:
            # 如果有群组信息，发送到群组
            if (hasattr(message_info, 'group_info') and 
                message_info.group_info and 
                hasattr(message_info.group_info, 'group_name') and 
                message_info.group_info.group_name):
                return message_info.group_info.group_name
            # 否则发送给用户
            elif (hasattr(message_info, 'user_info') and 
                  message_info.user_info and 
                  hasattr(message_info.user_info, 'user_nickname') and 
                  message_info.user_info.user_nickname):
                return message_info.user_info.user_nickname
            else:
                logger.warning("无法从消息信息中获取目标聊天，使用默认聊天")
                return "默认聊天"
        except Exception as e:
            logger.error(f"获取目标聊天失败: {str(e)}")
            return ""