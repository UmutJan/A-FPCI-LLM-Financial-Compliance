import json
import os
from typing import List, Dict, Any, Union, Tuple
import time


class RuleStatusPreprocessor:
    """
  规则状态数据预处理器【文件夹批量处理版】
  核心能力：✅ 无初始化输入 ✅ 遍历文件夹读取所有input json ✅ 增量更新output ✅ 结果保存到本地 ✅ 适配A/B/C1/C2/C3/D/E1全规则类型
  处理流程：读取input_table文件夹下所有json文件 → 逐个增量更新 → 保存最终结果到output_table.json
  """

    def __init__(self):
        self.input_table: List[Dict] = []  # 动态累积所有输入规则（用于类型映射）
        self.output_table: List[Dict] = []  # 核心维护的输出表
        # 适配用户规则分类的处理器映射
        self.type_handler_map = {
            "A": self._handle_discrete,
            "B": self._handle_simple_threshold,
            "C1": self._handle_complex_C1,
            "C2": self._handle_complex_C2,
            "C3": self._handle_complex_C3,
            "D": self._handle_discrete_simple,
            "E1": self._handle_discrete_complex_E1
        }

    # ===================== 通用工具方法 =====================
    def _is_comb_exist(self, new_comb: List, exist_combs: List[List]) -> bool:
        """判断离散组合是否存在"""
        return new_comb in exist_combs

    def _update_extreme_value(self, curr_max: Union[str, float], curr_min: Union[str, float], new_val: float) -> Tuple[
        str, str]:
        """统一按原始数值计算极值，最后格式化"""
        if not curr_max or not curr_min:
            return new_val, new_val
        curr_max = float(curr_max) if isinstance(curr_max, (str, int)) else curr_max
        curr_min = float(curr_min) if isinstance(curr_min, (str, int)) else curr_min
        new_max = max(curr_max, new_val)
        new_min = min(curr_min, new_val)
        return new_max, new_min

    def _safe_calculate(self, formula_type: str, **kwargs) -> float:
        """安全运算（除零保护），适配C1/C2/C3"""
        a = kwargs.get("A", 0.0)
        b = kwargs.get("B", 0.0)
        c = kwargs.get("C", 1.0)
        try:
            if formula_type == "C1":  # (A+B)/C
                return (a + b) / c if c != 0 else 0.0
            elif formula_type == "C2":  # A/B
                return a / b if b != 0 else 0.0
            elif formula_type == "C3":  # (A-B)/B
                return (a - b) / b if b != 0 else 0.0
            else:
                return 0.0
        except Exception:
            return 0.0

    def _split_status(self, statuses: Dict) -> Tuple[List[str], List[str], List[str], List[float]]:
        """动态拆分离散/数值字段"""
        discrete_keys, discrete_vals = [], []
        number_keys, number_vals = [], []
        for s_key, s_info in statuses.items():
            s_type = s_info["type"]
            s_val = s_info["value"]
            if (s_type == "" or s_type == "S") and isinstance(s_val, str) and s_val.strip() != "":
                discrete_keys.append(s_key)
                discrete_vals.append(s_val)
            elif isinstance(s_val, (int, float)):
                number_keys.append(s_key)
                number_vals.append(float(s_val))
        return discrete_keys, discrete_vals, number_keys, number_vals

    def _get_calc_mapping(self, statuses: Dict) -> Dict:
        """动态提取运算位映射（A/B/C）"""
        return {
            s_info["type"]: float(s_info["value"])
            if s_info["value"] != "" and isinstance(s_info["value"], (int, float))
            else 0.0
            for s_info in statuses.values()
            if s_info["type"] in ["A", "B", "C"]
        }

    # ===================== 各类规则处理函数 =====================
    def _handle_discrete(self, statuses: Dict, curr_result: List = None, is_init: bool = True) -> Tuple[List, List]:
        """A类：离散型"""
        res_name = list(statuses.keys())
        new_comb = [s_info["value"] for s_info in statuses.values()]
        if is_init:
            return res_name, [new_comb]
        if not self._is_comb_exist(new_comb, curr_result):
            curr_result.append(new_comb)
        return res_name, curr_result

    def _handle_simple_threshold(self, statuses: Dict, curr_result: List = None, is_init: bool = True) -> Tuple[
        List, List]:
        """B类：简单阈值型"""
        s_key = list(statuses.keys())[0]
        new_val = float(statuses[s_key]["value"])
        res_name = [f"{s_key}极大值", f"{s_key}极小值"]
        if is_init:
            return res_name, [new_val, new_val]
        curr_max, curr_min = curr_result
        new_max, new_min = self._update_extreme_value(curr_max, curr_min, new_val)
        return res_name, [new_max, new_min]

    def _handle_complex_C1(self, statuses: Dict, curr_result: List = None, is_init: bool = True) -> Tuple[List, List]:
        """C1类：(A+B)/C"""
        calc_map = self._get_calc_mapping(statuses)
        res_key = [k for k, v in statuses.items() if v["type"] == "D" or (v["value"] == "" and v["type"] == "C")][0]
        res_name = [f"{res_key}极大值", f"{res_key}极小值"]
        calc_result = self._safe_calculate("C1", **calc_map)
        if is_init:
            return res_name, [calc_result, calc_result]
        curr_max, curr_min = curr_result
        new_max, new_min = self._update_extreme_value(curr_max, curr_min, calc_result)
        return res_name, [new_max, new_min]

    def _handle_complex_C2(self, statuses: Dict, curr_result: List = None, is_init: bool = True) -> Tuple[List, List]:
        """C2类：A/B"""
        calc_map = self._get_calc_mapping(statuses)
        res_key = [k for k, v in statuses.items() if v["type"] == "C" or (v["value"] == "" and v["type"] != "")][0]
        res_name = [f"{res_key}极大值", f"{res_key}极小值"]
        calc_result = self._safe_calculate("C2", **calc_map)
        if is_init:
            return res_name, [calc_result, calc_result]
        curr_max, curr_min = curr_result
        new_max, new_min = self._update_extreme_value(curr_max, curr_min, calc_result)
        return res_name, [new_max, new_min]

    def _handle_complex_C3(self, statuses: Dict, curr_result: List = None, is_init: bool = True) -> Tuple[List, List]:
        """C3类：(A-B)/B"""
        calc_map = self._get_calc_mapping(statuses)
        res_key = [k for k, v in statuses.items() if v["type"] == "C" or (v["value"] == "" and v["type"] != "")][0]
        res_name = [f"{res_key}极大值", f"{res_key}极小值"]
        calc_result = self._safe_calculate("C3", **calc_map)
        if is_init:
            return res_name, [calc_result, calc_result]
        curr_max, curr_min = curr_result
        new_max, new_min = self._update_extreme_value(curr_max, curr_min, calc_result)
        return res_name, [new_max, new_min]

    def _handle_discrete_simple(self, statuses: Dict, curr_result: List = None, is_init: bool = True) -> Tuple[
        List, List]:
        """D类：离散-简单阈值型"""
        discrete_keys, discrete_vals, number_keys, number_vals = self._split_status(statuses)
        res_name = discrete_keys + [f"{k}极大值" for k in number_keys] + [f"{k}极小值" for k in number_keys]
        discrete_len = len(discrete_vals)
        number_len = len(number_vals)
        new_row = discrete_vals + number_vals + number_vals

        if is_init:
            return res_name, [new_row]

        for idx, exist_row in enumerate(curr_result):
            if exist_row[:discrete_len] == discrete_vals:
                for n_idx in range(number_len):
                    curr_max = exist_row[discrete_len + n_idx]
                    curr_min = exist_row[discrete_len + number_len + n_idx]
                    new_val = number_vals[n_idx]
                    upd_max, upd_min = self._update_extreme_value(curr_max, curr_min, new_val)
                    exist_row[discrete_len + n_idx] = upd_max
                    exist_row[discrete_len + number_len + n_idx] = upd_min
                break
        else:
            curr_result.append(new_row)
        return res_name, curr_result

    def _handle_discrete_complex_E1(self, statuses: Dict, curr_result: List = None, is_init: bool = True) -> Tuple[
        List, List]:
        """E1类：离散-复杂阈值型"""
        discrete_keys, discrete_vals, _, _ = self._split_status(statuses)
        calc_map = self._get_calc_mapping(statuses)
        res_key = [k for k, v in statuses.items() if v["type"] == "C" or (v["value"] == "" and v["type"] != "")][0]
        res_name = discrete_keys + [f"{res_key}极大值", f"{res_key}极小值"]
        calc_result = self._safe_calculate("C2", **calc_map)
        discrete_len = len(discrete_vals)
        new_row = discrete_vals + [calc_result, calc_result]

        if is_init:
            return res_name, [new_row]

        for idx, exist_row in enumerate(curr_result):
            if exist_row[:discrete_len] == discrete_vals:
                curr_max = exist_row[discrete_len]
                curr_min = exist_row[discrete_len + 1]
                upd_max, upd_min = self._update_extreme_value(curr_max, curr_min, calc_result)
                exist_row[discrete_len] = upd_max
                exist_row[discrete_len + 1] = upd_min
                break
        else:
            curr_result.append(new_row)
        return res_name, curr_result

    # ===================== 格式化输出 =====================
    def _format_output(self) -> List[Dict]:
        """格式化输出表：C1/C2/C3/E1转百分比，A/B/D纯数值"""
        formatted_table = []
        # 构建规则编号-类型映射
        rule_type_map = {r["rule_number"]: r["rule_type"] for r in self.input_table}

        for item in self.output_table:
            rule_no = item["rule_number"]
            rule_type = rule_type_map.get(rule_no, "")
            formatted_item = item.copy()
            result_name = item["resultName"]
            result_data = item["result"]
            need_percent = rule_type in ["C1", "C2", "C3", "E1"]

            # B/C类：一维极值列表
            if rule_type in ["B", "C1", "C2", "C3"]:
                if need_percent:
                    formatted_result = [f"{float(val) * 100:.2f}%" for val in result_data]
                else:
                    formatted_result = [f"{val}" for val in result_data]
                formatted_item["result"] = formatted_result

            # D/E1类：二维组合列表
            elif rule_type in ["D", "E1"]:
                formatted_result = []
                for row in result_data:
                    formatted_row = []
                    for idx, val in enumerate(row):
                        col_name = result_name[idx]
                        if "极大值" in col_name or "极小值" in col_name:
                            if need_percent:
                                formatted_row.append(f"{float(val) * 100:.2f}%")
                            else:
                                formatted_row.append(f"{val}")
                        else:
                            formatted_row.append(val)
                    formatted_result.append(formatted_row)
                formatted_item["result"] = formatted_result

            # A类：离散组合列表
            elif rule_type == "A":
                formatted_item["result"] = result_data

            formatted_table.append(formatted_item)
        return formatted_table

    # ===================== 核心批量处理逻辑 =====================
    def process_folder_inputs(self, input_folder: str = "input_table", output_file: str = "output_table.json"):
        """
        批量处理文件夹中的所有input json文件
        :param input_folder: 输入文件夹路径（默认：input_table）
        :param output_file: 输出文件路径（默认：output_table.json）
        """
        # 1. 检查输入文件夹是否存在
        if not os.path.exists(input_folder):
            os.makedirs(input_folder)
            print(f"⚠️  输入文件夹 {input_folder} 不存在，已自动创建，请放入input json文件后重新运行")
            return

        # 2. 获取文件夹下所有json文件（按文件名排序，确保处理顺序）
        json_files = [f for f in os.listdir(input_folder) if f.endswith(".json")]
        if not json_files:
            print(f"⚠️  输入文件夹 {input_folder} 中无json文件，请放入后重新运行")
            return
        # 按文件名排序（建议命名为：input_1.json, input_2.json...）
        json_files.sort(key=lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0)
        print(f"📄 找到 {len(json_files)} 个输入文件，处理顺序：{json_files}")

        # 3. 逐个读取并增量更新
        for file_name in json_files:
            file_path = os.path.join(input_folder, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    new_input_table = json.load(f)
                print(f"\n🔄 处理文件：{file_name}，包含 {len(new_input_table)} 条规则")

                # 调用增量更新逻辑
                self._process_new_input(new_input_table)
            except Exception as e:
                print(f"❌ 处理文件 {file_name} 失败：{str(e)}")
                continue

        # 4. 格式化并保存最终结果
        final_output = self._format_output()
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 所有文件处理完成！最终结果已保存到：{output_file}")

    def _process_new_input(self, new_input_table: List[Dict]):
        """增量更新核心逻辑（内部调用）"""
        # 构建规则编号-输出表索引映射
        rule_idx_map = {item["rule_number"]: idx for idx, item in enumerate(self.output_table)}
        new_rules = []  # 记录新增规则

        for new_rule in new_input_table:
            rule_no = new_rule["rule_number"]
            rule_type = new_rule["rule_type"]
            rule_content = new_rule["rule_content"]
            statuses = new_rule["statuses"]

            # 校验规则类型是否支持
            if rule_type not in self.type_handler_map:
                print(f"⚠️  规则 {rule_no} 类型 {rule_type} 不支持，跳过处理")
                continue

            # 新规则：自动初始化
            if rule_no not in rule_idx_map:
                res_name, res_data = self.type_handler_map[rule_type](statuses, is_init=True)
                self.output_table.append({
                    "rule_number": rule_no,
                    "rule_content": rule_content,
                    "resultName": res_name,
                    "result": res_data
                })
                rule_idx_map[rule_no] = len(self.output_table) - 1
                new_rules.append(new_rule)
            # 已有规则：增量更新
            else:
                target_idx = rule_idx_map[rule_no]
                curr_res_data = self.output_table[target_idx]["result"]
                new_res_name, new_res_data = self.type_handler_map[rule_type](statuses, curr_res_data, is_init=False)
                self.output_table[target_idx]["resultName"] = new_res_name
                self.output_table[target_idx]["result"] = new_res_data

        # 更新input_table，确保格式化时能匹配到rule_type
        if new_rules:
            self.input_table.extend(new_rules)


# ===================== 测试/运行入口 =====================
if __name__ == "__main__":
    start_time = time.time()

    # 初始化预处理器（无初始输入）
    preprocessor = RuleStatusPreprocessor()

    # 批量处理input_table文件夹下的所有json文件，结果保存到output_table.json
    preprocessor.process_folder_inputs(
        input_folder="input_table",  # 输入文件夹路径
        output_file="output_table_200.json"  # 输出文件路径
    )

    end_time = time.time() - start_time
    print(end_time)