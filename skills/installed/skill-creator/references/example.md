# Skill-Creator 示例

这是一个使用 skill-creator 创建新技能的示例。

## 示例场景

### 场景 1：创建一个计算器技能

**用户需求**：创建一个能够执行数学计算的技能

**创建步骤**：

1. **分析需求**
   - 技能名称：calculator
   - 技能描述：执行数学计算，支持加减乘除
   - 使用场景：用户需要进行数学计算时

2. **设计结构**
   ```
   calculator/
   ├── SKILL.md
   └── scripts/
       └── calculate.py
   ```

3. **创建 SKILL.md**
   ```yaml
   ---
   name: "calculator"
   description: "执行数学计算，支持加减乘除。当用户需要进行数学计算、求和、求差、求积、求商时使用"
   version: "1.0.0"
   author: "SkillsMP Team"
   tags:
     - math
     - calculator
     - utility
   ---
   
   # Calculator Skill
   
   这个技能用于执行数学计算。
   
   ## 功能说明
   
   1. **基本运算**：支持加、减、乘、除
   2. **表达式计算**：支持复杂的数学表达式
   
   ## 使用方法
   
   ### 基础用法
   
   ```
   execute_script(skill_id="calculator", script_name="calculate", args=["--expression", "2+2"])
   ```
   
   ### 高级用法
   
   ```
   execute_script(skill_id="calculator", script_name="calculate", args=["--expression", "sin(0.5)"])
   ```
   
   ## 技术细节
   
   - 使用 Python 的 eval 函数
   - 支持基本的数学运算
   - 包含错误处理
   ```

4. **创建脚本**
   ```python
   import sys
   import json
   
   def main():
       args = sys.argv[1:]
       expression = ""
       
       for i, arg in enumerate(args):
           if arg == "--expression" and i + 1 < len(args):
               expression = args[i + 1]
       
       try:
           result = eval(expression)
           print(json.dumps({
               "expression": expression,
               "result": result,
               "success": True
           }))
       except Exception as e:
           print(json.dumps({
               "expression": expression,
               "error": str(e),
               "success": False
           }))
   
   if __name__ == "__main__":
       main()
   ```

### 场景 2：修改 current_time 技能

**用户需求**：为 current_time 技能添加新的时间格式

**修改步骤**：

1. **加载现有技能**
   ```
   load_skill(skill_id="current_time", disclosure_level="extended")
   ```

2. **分析当前状态**
   - 查看现有的 SKILL.md 内容
   - 了解支持的格式（iso, rfc, timestamp, utc）
   - 确定需要添加的新格式

3. **修改 SKILL.md**
   - 在"时间格式说明"部分添加新格式
   - 更新使用方法示例

4. **验证修改**
   ```
   load_skill(skill_id="current_time", disclosure_level="extended")
   ```

## 最佳实践

### 1. 命名规范

- **Skill ID**：使用小写字母和下划线（如 `calculator`）
- **脚本文件名**：使用小写字母和下划线（如 `calculate.py`）
- **描述**：清晰简洁，说明技能的功能

### 2. 文档规范

- **结构清晰**：使用标题层级组织内容
- **示例完整**：提供完整的使用示例
- **技术细节**：说明技术实现和注意事项

### 3. 脚本规范

- **错误处理**：包含完整的错误处理逻辑
- **参数验证**：验证输入参数的有效性
- **返回格式**：使用 JSON 格式返回结构化数据

## 常见问题

### Q1：如何快速创建技能？

使用 skill-creator 的模板，按照以下步骤：

1. 复制基础模板
2. 修改元数据（name, description）
3. 填写功能说明和使用方法
4. 创建必要的脚本文件
5. 验证格式

### Q2：如何调试技能？

1. 使用 load_skill 加载技能
2. 检查返回的内容是否正确
3. 测试脚本执行
4. 查看错误日志

### Q3：如何发布技能？

1. 确保技能格式正确
2. 测试所有功能
3. 更新版本号
4. 提交到代码仓库