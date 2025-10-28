import asyncio
import logging
import signal
import sys
from wx_Listener import WeChatListener
from message_handler import MaiBotMessageHandler
from config import WX_TARGET_CHATS, LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)

logger = logging.getLogger(__name__)

class WePushMaiBotAdapter:
    def __init__(self):
        self.message_handler = None
        self.listener = None
        self.running = False
        
    async def initialize(self):
        """初始化所有组件"""
        try:
            # 初始化微信监听器
            self.listener = WeChatListener(
                target_chats=WX_TARGET_CHATS,
                callback=self._handle_wechat_message
            )
            
            # 初始化 MaiBot 消息处理器，传递微信监听器引用
            self.message_handler = MaiBotMessageHandler(wechat_listener=self.listener)
            await self.message_handler.initialize()
            
            logger.info("所有组件初始化成功")
            
        except Exception as e:
            logger.error(f"初始化组件时发生错误: {str(e)}")
            raise
    
    async def _handle_wechat_message(self, chat_name, message_data):
        """处理微信消息的回调函数"""
        await self.message_handler.send_to_maibot(chat_name, message_data)
    
    async def start(self):
        """启动服务"""
        self.running = True
        
        try:
            # 启动 MaiBot WebSocket 连接
            await self.message_handler.start()
            
            # 启动微信监听器
            await self.listener.start_listening()
            
            logger.info("WePush MaiBot Adapter 已启动")
            
            # 保持运行
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("收到停止信号")
        except Exception as e:
            logger.error(f"服务运行过程中发生错误: {str(e)}")
        finally:
            await self.stop()
    
    async def stop(self):
        """停止服务"""
        self.running = False
        
        if self.message_handler:
            await self.message_handler.stop()
        
        if self.listener:
            await self.listener.stop_listening()
        
        logger.info("WePush MaiBot Adapter 已停止")

async def main():
    """主函数"""
    app = WePushMaiBotAdapter()
    
    # 注册信号处理
    def signal_handler(sig, frame):
        logger.info("收到终止信号，正在关闭...")
        asyncio.create_task(app.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 初始化
        await app.initialize()
        
        # 启动服务
        await app.start()
        
    except Exception as e:
        logger.error(f"程序运行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 50)
    print("WePush - MaiBot WebSocket Adapter")
    print("=" * 50)
    
    asyncio.run(main())