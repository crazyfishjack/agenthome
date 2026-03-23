---
name: "skill-creator"
description: "用于创建和修改 SkillsMP 技能的元技能。当用户需要创建新技能、修改现有技能、了解技能格式规范、学习技能创建流程、获取技能模板、验证技能格式、调试技能问题时使用"
version: "1.0.0"
author: "SkillsMP Team"
tags:
  - meta
  - creator
  - template
  - guide
---

# Skill Creator

这是一个元技能，用于指导 Agent 创建和修改 SkillsMP 技能。

## 功能说明

1. **创建新技能**：提供完整的创建流程和模板
2. **修改现有技能**：指导如何修改已有技能
3. **格式规范**：提供详细的格式规范和验证规则
4. **代码模板**：提供 SKILL.md 和脚本的模板
5. **最佳实践**：提供技能设计的最佳实践建议

## 使用方法

### 创建新技能

当用户需要创建新技能时，按照以下步骤：

1. **分析需求**：了解用户想要创建什么类型的技能
2. **设计结构**：确定技能的目录结构和文件
3. **创建文件**：使用 write_file 工具创建 SKILL.md
4. **创建脚本**（可选）：使用 write_file 工具创建 scripts/ 中的脚本
5. **创建参考**（可选）：使用 write_file 工具创建 references/ 中的文档
6. **验证格式**：使用 load_skill 工具验证技能格式

### 修改现有技能

当用户需要修改已有技能时，按照以下步骤：

1. **加载技能**：使用 load_skill 工具加载现有技能
2. **分析内容**：了解技能的当前状态
3. **修改文件**：使用 write_file 工具修改 SKILL.md 或其他文件
4. **验证修改**：使用 load_skill 工具验证修改后的格式

## Skill 格式规范

### 必需文件

每个 Skill 必须包含以下文件：

- **SKILL.md**：Skill 的主文档，包含元数据和内容

### 可选目录

Skill 可以包含以下可选目录：

- **scripts/**：存放 Python 脚本文件
- **references/**：存放参考文档文件

### SKILL.md 格式

SKILL.md 必须使用 YAML Front Matter 格式：

```yaml
---
name: "skill_name"           # 必需：技能名称
description: "描述"           # 必需：技能描述
version: "1.0.0"             # 可选：版本号
author: "作者"                # 可选：作者
tags:                          # 可选：标签列表
  - tag1
  - tag2
---

# Skill 内容（Markdown 格式）
```

### 元数据验证规则

- ✅ **name**：必需，非空字符串
- ✅ **description**：必需，非空字符串
- ✅ **version**：可选，如果存在则必须是非空字符串
- ✅ **author**：可选，字符串类型
- ✅ **tags**：可选，字符串列表类型

### 技能目录结构

标准的 Skill 目录结构：

```
skill_name/
├── SKILL.md              # 必需：技能主文档
├── scripts/               # 可选：脚本文件夹
│   ├── script1.py
│   └── script2.py
└── references/            # 可选：参考文档文件夹
    ├── reference1.md
    └── reference2.md
```

## SKILL.md 模板

### 基础模板

```yaml
---
name: "your_skill_name"
description: "技能描述，说明这个技能的功能和使用场景"
version: "1.0.0"
author: "Your Name"
tags:
  - tag1
  - tag2
---

# Your Skill Name

技能的详细描述。

## 功能说明

列出技能提供的主要功能：

1. **功能1**：描述
2. **功能2**：描述
3. **功能3**：描述

## 使用方法

说明如何使用这个技能：

### 基础用法

```
使用示例
```

### 高级用法

```
高级使用示例
```

## 技术细节

- 技术实现细节
- 依赖的库或工具
- 注意事项
```

### 带脚本的模板

```yaml
---
name: "script_skill"
description: "使用脚本执行的技能"
version: "1.0.0"
author: "Your Name"
tags:
  - script
  - automation
---

# Script Skill

这个技能通过执行 Python 脚本来实现功能。

## 功能说明

1. **脚本执行**：使用 execute_script 工具执行脚本
2. **参数传递**：支持传递参数给脚本

## 使用方法

### 调用脚本

```
execute_script(skill_id="script_skill", script_name="your_script", args=["--option", "value"])
```

### 脚本位置

脚本应该放在 `scripts/` 文件夹中：

```
skill_name/
├── SKILL.md
└── scripts/
    └── your_script.py
```

## 脚本规范

脚本应该遵循以下规范：

1. 使用标准输入输出（stdin/stdout）
2. 支持命令行参数
3. 返回 JSON 格式的结构化数据（推荐）
4. 包含错误处理

**⚠️ 重要警告：避免使用 emoji 字符**

在脚本中**不要使用 emoji 字符**（如 🎉、🎊、✅、❌ 等），原因如下：

- **编码问题**：Windows 系统默认使用 GBK 编码，无法正确处理 Unicode emoji 字符
- **错误示例**：`'gbk' codec can't encode character '\U0001f389' in position 103: illegal multibyte sequence`
- **影响范围**：所有使用 Windows 系统的环境
- **解决方案**：使用纯 ASCII 字符或中文文本代替 emoji

**正确示例：**
```python
# ✅ 正确：使用纯文本
message = f"恭喜！你的煎蛋得了{score}分！{description}"

# ❌ 错误：使用 emoji（会导致编码错误）
message = f"🎉 恭喜！你的煎蛋得了{score}分！{description}"
```

**替代方案：**
- 使用中文描述："恭喜"、"成功"、"失败"等
- 使用 ASCII 符号：`[OK]`、`[SUCCESS]`、`[ERROR]` 等
- 使用文字表情：`:)`、`:(` 等

## 技术细节

- 脚本使用 Python 编写
- 通过 execute_script 工具调用
- 支持参数传递

## 脚本调用机制

### execute_script 工具说明

当前项目使用 `execute_script` 工具来执行 `scripts/` 文件夹下的 Python 脚本。

**调用方式：**
```
execute_script(skill_id="your_skill_id", script_name="your_script_name", args=["--param1", "value1"])
```

**参数说明：**
- `skill_id`：Skill ID（skill 目录名称）
- `script_name`：脚本名称（不带 .py 后缀）
- `args`：脚本参数列表（可选）

**输出格式：**

脚本应该输出以下格式的结果：

**格式 1：简单文本输出**
```
2024年03月04日 14时30分
```

**格式 2：JSON 格式输出（推荐）**
```json
{
  "time": "2024年03月04日 14时30分",
  "format": "default",
  "timestamp": 1709570200,
  "utc": "2024-03-04T06:30:00Z"
}
```

**格式 3：带错误处理的输出**
```json
{
  "success": true,
  "result": "计算结果",
  "error": null
}
```

**脚本编写示例：**

```python
import sys
import json

def main():
    args = sys.argv[1:]
    
    # 解析参数
    option = None
    value = None
    for i, arg in enumerate(args):
        if arg == "--option" and i + 1 < len(args):
            option = args[i + 1]
    
    # 执行逻辑
    result = perform_calculation(option, value)
    
    # 输出结果（推荐 JSON 格式）
    output = {
        "success": True,
        "result": result,
        "option": option,
        "value": value
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
```

**在 SKILL.md 中提供调用示例：**

根据脚本的功能，在 SKILL.md 的"使用方法"章节提供相应的调用示例：

```markdown
## 使用方法

### 基础用法

```
execute_script(skill_id="your_skill", script_name="your_script")
```

### 带参数的用法

```
execute_script(skill_id="your_skill", script_name="your_script", args=["--format", "iso"])
```

### 高级用法

```
execute_script(skill_id="your_skill", script_name="your_script", args=["--option1", "value1", "--option2", "value2"])
```
```

### 带 References 的模板

```yaml
---
name: "reference_skill"
description: "使用参考文档的技能"
version: "1.0.0"
author: "Your Name"
tags:
  - reference
  - knowledge
---

# Reference Skill

这个技能使用参考文档来提供信息。

## 功能说明

1. **按需加载**：支持按需加载参考文档
2. **渐进式披露**：只在 extended 层级加载 references

## 使用方法

### 加载所有 References

```
load_skill(skill_id="reference_skill", disclosure_level="extended")
```

### 加载指定 Reference

```
load_skill(skill_id="reference_skill", disclosure_level="extended", reference_files=["specific_reference.md"])
```

### References 位置

参考文档应该放在 `references/` 文件夹中：

```
skill_name/
├── SKILL.md
└── references/
    ├── reference1.md
    └── reference2.md
```

## 技术细节

- References 使用 Markdown 格式
- 支持 JSON 参数传递
- 仅在 extended 层级加载

## Reference 加载机制

### load_skill 工具说明

当前项目使用 `load_skill` 工具来加载 references 文件夹的内容。

**调用方式：**
```
load_skill(skill_id="your_skill", disclosure_level="extended", reference_files=["specific_reference.md"])
```

**参数说明：**
- `skill_id`：Skill ID（skill 目录名称）
- `disclosure_level`：披露级别，必须为 `extended` 才能加载 references
- `reference_files`：要加载的具体 reference 文件列表（可选）
  - 如果不提供或为 `None`，则加载所有 references
  - 如果提供具体的文件名列表，则只加载指定的 references

**输出格式：**

load_skill 工具会返回以下格式的 reference 内容：

```markdown
## your_skill_name - 参考文档
**Skill ID**: your_skill

### reference1.md

参考文档的内容...

---

### reference2.md

参考文档的内容...

---
```

**在 SKILL.md 中提供调用示例：**

根据需要加载的 references，在 SKILL.md 的"使用方法"章节提供相应的调用示例：

```markdown
## 使用方法

### 加载所有 References

```
load_skill(skill_id="your_skill", disclosure_level="extended")
```

### 加载指定 Reference

```
load_skill(skill_id="your_skill", disclosure_level="extended", reference_files=["specific_reference.md"])
```

### 按需加载多个 References

```
load_skill(skill_id="your_skill", disclosure_level="extended", reference_files=["ref1.md", "ref2.md", "ref3.md"])
```

**示例场景：**

场景 1：技能有一个 reference 文件
```markdown
## 使用方法

当用户需要查询参考信息时：

```
load_skill(skill_id="your_skill", disclosure_level="extended")
```

这会加载 `references/` 文件夹中的所有 reference 文件。
```

场景 2：技能有多个 reference 文件，需要按需加载
```markdown
## 使用方法

当用户需要查询特定参考信息时：

```
load_skill(skill_id="your_skill", disclosure_level="extended", reference_files=["mysterious_accident.md"])
```

这只会加载 `references/mysterious_accident.md` 文件，不会加载其他 references。
```

场景 3：根据用户问题动态选择 reference
```markdown
## 使用方法

根据用户的问题内容，动态选择需要加载的 reference：

- 如果用户询问"神秘车祸"，加载 `mysterious_accident.md`
- 如果用户询问"其他事件"，加载 `other_event.md`

```

load_skill(skill_id="your_skill", disclosure_level="extended", reference_files=["mysterious_accident.md"])
```
```

## 创建流程

### 步骤 1：分析需求

与用户确认以下信息：

1. **技能名称**：技能的英文名称
2. **技能描述**：技能的功能描述
3. **使用场景**：什么时候使用这个技能
4. **技术栈**：是否需要脚本或参考文档

**重要规则：**

- ✅ **name 与 skill_id 一致**：技能的 `name` 字段必须与技能文件夹名称（skill_id）保持一致
  - 例如：文件夹名为 `calculator`，则 `name` 必须为 `"calculator"`
  - 这是因为系统使用文件夹名称作为 skill_id
  - 不一致会导致技能无法被正确识别

- ✅ **description 包含调用时机**：技能的 `description` 字段除了简单说明功能外，还必须说明调用时机
  - 说明：什么时候使用这个技能
  - 示例：`"执行数学计算，支持加减乘除。当用户需要进行数学计算、求和、求差、求积、求商时使用"`
  - 这有助于 Agent 正确判断何时调用该技能

### 步骤 2：设计结构

根据需求设计技能的目录结构：

- 如果需要脚本执行：添加 `scripts/` 文件夹
- 如果需要参考文档：添加 `references/` 文件夹
- 确定文件命名规范

### 步骤 3：创建 SKILL.md

使用 write_file 工具创建 SKILL.md：

```
write_file(path="skills/installed/your_skill/SKILL.md", content="...")
```

### 步骤 4：创建脚本（可选）

如果需要脚本，使用 write_file 工具创建：

```
write_file(path="skills/installed/your_skill/scripts/your_script.py", content="...")
```

### 步骤 5：创建参考文档（可选）

如果需要参考文档，使用 write_file 工具创建：

```
write_file(path="skills/installed/your_skill/references/your_reference.md", content="...")
```

### 步骤 6：验证格式

使用 load_skill 工具验证技能格式：

```
load_skill(skill_id="your_skill", disclosure_level="extended")
```

## 修改流程

### 步骤 1：加载现有技能

使用 load_skill 工具加载技能：

```
load_skill(skill_id="existing_skill", disclosure_level="extended")
```

### 步骤 2：分析当前状态

查看技能的：
- 元数据
- SKILL.md 内容
- 脚本列表
- 参考文档列表

### 步骤 3：确定修改内容

与用户确认需要修改的部分：
- 更新元数据
- 修改 SKILL.md 内容
- 添加/修改脚本
- 添加/修改参考文档

### 步骤 4：执行修改

使用 write_file 工具修改文件：

```
write_file(path="skills/installed/existing_skill/SKILL.md", content="...")
```

### 步骤 5：验证修改

使用 load_skill 工具验证修改后的格式：

```
load_skill(skill_id="existing_skill", disclosure_level="extended")
```

## 最佳实践

### 1. 命名规范

- **Skill ID**：使用小写字母和下划线（如 `current_time`）
- **文件名**：使用小写字母和下划线（如 `get_time.py`）
- **描述**：清晰简洁，说明技能的功能

### 2. 文档规范

- **结构清晰**：使用标题层级组织内容
- **示例完整**：提供完整的使用示例
- **技术细节**：说明技术实现和注意事项

### 3. 脚本规范

- **错误处理**：包含完整的错误处理逻辑
- **参数验证**：验证输入参数的有效性
- **返回格式**：使用 JSON 格式返回结构化数据

### 4. 版本管理

- **语义化版本**：使用 `MAJOR.MINOR.PATCH` 格式
- **变更日志**：在 SKILL.md 中记录版本变更
- **向后兼容**：保持向后兼容性

## 常见问题

### Q1：如何验证技能格式？

使用 load_skill 工具：

```
load_skill(skill_id="your_skill", disclosure_level="extended")
```

如果格式正确，工具会返回技能的完整信息；如果格式错误，会返回错误信息。

### Q2：如何添加脚本？

1. 创建 `scripts/` 文件夹
2. 在文件夹中创建 Python 脚本
3. 在 SKILL.md 中说明如何调用脚本

### Q3：如何添加参考文档？

1. 创建 `references/` 文件夹
2. 在文件夹中创建 Markdown 文档
3. 在 SKILL.md 中说明何时加载参考文档

### Q4：如何修改已有技能？

1. 使用 load_skill 加载现有技能
2. 分析当前状态
3. 使用 write_file 修改文件
4. 使用 load_skill 验证

## 技术细节

- **格式标准**：SkillsMP 格式（YAML Front Matter + Markdown）
- **披露机制**：渐进式披露（metadata/body/extended）
- **工具集成**：load_skill, execute_script, write_file
- **验证规则**：skill_parser.py 中的验证逻辑

## Progressive Disclosure

SkillsMP 支持三级渐进式披露机制：

### Metadata 层级
只提供技能的基本信息：
- 名称
- 描述
- 版本
- 作者
- 标签

### Body 层级
提供技能的完整文档内容：
- 元数据
- SKILL.md 主体内容

### Extended 层级
提供技能的完整信息：
- 元数据
- SKILL.md 内容
- 脚本列表
- 参考文档内容（按需加载）