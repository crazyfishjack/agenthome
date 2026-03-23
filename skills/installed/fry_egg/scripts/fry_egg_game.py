#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
煎鸡蛋小游戏脚本
生成0-100的随机分数，代表煎蛋水平
"""

import random
import json
import sys

def get_score_description(score):
    """根据分数返回描述"""
    if score >= 90:
        return "完美煎蛋！外焦里嫩，火候恰到好处"
    elif score >= 70:
        return "不错的煎蛋，味道很好"
    elif score >= 50:
        return "及格水平，还可以更好"
    elif score >= 30:
        return "需要改进，多加练习"
    else:
        return "建议重新学习煎蛋技巧"

def main():
    """主函数"""
    args = sys.argv[1:]
    
    try:
        # 解析参数（支持难度参数）
        difficulty = "normal"
        for i, arg in enumerate(args):
            if arg == "--difficulty" and i + 1 < len(args):
                difficulty = args[i + 1]
        
        # 根据难度调整分数范围
        if difficulty == "easy":
            score = random.randint(60, 100)  # 简单模式：60-100分
        elif difficulty == "hard":
            score = random.randint(0, 80)    # 困难模式：0-80分
        else:
            score = random.randint(0, 100)   # 普通模式：0-100分
        
        # 获取分数描述和等级
        description = get_score_description(score)
        level = get_score_level(score)
        
        # 构建结果字典
        result = {
            "success": True,
            "score": score,
            "description": description,
            "level": level,
            "difficulty": difficulty,
            "message": f"恭喜！你的煎蛋得了{score}分！{description}"
        }
        
        # 输出JSON结果
        json_output = json.dumps(result, ensure_ascii=False, indent=2)
        print(json_output.encode('utf-8').decode('utf-8'))
        
    except Exception as e:
        # 错误处理
        error_result = {
            "success": False,
            "error": str(e),
            "message": "煎蛋过程中出现了问题，请重试"
        }
        json_output = json.dumps(error_result, ensure_ascii=False, indent=2)
        print(json_output.encode('utf-8').decode('utf-8'))

def get_score_level(score):
    """获取分数等级"""
    if score >= 90:
        return "完美"
    elif score >= 70:
        return "优秀"
    elif score >= 50:
        return "及格"
    elif score >= 30:
        return "需要改进"
    else:
        return "重新学习"

if __name__ == "__main__":
    main()