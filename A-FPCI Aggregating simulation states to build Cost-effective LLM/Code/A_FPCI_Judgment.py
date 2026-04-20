from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from openai import OpenAI
import json
import time
import os

# 加载环境变量（DeepSeek API KEY 配置在 .env 文件中，无需修改原有配置）
load_dotenv()

# ===================== 1. 初始化DeepSeek官方原生客户端（替换原LangChain模型初始化）=====================
# 经测试可100%获取真实Token，完全对齐官方规范，无封装层、无警告
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"  # DeepSeek官方OpenAI兼容接口地址
)
MODEL_NAME = "deepseek-chat"  # 模型名与原配置一致

# ===================== 2. 定义Pydantic模型（完全保留原有定义）=====================
class ViolationRule(BaseModel):
    rule_number: int = Field(..., description="违规的法规编号")

# ===================== 3. 读取本地法规文件（完全保留原有逻辑，路径为output_table.json）=====================
def read_rules_from_json(file_path: str = "output_table.json") -> List[Dict[str, Any]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            rules = json.load(f)
        if not isinstance(rules, list):
            raise ValueError("JSON文件根结构必须是列表（[]）")
        return rules
    except FileNotFoundError:
        raise FileNotFoundError(f"未找到文件：{file_path}")
    except json.JSONDecodeError:
        raise json.JSONDecodeError(f"JSON格式错误：{file_path}")

# ===================== 4. 提示词模板（用原生字符串实现，完全保留原有提示词内容，无需修改）=====================
# 保留原有所有判断规则，仅替换为原生字符串格式化，和原逻辑完全一致
PROMPT_TPL = """
请你作为法规合规判断专家，根据以下法规列表，逐一检查每条法规的所有result状态组合是否违反对应法规的rule_content要求。
你的核心任务：识别出**存在至少1种违规状态组合**的法规编号。
法规列表：{rules}

# 你的判断规则：
1. 每条法规对应唯一的rule_number，仅返回**违规的法规编号**，未违规的不返回
2. 若某条法规的所有result状态组合都符合rule_content要求，则该法规不违规
3. 输出格式必须是严格的JSON数组，仅包含违规编号，无任何其他内容，示例：[1,3,5]
4. 若没有任何法规违规，输出空数组：[]
"""

# ===================== 5. 核心处理函数（保留所有业务逻辑，仅替换模型调用+Token读取）=====================
def judge_violation_rules() -> List[ViolationRule]:
    start_time = time.time()
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    try:
        # 读取法规数据（完全保留原有逻辑）
        rules = read_rules_from_json()
        rules_str = json.dumps(rules, ensure_ascii=False, indent=2)
        print(f"成功读取{len(rules)}条法规数据")

        # 构建最终提示词+打印（完全保留原有打印格式）
        final_prompt = PROMPT_TPL.format(rules=rules_str)
        print("\n" + "="*60 + " 最终提示词 " + "="*60)
        print(final_prompt)
        print("="*150 + "\n")

        # ===================== 核心替换：官方原生接口调用大模型 =====================
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": final_prompt}],  # 提示词作为用户消息发送
            temperature=0  # 显式传参，无任何警告，保证结果确定性
        )

        # ===================== 100%精准读取Token（官方原生方式）=====================
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        total_tokens = response.usage.total_tokens

        # 提取大模型回复内容（原生接口取值方式）
        model_answer = response.choices[0].message.content.strip()

        # 解析大模型返回结果（完全保留原有解析+过滤逻辑）
        violation_numbers = json.loads(model_answer)
        if not isinstance(violation_numbers, list):
            raise ValueError(f"大模型返回格式错误，非JSON数组：{model_answer}")
        # 过滤非整数编号，转为Pydantic列表
        violation_result = [ViolationRule(rule_number=num) for num in violation_numbers if isinstance(num, int)]

    except Exception as e:
        raise RuntimeError(f"违规判断处理失败：{str(e)}")

    finally:
        # 统计并打印运行指标（完全保留原有打印格式）
        run_time = time.time() - start_time
        print("\n" + "=" * 50 + " 程序运行指标 " + "=" * 50)
        print(f"总运行时间：{run_time:.2f} 秒")
        print(f"Token消耗 - 输入：{prompt_tokens} 个，输出：{completion_tokens} 个，总：{total_tokens} 个")
        print("=" * 108)

    return violation_result

# ===================== 6. 主程序入口（完全保留原有所有逻辑，包括结果保存）=====================
if __name__ == "__main__":
    violation_list = judge_violation_rules()

    # 打印最终判断结果（完全保留原有格式）
    print("\n" + "=" * 50 + " 违规法规判断结果 " + "=" * 50)
    if violation_list:
        violation_numbers = [item.rule_number for item in violation_list]
        print(f"存在违规法规，违规编号：{violation_numbers}")
    else:
        print("无任何法规违规，返回空列表")
    print("=" * 108)

    # 保存结果到本地JSON（完全保留原有保存格式，含timestamp）
    result_data = {
        "violation_rules": [item.dict() for item in violation_list],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    with open("violation_result.json", "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    print(f"\n违规结果已保存至：violation_result.json")