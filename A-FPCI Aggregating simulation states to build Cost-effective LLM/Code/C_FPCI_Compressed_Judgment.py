import os
import json
import time
import csv
from dotenv import load_dotenv
from openai import OpenAI

# ===================== 加载环境变量 =====================
load_dotenv()

# ===================== 固定配置 =====================
INPUT_DIR = "dataSet"
OUTPUT_DIR = "Output"
GROUP_SIZE = 50
MODEL_NAME = os.getenv("QWEN_MODEL_NAME")

# ===================== OpenAI兼容模式调用 =====================
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# ===================== 通用压缩提示词 =====================
COMPRESS_PROMPT = """
你是专业的JSON文本压缩助手，请严格按照以下要求压缩文本：
1. 压缩对象：JSON格式的法规合规数据
2. 压缩规则：
   - 精简冗余文字、重复描述、无意义修饰词
   - 严格保留所有核心字段：rule_number、rule_content、statuses、value
   - 绝对保证JSON语法完整、可直接解析
   - 不丢失任何合规判断所需的核心信息
   - 最大限度压缩文本长度
3. 输出要求：仅返回压缩后的纯JSON字符串，无任何多余文字、解释、注释

待压缩文本：
{text}
"""


# ===================== 大模型压缩函数（返回结果+Token） =====================
def compress_with_qwen(raw_text: str) -> tuple[str, int, int]:
    prompt = COMPRESS_PROMPT.format(text=raw_text)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    compressed_text = response.choices[0].message.content.strip()
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    return compressed_text, input_tokens, output_tokens


# ===================== 批量处理（仅处理351-500，共3组） =====================
def process_files():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    token_statistics = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_group_time = 0

    print("✅ 通义千问3.5-plus 初始化完成，开始处理 400~500 文件...")

    # 🔥 核心修改：只运行第8、9、10组（对应351-500）
    for group_num in range(10, 11):
        # 计算文件范围
        start = (group_num - 1) * GROUP_SIZE + 1
        end = group_num * GROUP_SIZE
        all_data = []
        # 每组开始计时
        group_start_time = time.time()

        print(f"\n{'=' * 50}")
        print(f"处理第 {group_num} 组：文件 {start} ~ {end}")

        # 读取50个文件
        for idx in range(start, end + 1):
            file_path = os.path.join(INPUT_DIR, f"input_table{idx}.json")
            if not os.path.exists(file_path):
                print(f"⚠️ 跳过：input_table{idx}.json")
                continue
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)

        # 合并+压缩
        raw_json = json.dumps(all_data, ensure_ascii=False, indent=2)
        try:
            compressed_json, input_tokens, output_tokens = compress_with_qwen(raw_json)
        except Exception as e:
            print(f"❌ 第{group_num}组压缩失败：{str(e)}")
            continue

        # 计算本组耗时
        group_cost_time = time.time() - group_start_time
        total_group_time += group_cost_time

        # 统计与保存
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        # 输出文件：output_8.json / 9.json /10.json 不覆盖之前文件
        output_path = os.path.join(OUTPUT_DIR, f"output_{group_num}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(compressed_json)

        # 记录日志（新增耗时字段）
        group_stats = {
            "group_num": group_num,
            "file_range": f"{start}-{end}",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "group_time_seconds": round(group_cost_time, 2),  # 本组耗时
            "output_file": output_path
        }
        token_statistics.append(group_stats)
        print(f"✅ 第{group_num}组完成 | 输入Token：{input_tokens} | 输出Token：{output_tokens} | 耗时：{group_cost_time:.2f}s")

    # 总统计
    print(f"\n{'=' * 50}")
    print("🎉 400~500 文件压缩全部完成！")
    print(f"总输入Token：{total_input_tokens}")
    print(f"总输出Token：{total_output_tokens}")
    print(f"三组总耗时：{total_group_time:.2f} 秒")

    # 保存Token+耗时明细（CSV新增耗时列）
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    stats_file = os.path.join(OUTPUT_DIR, f"compress_token_stats_400-500_{timestamp}.csv")
    with open(stats_file, "w", newline="", encoding="utf-8") as f:
        # 字段增加 group_time_seconds 耗时
        fieldnames = ["group_num", "file_range", "input_tokens", "output_tokens", "total_tokens", "group_time_seconds", "output_file"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(token_statistics)
    print(f"\n📄 Token+耗时统计文件已保存：{stats_file}")


if __name__ == "__main__":
    # 程序总耗时
    program_start = time.time()
    process_files()
    program_end = time.time()
    print(f"\n⏱️ 程序总运行时长：{program_end - program_start:.2f} 秒")
    print(f"{'=' * 50}")