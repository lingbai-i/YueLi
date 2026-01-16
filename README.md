<div align="center">
  <h1>月璃 YueLiBot </h1>
  
  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python Version">
    <img src="https://img.shields.io/badge/Focus-VTB%20Live-pink" alt="Focus">
  </p>

  <p>面向直播互动的 AI 智能体，让虚拟主播更“像人”</p>
</div>

<br>

## 📖 项目简介

**月璃 (YueLiBot)** 是一个专注于 **VTB (Virtual YouTuber)** 直播互动的 AI 智能体，目标是让“对话”不仅能回答，还能有情绪、有节奏、有舞台感。

本项目基于 [MaiBot (MaiCore)](https://github.com/Mai-with-u/MaiBot) 二次开发：保留其群聊与插件能力，并针对直播场景强化了动作/表情联动、音频路由与平台接入等能力，适合将 AI 智能体接入到虚拟形象与直播间的实时互动链路中。

我们致力于构建一个“有灵魂”的直播伴侣，而不仅仅是一个自动回复机器。

<br clear="both">

---

## ✨ 核心能力

- 🔌 **插件系统**：支持 Action / Command / Tool 等组件形态，便于扩展互动能力与工作流
- 🧠 **记忆与人物信息**：长期记忆、关系/状态维度的上下文管理，面向持续陪伴与长期互动
- 😊 **情绪系统**：可维持会话级长期情绪状态，并参与生成与动作决策
- 🧩 **表达与资源系统**：表达方式、资源管理等能力，为“风格化输出”提供素材基础

[IMPORTANT]
第三方项目声明
本项目为 MaiBot 的第三方衍生项目，独立维护，非官方版本；功能取舍与实现细节以本仓库为准。

---

## 🎭 直播增强（VTB Focus）

- 🎭 **双流情感-动作决策**：`VTBActionDecisionEngine` 综合文本语义与长期情绪状态，输出更符合“人设”的动作选择
- 🎮 **VTube Studio 控制**：`VTBController` 通过热键映射触发表情/姿势/饰品等动作，实现“说话-表情-动作”联动
- 🎧 **直播级音频路由**：`AudioManager` 面向虚拟声卡等输出设备的路由与播放队列，降低互动延迟
- 📺 **Bilibili 直播接入**：提供独立 Hub 以接入弹幕等事件流，将直播间互动汇入核心对话链路

---

## 📦 仓库组成

- `YueLiBot/`：核心服务（对话、情绪、记忆、插件系统等）
- `YueLiBot-Bilibili-Hub/`：直播间事件接入（弹幕等）

---

## 🙏 致谢

- **[MaiBot (MaiCore)](https://github.com/Mai-with-u/MaiBot)**：提供核心交互框架与大量基础能力

---

## 📄 许可证

GPL-3.0（见 [LICENSE](LICENSE)）

<div align="center">
  <small>Code is open, but the soul is yours.</small>
</div>
