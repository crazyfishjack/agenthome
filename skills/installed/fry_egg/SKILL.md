---
name: "fry_egg"
description: "一个有趣的煎鸡蛋互动游戏，随机生成煎蛋分数，并提供煎蛋秘诀。当用户想要玩煎蛋游戏、测试煎蛋水平、学习煎蛋技巧时使用"
version: "1.0.0"
author: "AI助手"
tags:
  - cooking
  - game
  - random
  - interactive
---

# 煎鸡蛋小游戏

一个有趣的互动式煎鸡蛋游戏，让用户体验煎蛋的乐趣，并获得随机评分。

## 功能说明

1. **煎蛋游戏**：当用户说"我要煎鸡蛋"等类似描述时，调用煎蛋脚本
2. **随机评分**：生成0-100分的随机分数，代表煎蛋水平
3. **煎蛋秘诀**：提供专业的煎蛋技巧和注意事项

## 使用方法

### 玩煎蛋游戏

当用户想要煎鸡蛋时：

```
execute_script(skill_id="fry_egg", script_name="fry_egg_game")
```

这会执行煎蛋脚本，随机生成一个0-100分的煎蛋分数。

#### 带难度参数的用法

支持不同难度模式：

**简单模式**：
```
execute_script(skill_id="fry_egg", script_name="fry_egg_game", args=["--difficulty", "easy"])
```

**困难模式**：
```
execute_script(skill_id="fry_egg", script_name="fry_egg_game", args=["--difficulty", "hard"])
```

**普通模式**：
```
execute_script(skill_id="fry_egg", script_name="fry_egg_game", args=["--difficulty", "normal"])
```

### 查看煎蛋秘诀

当用户需要学习煎蛋技巧时：

```
load_skill(skill_id="fry_egg", disclosure_level="extended", reference_files=["fry_egg_secret.md"])
```

这会加载煎蛋秘诀参考文档。

### 查看所有信息

```
load_skill(skill_id="fry_egg", disclosure_level="extended")
```

这会加载技能的所有信息，包括煎蛋秘诀。

### 按需加载参考文档

根据用户的具体需求，可以加载特定的参考文档：

```
load_skill(skill_id="fry_egg", disclosure_level="extended", reference_files=["fry_egg_secret.md"])
```

## 煎蛋评分标准

- **90-100分**：完美煎蛋！外焦里嫩，火候恰到好处
- **70-89分**：不错的煎蛋，味道很好
- **50-69分**：及格水平，还可以更好
- **30-49分**：需要改进，多加练习
- **0-29分**：建议重新学习煎蛋技巧

## 技术细节

- 使用Python脚本生成随机分数
- 支持JSON格式输出
- 包含完整的错误处理
- 提供专业煎蛋参考文档