from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from openai import OpenAI
import json
import time
import os
import csv

# 加载环境变量
load_dotenv()

# ===================== 1. 初始化DeepSeek官方原生客户端 =====================
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)
MODEL_NAME = "deepseek-chat"


# ===================== 2. 定义Pydantic模型（保留但不使用） =====================
class ViolationRule(BaseModel):
    rule_number: int = Field(..., description="违规的法规编号")


# ===================== 3. 读取本地法规文件（动态文件索引） =====================
def read_rules_from_json(file_index: int) -> List[Dict[str, Any]]:
    """
    读取指定索引的法规文件
    :param file_index: 文件编号（1-500）
    :return: 法规列表
    """
    file_path = f"dataSet/input_table{file_index}.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            rules = json.load(f)
        if not isinstance(rules, list):
            raise ValueError(f"JSON文件根结构必须是列表（[]）：{file_path}")
        return rules
    except FileNotFoundError:
        raise FileNotFoundError(f"未找到文件：{file_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"JSON格式错误：{file_path}，错误信息：{str(e)}")


# ===================== 4. 提示词模板（保留） =====================
PROMPT_TPL = """
请你作为法规合规判断专家，根据以下法规内容和状态组合，判断该条法规是否合规。
## 法规信息：
- 法规编号：rule_number
- 法规内容：rule_content
- 当前状态组合：statuses
    -状态取值：value
其余字段不影响法规判断
法规列表：{rules}

# 判断要求：
1. 根据法规内容要求，分析当前状态组合是否符合规定
2. 如果状态组合中的状态取值**存在任何不符合**法规内容要求的情况，需要返回该法规对应唯一的rule_number，仅返回**违规的法规编号**，未违规的不返回
3. 如果状态组合中的状态取值**完全符合**法规内容要求，则该法规不违规
4. 某些涉及计算类（如比值运算，求合再进行比值运算等）法规的statuses字段中计算结果状态的value值为null，**需要你自行通过该statuses字段中其他状态计算得出再去判断合规性**
5. 输出格式必须是严格的JSON数组，仅包含违规法规的编号，无任何其他内容，示例：[1,3,5]
6. 若没有任何法规违规，输出空数组：[]
"""


# ===================== 5. 核心处理函数（修改：仅返回时间和token，支持文件索引） =====================
def judge_violation_rules_single_call(file_index: int) -> Dict[str, Any]:
    """
    单次调用大模型进行合规检测（指定文件索引）
    返回字典包含：运行时间、总token消耗（仅保留核心关注字段）
    """
    start_time = time.time()
    total_tokens = 0

    try:
        # 读取指定索引的法规数据
        rules = read_rules_from_json(file_index)
        rules_str = json.dumps(rules, ensure_ascii=False, indent=2)

        # 构建最终提示词
        final_prompt = PROMPT_TPL.format(rules=rules_str)
        print(final_prompt)

        # 调用大模型
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": final_prompt}],
            temperature=0
        )

        # 读取Token消耗（仅保留总token）
        total_tokens = response.usage.total_tokens

    except Exception as e:
        print(f"第{file_index}次调用处理失败：{str(e)}")

    finally:
        # 计算运行时间
        run_time = time.time() - start_time

    return {
        "time": run_time,          # 单次调用耗时（秒）
        "total_tokens": total_tokens  # 单次调用总token消耗
    }


# ===================== 7. 主程序入口（核心修改） =====================
if __name__ == "__main__":
    # 1. 配置实验参数
    total_calls = 500  # 循环调用500次
    results = []       # 存储每轮实验数据
    cumulative_time = 0  # 累计总时间
    cumulative_tokens = 0  # 累计总token

    # 2. 创建结果保存目录（不存在则创建）
    output_dir = "experiment1and2"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 3. 开始循环调用
    print(f"开始进行{total_calls}次合规检测调用...")
    print("=" * 80)

    for i in range(1, total_calls + 1):
        print(f"正在进行第 {i}/{total_calls} 次调用...")

        # 每次调用前设置1秒sleep（不计入实验时间）
        time.sleep(1)

        # 执行合规检测（传入当前文件索引i）
        call_result = judge_violation_rules_single_call(i)

        # 更新累计值
        cumulative_time += call_result["time"]
        cumulative_tokens += call_result["total_tokens"]

        # 记录核心数据（仅保留调用次数、单次耗时、单次token、累计时间、累计token）
        result_entry = {
            "call_index": i,                  # 调用次数（1-500）
            "single_time": call_result["time"],  # 单次调用耗时（秒）
            "single_tokens": call_result["total_tokens"],  # 单次调用总token
            "cumulative_time": cumulative_time,  # 累计总时间
            "cumulative_tokens": cumulative_tokens  # 累计总token
        }
        results.append(result_entry)

        # 打印本次调用结果（简化版）
        print(f"  第{i}次调用: 单次耗时={call_result['time']:.2f}s, 单次token={call_result['total_tokens']}, "
              f"累计时间={cumulative_time:.2f}s, 累计token={cumulative_tokens}")

        # 每100次打印关键节点进度（满足"每一百次为一个关键节点"要求）
        if i % 100 == 0:
            print(f"\n--- 第{i}次调用（关键节点）完成，进度摘要 ---")
            print(f"累计总时间: {cumulative_time:.2f}s")
            print(f"累计总Token数: {cumulative_tokens}")
            print(f"平均单次耗时: {cumulative_time / i:.2f}s")
            print(f"平均单次token: {cumulative_tokens / i:.0f}")
            print("-" * 40)

    # 4. 实验完成，打印汇总信息
    print(f"\n{total_calls}次调用全部完成!")
    print(f"\n最终统计汇总:")
    print(f"总调用次数: {total_calls}")
    print(f"累计总时间: {cumulative_time:.2f}s")
    print(f"累计总Token数: {cumulative_tokens}")
    print(f"平均单次调用时间: {cumulative_time / total_calls:.2f}s")
    print(f"平均单次调用Token消耗: {cumulative_tokens / total_calls:.0f}")

    # 5. 生成实验数据文件（CSV格式，适合后续画图、计算平均和误差棒）
    # 文件名格式：experiment3_时间戳.csv（带experiment1标识）
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"experiment3_{timestamp}.csv")

    # 写入CSV文件（表头对应记录的字段，便于后续pandas/Matplotlib处理）
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["call_index", "single_time", "single_tokens", "cumulative_time", "cumulative_tokens"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()  # 写入表头
        writer.writerows(results)  # 写入所有实验数据

    print(f"\n实验数据文件已保存至: {output_file}")

    # 6. 生成简易汇总文件（可选，辅助验证）
    summary_file = os.path.join(output_dir, f"experiment3_summary_{timestamp}.json")
    summary_data = {
        "experiment_info": {
            "total_calls": total_calls,
            "total_cumulative_time": cumulative_time,
            "total_cumulative_tokens": cumulative_tokens,
            "avg_single_time": cumulative_time / total_calls,
            "avg_single_tokens": cumulative_tokens / total_calls,
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "data_file": output_file
        }
    }
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    print(f"实验汇总文件已保存至: {summary_file}")
    print("\n实验完成!")