# 🐺 Wolves-Game - AI驱动的狼人杀游戏

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Ollama](https://img.shields.io/badge/Ollama-Required-orange.svg)](https://ollama.ai/)

> 一个基于大语言模型的智能狼人杀游戏，支持多种角色和完整的游戏流程

## 🌟 亮点特性

* 🤖 **AI驱动的智能玩家** - 基于 Ollama LLM 的智能对话和决策
* 🎮 **完整的游戏体验** - 支持狼人、村民、预言家、女巫等经典角色
* 🌙 **昼夜循环系统** - 完整的夜晚和白天阶段游戏流程
* 💬 **智能发言系统** - AI玩家能够进行策略性发言和投票
* 🎯 **角色技能系统** - 预言家查验、女巫药剂、狼人击杀等完整技能
* 🌍 **中文本地化** - 完整的中文界面和游戏提示
* ⚙️ **高度可配置** - 灵活的游戏参数和房间设置
* 🏗️ **模块化架构** - 基于 Convention 框架的清晰代码结构

## ℹ️ 项目概述

Wolves-Game 是一个创新的狼人杀游戏实现，将传统桌游与现代人工智能技术相结合。游戏使用 Ollama 作为大语言模型后端，为每个玩家角色提供智能的决策能力和自然的对话体验。

### 🎯 核心功能

游戏支持经典的狼人杀规则，包括：
- **狼人阵营**：夜晚击杀、白天伪装
- **村民阵营**：发言分析、投票决策
- **预言家**：夜晚查验玩家身份
- **女巫**：使用解药救人或毒药杀人

### 🏗️ 技术架构

- **后端引擎**：Python 3.12+ 游戏引擎
- **AI 框架**：Ollama + llama-index
- **基础设施**：Convention 自研框架
- **配置管理**：JSON 配置文件
- **本地化**：完整的中文支持

## 🚀 快速开始

### 基本使用

```python
# 启动游戏
python run.py
```

游戏将自动创建配置的房间并开始游戏流程。

## ⬇️ 安装说明

### 环境要求

- Python 3.12 或更高版本
- Ollama 服务（本地或远程）
- 支持的操作系统：Windows、macOS、Linux

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/your-username/Wolves-Game.git
   cd Wolves-Game
   ```

2. **安装 Python 依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **安装并启动 Ollama**
   ```bash
   # 下载 Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # 启动 Ollama 服务
   ollama serve
   
   # 下载模型（推荐使用 qwen2.5:7b 或类似模型）
   ollama pull qwen2.5:7b
   ```

4. **配置游戏参数**
   
   编辑 `config.json` 文件，设置 Ollama 服务地址和模型：
   ```json
   {
     "properties": {
       "ollama_url": "http://localhost:11434",
       "model": "qwen2.5:7b",
       "room": {
         "🐺 狼人": 2,
         "👥 村民": 4,
         "🔮 预言家": 1,
         "🧙‍♀️ 女巫": 1
       }
     }
   }
   ```

## 📖 使用指南

### 游戏配置

在 `config.json` 中可以配置以下参数：

- **ollama_url**: Ollama 服务地址
- **model**: 使用的 LLM 模型名称
- **agent_config**: AI 代理配置（温度、超时等）
- **room**: 房间角色配置
- **Translate**: 游戏文本本地化

### 游戏流程

1. **游戏初始化**：系统创建指定数量的玩家角色
2. **夜晚阶段**：
   - 狼人讨论并选择击杀目标
   - 预言家查验玩家身份
   - 女巫使用药剂
3. **白天阶段**：
   - 所有玩家依次发言
   - 投票放逐一名玩家
4. **胜利判定**：检查胜利条件并结束游戏

### 角色技能

- **🐺 狼人**：夜晚击杀、狼人讨论
- **👥 村民**：发言分析、投票决策
- **🔮 预言家**：夜晚查验玩家身份
- **🧙‍♀️ 女巫**：使用解药救人或毒药杀人

## 📁 项目结构

```
Wolves-Game/
├── run.py                 # 主入口文件
├── config.json            # 游戏配置文件
├── LICENSE                # 许可证文件
├── src/                   # 源代码目录
│   ├── engine/           # 游戏引擎
│   │   ├── game_engine.py    # 核心游戏逻辑
│   │   └── player_engine.py  # 玩家系统
│   ├── roles/            # 角色定义
│   └── ui/               # 用户界面
└── Convention/           # 基础设施框架
    ├── Runtime/          # 运行时组件
    ├── setup.py          # 框架安装配置
    └── README.md         # 框架文档
```

### 核心模块说明

- **game_engine.py**: 游戏控制器、昼夜系统、UI系统
- **player_engine.py**: AI玩家代理、工具技能、公共记忆
- **config.json**: 游戏配置、本地化文本、角色提示

## 🛠️ 开发指南

### 环境搭建

1. **克隆项目并安装依赖**
   ```bash
   git clone https://github.com/your-username/Wolves-Game.git
   cd Wolves-Game
   pip install -r requirements.txt
   ```

2. **安装开发依赖**
   ```bash
   pip install -e Convention/
   ```

3. **配置开发环境**
   ```bash
   # 确保 Ollama 服务运行
   ollama serve
   
   # 测试模型可用性
   ollama list
   ```

### 代码结构

项目采用模块化设计，主要组件：

- **GameController**: 游戏主控制器
- **DaySystem/NightSystem**: 昼夜阶段管理
- **PlayerAgent**: AI玩家代理
- **PublicMemory**: 公共记忆系统
- **AgentToolSkills**: 玩家技能工具

### 扩展开发

要添加新功能，可以：

1. 在 `src/engine/` 中添加新的游戏逻辑
2. 在 `player_engine.py` 中添加新的工具技能
3. 在 `config.json` 中添加配置参数
4. 更新本地化文本

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 如何贡献

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 贡献类型

- 🐛 Bug 修复
- ✨ 新功能开发
- 📝 文档改进
- 🌍 本地化翻译
- 🧪 测试用例
- 💡 建议和反馈

### 开发规范

- 遵循 PEP 8 代码风格
- 添加适当的注释和文档
- 确保代码通过测试
- 更新相关文档

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

**版权声明：** Copyright (c) 2025 ninemine

---

**⭐ 如果这个项目对你有帮助，请给我们一个星标！**

**💬 有任何问题或建议？欢迎开启 [Issue](https://github.com/your-username/Wolves-Game/issues) 或 [Discussion](https://github.com/your-username/Wolves-Game/discussions)！** 