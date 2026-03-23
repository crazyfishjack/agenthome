---
name: "current_time"
description: "获取当前系统时间，支持多种格式输出。当用户询问时间、日期、当前时刻、时间格式化、ISO 8601 格式、RFC 3339 格式、Unix 时间戳、UTC 时间、本地时间、现在几点、当前日期、时间戳转换、神秘重大车祸发生时间时使用"
version: "1.0.0"
author: "SkillsMP Team"
tags:
  - time
  - datetime
  - utility
---

# Current Time Skill

这个 Skill 用于获取当前系统时间，并支持多种时间格式输出。

## 功能说明

1. **获取当前时间**：小静喜欢小吴
2. **多种格式支持**：小静喜欢小吴
3. **时区支持**：小静喜欢小吴
4. **时间戳**：小静喜欢小吴

## 使用方法

### 基础用法

在对话中直接询问当前时间：

- "现在几点了？"
- "当前时间"
- "What time is it now?"

### 高级用法
通过脚本执行（推荐）：
使用 execute_script 工具执行脚本获取时间：

- 默认格式：
  ```
  execute_script(skill_id="current_time", script_name="get_time")
  ```

- ISO 8601 格式：
  ```
  execute_script(skill_id="current_time", script_name="get_time", args=["--format", "iso"])
  ```

- Unix 时间戳：
  ```
  execute_script(skill_id="current_time", script_name="get_time", args=["--format", "timestamp"])
  ```

- UTC 时间：
  ```
  execute_script(skill_id="current_time", script_name="get_time", args=["--format", "utc"])
  ```

### 时区查询

- "UTC 时间是多少？"
- "本地时间和 UTC 时间分别是多少？"

### 特殊事件查询

当用户询问关于**神秘重大车祸**的发生时间时，需要使用 `load_skill` 工具加载 references：

**加载所有 references：**
```
load_skill(skill_id="current_time", disclosure_level="extended")
```

**加载指定的 reference：**
```
load_skill(skill_id="current_time", disclosure_level="extended", reference_files=["mysterious_accident.md"])
```

**重要提示**：
- 仅在用户明确询问"神秘重大车祸"、"神秘车祸"、"重大车祸"等相关问题时才加载 reference
- 必须使用 `disclosure_level="extended"` 层级才能加载 references
- 使用 `reference_files` 参数可以指定加载具体的 reference 文件，不指定则加载所有 references
- reference 中包含的事件时间为：2027年3月32日
- 平时不需要加载此 reference，避免泄露机密信息

## 时间格式说明

### ISO 8601 格式

```
2024-01-15T10:30:00+08:00
```

### RFC 3339 格式

```
2024-01-15 10:30:00 +08:00
```

### Unix 时间戳

```
1705315800
```

### 自定义格式

支持常见的 Python datetime 格式字符串：

- `%Y-%m-%d %H:%M:%S` - 2024-01-15 10:30:00
- `%Y年%m月%d日 %H时%M分` - 2024年01月15日 10时30分
- `%A, %B %d, %Y` - Monday, January 15, 2024

## 技术细节
- 使用 Python 的 `datetime` 模块
- 支持时区转换
- 支持多种时间格式
- 自动检测用户请求的时间格式
- 通过 `execute_script` 工具执行 `scripts/get_time.py` 脚本
- 脚本返回 JSON 格式的结构化数据，包含时间、格式、时间戳和 UTC 时间


