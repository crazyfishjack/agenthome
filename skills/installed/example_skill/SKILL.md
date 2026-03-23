---
name: "example_skill"
description: "这是一个示例 Skill，用于演示 SkillsMP 集成功能和渐进式披露机制。当用户想要了解 SkillsMP 系统如何工作、查看示例技能、测试技能加载机制、学习技能格式规范、演示技能元数据层/详情层/扩展层功能时使用"
version: "1.0.0"
author: "SkillsMP Team"
tags:
  - example
  - demo
  - testing
---

# Example Skill

这是一个示例 Skill，用于演示 SkillsMP 集成功能。

## 功能说明

这个 Skill 提供了以下功能：

1. **元数据层**：只显示基本信息（名称、描述、版本）
2. **详情层**：显示完整的文档内容
3. **扩展层**：显示完整的文件列表

## 使用方法

在 School 配置页面中，将这个 Skill 拖拽到 School 中即可启用。

## 披露级别

SkillsMP 支持三种披露级别：

- **元数据层**：只提供 skill 的基本信息
- **详情层**：提供 skill 的完整文档内容
- **扩展层**：提供 skill 的完整代码和资源

## 技术细节

- 支持标准 SkillsMP 格式的 SKILL.md
- 使用 YAML Front Matter 存储元数据
- 支持渐进式披露机制
