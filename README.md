# VxBot - MaiBot WebSocket Adapter

一个基于wxauto的微信到MaiBot WebSocket适配器，实现微信消息与MaiBot Core之间的实时双向通信。

## 📋 项目简介

VxBot是一个桥接工具，通过WebSocket协议将微信消息转发到MaiBot Core，并将MaiBot的回复发送回微信，实现智能对话功能。

### 主要特性

- 🔄 **双向消息转发**：微信消息 ↔ MaiBot Core
- 📱 **微信消息监听**：支持监听指定聊天或群组
- 🤖 **MaiBot集成**：通过WebSocket与MaiBot Core实时通信
- 📸 **多媒体支持**：支持文本和图片消息
- ⚡ **异步处理**：基于asyncio的高性能消息处理
- 🛡️ **安全可靠**：支持Token认证和连接重试机制

## 🏗️ 项目结构

```
VxBot-MaiBot-Adapter/
├── main.py                 # 主程序入口
├── config.py              # 配置模块
├── wx_Listener.py         # 微信监听器
├── message_handler.py     # MaiBot消息处理器
├── wxauto            # 微信自动化库
├── requirements.txt      # 依赖包列表
├── .env                  # 环境变量配置
├── start.bat             # Windows启动脚本
└── README.md            # 项目文档
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Windows 10/11（微信客户端）
- 已安装微信PC版3.9.11.17
- MaiBot Core服务

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd VxBot-MaiBot-Adapter
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   ```bash
   # 复制环境配置文件
   cp .env .env.example
   
   # 编辑配置文件，设置正确的参数
   # 请参考下方配置说明
   ```

4. **运行程序**
   ```bash
   # Windows用户
   start.bat
   
   # 或手动运行
   python main.py
   ```

## ⚙️ 配置说明

### 环境变量配置 (.env)

#### MaiBot WebSocket 配置
```env
# WebSocket服务器地址
MAIBOT_WS_URL=ws://127.0.0.1:8001/ws

# MaiBot访问令牌
MAIBOT_TOKEN=your_maibot_token_here

# 平台标识
PLATFORM_ID=wxauto
```

#### 微信监听配置
```env
# 目标监听聊天列表（多个用逗号分隔）
WX_TARGET_CHATS=group1,group2

# 排除监听聊天列表
WX_EXCLUDED_CHATS=文件传输助手,微信团队,微信支付
```

### 配置项详解

| 配置项 | 说明 | 必需 | 示例 |
|--------|------|------|------|
| `MAIBOT_WS_URL` | MaiBot WebSocket服务地址 | ✅ | `ws://127.0.0.1:8001/ws` |
| `MAIBOT_TOKEN` | MaiBot访问令牌 | ✅ | `your_token_here` |
| `WX_TARGET_CHATS` | 监听的微信聊天名称 | ❌ | `群聊名称,好友名称` |
| `WX_EXCLUDED_CHATS` | 排除的聊天名称 | ❌ | `文件传输助手,微信团队` |

## 📚 使用指南

### 基本使用

1. **启动微信**：确保微信PC版已登录
2. **启动MaiBot**：确保MaiBot Core服务正常运行
3. **启动适配器**：运行 `python main.py`
4. **开始对话**：在指定的微信聊天中发送消息

### 消息流程

```
微信消息 → wxauto监听 → 消息转发 → MaiBot Core处理 → 回复接收 → 微信发送回复
```

### 支持的消息类型

- ✅ 文本消息
- ✅ 图片消息
- ❌ 语音消息（暂不支持）
- ❌ 文件消息（暂不支持）

## 🔧 核心组件

### 1. VxBotMaiBotAdapter (main.py)
主适配器类，协调微信监听器和MaiBot消息处理器。

**主要功能：**
- 初始化所有组件
- 启动WebSocket连接
- 管理消息转发流程
- 处理程序生命周期

### 2. WeChatListener (wx_Listener.py)
微信消息监听器，基于wxauto库实现。

**主要功能：**
- 监听指定微信聊天
- 捕获新消息事件
- 发送消息到微信
- 处理图片和文本消息

### 3. MaiBotMessageHandler (message_handler.py)
MaiBot消息处理器，负责与MaiBot Core的WebSocket通信。

**主要功能：**
- 建立WebSocket连接
- 转发微信消息到MaiBot
- 接收并处理MaiBot回复
- 消息格式转换

### 4. Config (config.py)
配置管理模块，加载和管理所有配置参数。

**主要功能：**
- 环境变量加载
- 配置参数验证
- 默认值设置
- 配置信息打印

## 🛠️ 开发指南

### 添加新的消息类型

1. **扩展消息处理器**
   ```python
   # 在 message_handler.py 中添加新的消息类型处理
   async def _handle_new_message_type(self, message):
       # 处理新消息类型
       pass
   ```

2. **更新微信监听器**
   ```python
   # 在 wx_Listener.py 中添加新消息类型的捕获
   def _capture_new_message_type(self):
       # 捕获新消息类型
       pass
   ```

### 自定义消息过滤

```python
# 在 wx_Listener.py 的 _process_message 方法中添加过滤逻辑
async def _process_message(self, chat_name, message):
    # 自定义过滤条件
    if self._should_filter_message(message):
        return
    
    # 继续处理消息
    await super()._process_message(chat_name, message)
```

## 📊 监控和日志

### 日志级别

- `DEBUG`：详细的调试信息
- `INFO`：一般信息记录
- `WARNING`：警告信息
- `ERROR`：错误信息

### 关键日志事件

- ✅ WebSocket连接建立
- ✅ 微信消息接收
- ✅ 消息转发成功
- ⚠️ 连接断开重试
- ❌ 消息发送失败

### 监控建议

1. **连接状态监控**：定期检查WebSocket连接状态
2. **消息转发监控**：统计消息转发成功率
3. **错误日志监控**：关注异常错误和重试次数

## 🐛 故障排除

### 常见问题
确保微信PC版已登录
确保聊天在独立窗口打开

### 调试模式

启用详细日志输出：
```env
LOG_LEVEL=DEBUG
```


## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 🙏 致谢

感谢以下开源项目：
- [wxauto](https://github.com/cluic/wxauto) - 微信自动化库
- [maim_message](https://github.com/MaiM-with-u/maim_message) - MaiBot消息库
- [WeMai](https://github.com/aki66938/WeMai) - 提供了基础思路

---

**注意：** 请合理使用本工具，遵守微信使用条款和相关法律法规。
