import asyncio
import logging
import time
import re
import win32clipboard
import win32con
import win32gui
import win32api
import os
import base64
import tempfile
from datetime import datetime
from wxauto import WeChat
from config import WX_TARGET_CHATS, WX_LISTEN_ALL_IF_EMPTY, WX_EXCLUDED_CHATS

logger = logging.getLogger(__name__)

class WeChatListener:
    def __init__(self, target_chats=None, callback=None):
        """初始化微信监听器
        
        Args:
            target_chats: 要监听的聊天列表
            callback: 收到消息时的回调函数
        """
        self.wx = WeChat()
        self.target_chats = target_chats or []
        self.callback = callback
        self.running = False
        self.listen_chats = set()
        self.last_check_time = time.time()
        
        logger.info(f"微信监听器初始化成功: {self.wx.nickname}")
        logger.info(f"目标聊天: {self.target_chats}")
    
    async def start_listening(self):
        """开始监听微信消息"""
        logger.info("开始监听微信消息...")
        self.running = True
        
        # 设置监听聊天
        await self._setup_listen_chats()
        
        # 开始监听循环
        try:
            while self.running:
                await self._check_new_messages()
                await asyncio.sleep(1)    
        except Exception as e:
            logger.error(f"监听过程中发生错误: {str(e)}")
        finally:
            await self.stop_listening()
    
    async def _setup_listen_chats(self):
        """设置监听的聊天"""
        if self.target_chats:
            for chat in self.target_chats:
                await self._add_listen_chat(chat)
        elif WX_LISTEN_ALL_IF_EMPTY:
            # 获取所有会话列表
            session_list = await asyncio.get_event_loop().run_in_executor(
                None, self.wx.GetSessionList, True
            )
            for chat in session_list:
                if chat not in WX_EXCLUDED_CHATS:
                    await self._add_listen_chat(chat)
    
    async def _add_listen_chat(self, chat_name):
        """添加监听的聊天"""
        try:
            # 使用线程池执行同步的微信操作
            success = await asyncio.get_event_loop().run_in_executor(
                None, self.wx.ChatWith, chat_name
            )
            if success:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.wx.AddListenChat, chat_name
                )
                self.listen_chats.add(chat_name)
                logger.info(f"添加监听聊天: {chat_name}")
                return True
        except Exception as e:
            logger.error(f"添加监听聊天失败 {chat_name}: {str(e)}")
        return False
    
    async def _check_new_messages(self):
        """检查新消息"""
        try:
            # 使用线程池执行同步的微信操作
            all_messages = await asyncio.get_event_loop().run_in_executor(
                None, self.wx.GetListenMessage
            )
            
            if all_messages:
                for chat, messages in all_messages.items():
                    chat_name = chat.who if hasattr(chat, 'who') else str(chat)
                    if messages:
                        for msg in messages:
                            await self._process_message(chat_name, msg)
        except Exception as e:
            logger.error(f"检查新消息失败: {str(e)}")
    
    async def _process_message(self, chat_name, message):
        """处理单条消息"""
        try:
            # 过滤系统消息和自己发送的消息
            if (hasattr(message, 'type') and message.type in ['sys', 'self'] or 
                hasattr(message, 'sender') and message.sender == 'Self' or
                hasattr(message, 'content') and (
                    "以下为新消息" in message.content or
                    "新消息" in message.content
                )):
                return
            
            message_data = {
                "chat": chat_name,
                "sender": getattr(message, 'sender', 'Unknown'),
                "type": getattr(message, 'type', 'text'),
                "content": getattr(message, 'content', ''),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.info(f"收到消息: {chat_name} - {message_data['sender']}: {message_data['content'][:50]}...")
            
            # 调用回调函数
            if self.callback:
                await self.callback(chat_name, message_data)
                
        except Exception as e:
            logger.error(f"处理消息失败: {str(e)}")
    
    async def send_wechat_message(self, chat_name: str, message: str) -> bool:
        """发送消息到微信
        
        Args:
            chat_name: 聊天名称
            message: 要发送的消息内容
            
        Returns:
            bool: 是否发送成功
        """
        try:
            # 使用线程池执行同步的微信操作
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None, self._sync_send_wechat_message, chat_name, message
            )
            
            if success:
                logger.info(f"已发送回复到微信: {chat_name} - {message}")
                return True
            else:
                logger.error(f"发送消息到微信失败: {chat_name}")
                return False
                
        except Exception as e:
            logger.error(f"发送消息到微信失败: {str(e)}")
            return False
    

    def _sync_send_wechat_message(self, chat_name: str, message: str) -> bool:
        """同步发送消息到微信（在后台线程中执行）"""
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"尝试发送消息 [{attempt+1}/{max_retries}]: {chat_name}")
                
                # 尝试使用WeChat的SendMsg方法
                success = self._send_via_wxauto_api(chat_name, message)
                
                if success:
                    logger.info(f"成功通过WeChat API发送消息")
                    return True
                    
            except Exception as e:
                logger.error(f"发送微信消息失败 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        logger.error(f"最终发送失败")
        return False

    def _send_via_wxauto_api(self, chat_name: str, message: str) -> bool:
        """通过WeChat的SendMsg API发送消息"""
        try:
            # 确保微信窗口激活
            self.wx._show()
            time.sleep(1)
            
            logger.info(f"使用WeChat SendMsg API发送到: {chat_name}")
            
            # 使用WeChat的SendMsg方法
            result = self.wx.SendMsg(message, who=chat_name)
            
            # 检查结果，SendMsg方法可能返回None表示成功，或者其他值
            if result is None:
                logger.info("WeChat SendMsg API调用成功")
                time.sleep(1)
                return True
            else:
                logger.warning(f"WeChat SendMsg返回: {result}")
                return False
                
        except Exception as e:
            logger.error(f"WeChat API发送失败: {str(e)}")
            return False
    
    def _switch_to_chat_simple(self, chat_name: str) -> bool:
        """简化的聊天切换方法 - 专注于切换操作本身"""
        try:
            # 确保在聊天页面
            self.wx.SwitchToChat()
            time.sleep(1)
            
            # 使用原始的ChatWith方法
            result = self.wx.ChatWith(chat_name)
            
            if result:
                logger.info(f"ChatWith成功，返回: {result}")
                time.sleep(2)
                return True
            else:
                # 如果ChatWith返回False，尝试使用搜索方法
                logger.info(f"ChatWith返回False，尝试搜索方法")
                return self._switch_via_search(chat_name)
                
        except Exception as e:
            logger.error(f"切换聊天失败: {str(e)}")
            return False
    
    def _switch_via_search(self, chat_name: str) -> bool:
        """通过搜索方式切换聊天"""
        try:
            logger.info(f"使用搜索功能查找聊天: {chat_name}")
            self.wx.UiaAPI.SendKeys('{Ctrl}f', waitTime=1)
            time.sleep(1)
            
            search_box = self.wx.B_Search
            if search_box.Exists(2):
                search_box.Click(simulateMove=False)
                search_box.SendKeys('{Ctrl}a', waitTime=0)
                search_box.SendKeys(chat_name, waitTime=1.5)
                
                # 等待搜索结果
                time.sleep(2)
                
                # 尝试点击搜索结果
                target_control = self.wx.SessionBox.TextControl(Name=f"<em>{chat_name}</em>")
                if target_control.Exists(2):
                    logger.info("找到精确匹配的搜索结果")
                    target_control.Click(simulateMove=False)
                    time.sleep(3)
                    # 关闭搜索框
                    self.wx.UiaAPI.SendKeys('{Esc}', waitTime=1)
                    time.sleep(1)
                    return True
                else:
                    # 尝试点击第一个搜索结果
                    try:
                        search_results = self.wx.SessionBox.GetChildren()[1].GetChildren()[1].GetFirstChildControl()
                        if search_results.Exists(1):
                            first_result = search_results.GetFirstChildControl()
                            if first_result.Exists(1):
                                logger.info("点击第一个搜索结果")
                                first_result.Click(simulateMove=False)
                                time.sleep(3)
                                # 关闭搜索框
                                self.wx.UiaAPI.SendKeys('{Esc}', waitTime=1)
                                time.sleep(1)
                                return True
                    except:
                        pass
            
            # 关闭搜索框（如果还开着）
            self.wx.UiaAPI.SendKeys('{Esc}', waitTime=1)
            time.sleep(1)
            return False
                
        except Exception as e:
            logger.error(f"搜索切换失败: {str(e)}")
            # 关闭搜索框（如果还开着）
            try:
                self.wx.UiaAPI.SendKeys('{Esc}', waitTime=1)
            except:
                pass
            return False
    
    def _send_via_clipboard(self, message: str) -> bool:
        """使用剪贴板方式发送消息"""
        try:
            # 确保输入框获得焦点
            if not self._ensure_input_focus():
                logger.warning("无法确保输入框焦点")
                return False
                
            time.sleep(0.5)
            
            # 设置剪贴板内容
            self._set_clipboard_text(message)
            time.sleep(0.5)
            
            # 清除输入框内容
            self.wx.UiaAPI.SendKeys('^a')  # Ctrl+A 全选
            time.sleep(0.3)
            self.wx.UiaAPI.SendKeys('{DEL}')  # 删除
            time.sleep(0.3)
            
            # 粘贴内容
            self.wx.UiaAPI.SendKeys('^v')  # Ctrl+V 粘贴
            time.sleep(0.5)
            
            # 发送消息
            self.wx.UiaAPI.SendKeys('{Enter}')
            time.sleep(1)
            
            logger.info("剪贴板方式发送完成")
            return True
            
        except Exception as e:
            logger.error(f"剪贴板发送失败: {str(e)}")
            return False
    
    def _ensure_input_focus(self) -> bool:
        """确保输入框获得焦点"""
        try:
            # 方法1: 尝试直接找到并点击输入框
            edit_control = self.wx.ChatBox.EditControl()
            if edit_control.Exists(1):
                rect = edit_control.BoundingRectangle
                if rect.width() > 0 and rect.height() > 0:
                    # 点击输入框中心位置
                    x = (rect.left + rect.right) // 2
                    y = (rect.top + rect.bottom) // 2
                    win32api.SetCursorPos((x, y))
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                    logger.info("已点击输入框确保焦点")
                    return True
            
            # 方法2: 通过Tab键切换焦点到输入框
            logger.info("尝试使用Tab键切换焦点")
            self.wx.UiaAPI.SendKeys('{TAB}')
            time.sleep(0.2)
            self.wx.UiaAPI.SendKeys('{TAB}')
            time.sleep(0.2)
            logger.info("使用Tab键切换焦点到输入框")
            return True
            
        except Exception as e:
            logger.warning(f"确保输入框焦点失败: {str(e)}")
            return False
    
    def _set_clipboard_text(self, text: str):
        """设置剪贴板文本"""
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            logger.debug("剪贴板设置成功")
        except Exception as e:
            logger.error(f"设置剪贴板失败: {str(e)}")
            raise
    
    def _extract_chat_name(self, chat_name: str) -> str:
        """从可能的复杂聊天名称中提取实际的聊天名称"""
        # 如果聊天名称包含 "Chat Window at"，尝试提取实际的聊天名称
        if 'Chat Window at' in chat_name:
            match = re.search(r'for ([^>]+)', chat_name)
            if match:
                return match.group(1).strip()
        
        # 如果聊天名称是 ChatWnd 对象的字符串表示，尝试使用 who 属性
        if hasattr(chat_name, 'who'):
            return chat_name.who
        
        # 否则返回原名称
        return str(chat_name)
    
    async def stop_listening(self):
        """停止监听"""
        self.running = False
        logger.info("停止监听微信消息")