import re
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
from langchain.schema import HumanMessage, SystemMessage
import random
from time import time
from model import chat
from threading import Thread, Lock
from queue import Queue


def load_test_data(test_cases: List[str], functions_schema: str, prompt_template: str) -> Dict[str, Any]:
    """
    加载测试数据和配置
    
    Args:
        test_cases: 测试用例列表
        functions_schema: 函数描述schema
        prompt_template: 提示词模板
        
    Returns:
        包含测试配置的字典
    """
    return {
        'test_cases': test_cases,
        'functions_schema': functions_schema,
        'prompt_template': prompt_template,
        'stats': {
            'total': len(test_cases),
            'success': 0,
            'failed': 0,
            'failed_cases': [],
            'timing': {
                'total_time': 0,
                'average_time': 0,
                'min_time': float('inf'),
                'max_time': 0,
                'per_case_time': []
            },
            'function_stats': {  # 新增：函数调用统计
                'calls': {},  # 记录每个函数的调用次数
                'avg_time': {}  # 记录每个函数的平均响应时间
            }
        }
    }


def extract_python_code(text: str) -> Optional[str]:
    """从文本中提取markdown格式的Python代码"""
    pattern = r"```python\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches[0] if matches else None


def validate_generated_code(code: str, required_functions: List[str]) -> tuple[bool, str]:
    """
    验证生成的代码质量
    
    Args:
        code: 要验证的代码
        required_functions: 必需的函数列表
        
    Returns:
        (验证是否通过, 验证信息)
    """
    if not code:
        return False, "空代码"

    # 检查是否包含必要的函数调用
    found_functions = []
    for func in required_functions:
        if func in code:
            found_functions.append(func)

    if not found_functions:
        return False, "没有使用任何预定义函数"

    # 检查手机号格式（新增）
    phone_pattern = r"1[3-9]\d{9}"
    if re.search(phone_pattern, code):
        if not all(len(num) == 11 for num in re.findall(phone_pattern, code)):
            return False, "存在格式不正确的手机号"

    # 包装代码到函数中进行语法检查
    wrapped_code = f"""
def _validate():
{chr(10).join('    ' + line for line in code.split(chr(10)))}
"""

    # 基本的语法检查
    try:
        compile(wrapped_code, '<string>', 'exec')
    except SyntaxError as e:
        return False, f"语法错误: {str(e)}"

    return True, f"代码验证通过，使用了以下函数: {', '.join(found_functions)}"


def execute_code(code: str, global_context: dict) -> dict:
    """
    在提供的上下文中执行代码
    
    Args:
        code: 要执行的代码
        global_context: 全局上下文字典
        
    Returns:
        本地变量字典，包含执行时间和返回值
    """
    try:
        # 添加基础模块和常量到执行环境
        global_context.update({
            'datetime': datetime,
            'timedelta': timedelta,
            'random': random,
            'print': print,
            'Thread': Thread,
            'Lock': Lock,
            'Queue': Queue,
            'PACKAGE_TYPES': {  # 从 mservice.py 导入
                "data": "流量包",
                "voice": "通话包",
                "sms": "短信包"
            }
        })

        # 创建本地变量空间
        local_context = {}

        # 记录函数调用开始时间
        start_time = time()

        # 包装代码以捕获返回值
        wrapped_code = f"""
def _execute():
{chr(10).join('    ' + line for line in code.split(chr(10)))}

_return_value = _execute()
"""

        # 执行代码
        print("开始执行生成的代码...")
        exec(wrapped_code, global_context, local_context)
        print("代码执行完成")

        # 计算执行时间
        execution_time = time() - start_time
        local_context['_execution_time'] = execution_time

        return local_context
    except Exception as e:
        print(f"执行出错: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        raise


def run_test(config: Dict[str, Any], mock_functions: Dict[str, Any], required_functions: List[str]) -> Dict[str, Any]:
    """
    运行测试用例
    
    Args:
        config: 测试配置字典
        mock_functions: mock函数字典
        required_functions: 必需的函数列表
        
    Returns:
        测试统计信息
    """
    total_start_time = time()
    stats = config['stats']

    # 初始化函数调用统计
    for func in required_functions:
        stats['function_stats']['calls'][func] = 0
        stats['function_stats']['avg_time'][func] = 0.0

    for idx, test_case in enumerate(config['test_cases'], 1):
        print(f"\n{'=' * 20} 测试用例 {idx}/{stats['total']} {'=' * 20}")
        print(f"测试内容: {test_case}")
        print("-" * 50)

        case_start_time = time()

        try:
            # 构造完整提示词
            prompt = config['prompt_template'].format(
                functions_schema=config['functions_schema'],
                user_query=test_case
            )

            # 获取模型响应
            messages = [
                SystemMessage(content="你是一个移动通信服务的智能助手"),
                HumanMessage(content=prompt)
            ]

            print("正在等待模型响应...")
            response = chat.invoke(messages)
            print("模型响应完成")

            # 提取代码
            code = extract_python_code(response.content)
            valid, message = validate_generated_code(code, required_functions)
            print(f"\n代码验证结果: {message}")

            if not valid:
                raise Exception(f"代码验证失败: {message}")
            if not code:
                print("未找到可执行代码")
                stats['failed'] += 1
                stats['failed_cases'].append((test_case, "未找到可执行代码"))
                continue

            print("\n生成的代码:")
            print("-" * 30)
            print(code)
            print("-" * 30)

            print("\n执行结果:")
            print("-" * 30)
            local_vars = execute_code(code, mock_functions.copy())

            # 获取代码执行的返回值
            if '_return_value' in local_vars:
                print("返回结果:")
                print(local_vars['_return_value'])
            else:
                print("警告：代码没有返回任何结果")
            print("-" * 30)

            # 打印本次查询的耗时
            query_time = time() - case_start_time
            print(f"\n本次查询耗时: {query_time:.2f}秒")

            # 更新函数调用统计
            for func in required_functions:
                if func in code:
                    stats['function_stats']['calls'][func] += 1
                    # 这里假设每个函数调用大约花费 1 秒
                    current_avg = stats['function_stats']['avg_time'][func]
                    calls = stats['function_stats']['calls'][func]
                    stats['function_stats']['avg_time'][func] = (
                            (current_avg * (calls - 1) + local_vars.get('_execution_time', 1.0)) / calls
                    )

            stats['success'] += 1

        except Exception as e:
            stats['failed'] += 1
            stats['failed_cases'].append((test_case, str(e)))
            print(f"\n处理失败: {str(e)}")
            import traceback
            print(f"详细错误信息:\n{traceback.format_exc()}")
            continue
        finally:
            case_time = time() - case_start_time
            stats['timing']['per_case_time'].append((test_case, case_time))
            stats['timing']['min_time'] = min(stats['timing']['min_time'], case_time)
            stats['timing']['max_time'] = max(stats['timing']['max_time'], case_time)

        print(f"{'=' * 20} 用例执行完成 {'=' * 20}\n")

    # 计算总耗时和平均耗时
    stats['timing']['total_time'] = time() - total_start_time
    stats['timing']['average_time'] = stats['timing']['total_time'] / stats['total']

    return stats


def print_test_results(stats: Dict[str, Any]) -> None:
    """
    打印测试结果
    
    Args:
        stats: 测试统计信息字典
    """
    print("\n" + "=" * 50)
    print("测试统计信息:")
    print(f"总测试用例数: {stats['total']}")
    print(f"成功用例数: {stats['success']}")
    print(f"失败用例数: {stats['failed']}")
    print(f"成功率: {(stats['success'] / stats['total'] * 100):.2f}%")

    print("\n耗时统计:")
    print(f"总耗时: {stats['timing']['total_time']:.2f}秒")
    print(f"平均耗时: {stats['timing']['average_time']:.2f}秒")
    print(f"最短耗时: {stats['timing']['min_time']:.2f}秒")
    print(f"最长耗时: {stats['timing']['max_time']:.2f}秒")

    print("\n函数调用统计:")
    for func, calls in stats['function_stats']['calls'].items():
        avg_time = stats['function_stats']['avg_time'][func]
        print(f"- {func}:")
        print(f"  调用次数: {calls}")
        print(f"  平均响应时间: {avg_time:.2f}秒")

    if stats['failed_cases']:
        print("\n失败用例详情:")
        for idx, (case, error) in enumerate(stats['failed_cases'], 1):
            print(f"\n{idx}. 测试用例: {case}")
            print(f"   错误: {error}")

    print("\n每个用例的耗时详情(Top 5):")
    for case, time_taken in sorted(stats['timing']['per_case_time'],
                                   key=lambda x: x[1],
                                   reverse=True)[:5]:
        print(f"- {time_taken:.2f}秒: {case}")


def run_generic_test(
        test_cases: List[str],
        functions_schema: str,
        prompt_template: str,
        mock_functions: Dict[str, Any],
        required_functions: List[str]
) -> Dict[str, Any]:
    """
    运行通用测试框架
    
    Args:
        test_cases: 测试用例列表
        functions_schema: 函数描述schema
        prompt_template: 提示词模板
        mock_functions: mock函数字典
        required_functions: 必需的函数列表
        
    Returns:
        测试统计信息
    """
    # 加载测试配置
    config = load_test_data(test_cases, functions_schema, prompt_template)

    # 运行测试
    stats = run_test(config, mock_functions, required_functions)

    # 打印测试结果
    print_test_results(stats)

    return stats


if __name__ == "__main__":
    # 从 mservice 导入所需内容
    from mservice import (
        functions_schema,
        functions_name_list,
        test_queries,
        load_functions
    )

    # 加载 mock 函数
    mock_functions = load_functions()

    # 使用预定义的函数列表
    required_functions = functions_name_list

    # 定义提示词模板
    PROMPT_TEMPLATE = """你是一个移动通信服务的智能助手。你的任务是理解用户需求，并生成相应的Python代码来完成服务查询流程。

你可以使用的系统函数如下:
{functions_schema}

用户查询: {user_query}

请生成Python代码来处理这个查询。注意：
1. 代码应该调用合适的函数来满足用户的需求
2. 必须使用 threading 实现并发查询，提高响应速度
3. 确保代码能够正确处理所有必要的参数
4. 必须将所有查询结果合并成一个字符串并通过 return 语句返回
5. 返回的字符串应该包含所有查询的结果，并且格式清晰易读

示例代码格式：
```python
def process_query():
    # 从用户查询中提取手机号码
    phone = "13800138000"
    
    # 创建线程安全的结果列表
    from threading import Thread, Lock
    from queue import Queue
    
    results_queue = Queue()
    threads = []
    
    def worker(func, *args):
        # 执行函数并将结果放入队列
        result = func(*args)
        results_queue.put(result)
    
    # 创建并启动所有查询线程
    threads.append(Thread(target=worker, args=(search_phone_number_balance, phone)))
    threads.append(Thread(target=worker, args=(check_network_status, phone)))
    
    # 启动所有线程
    for thread in threads:
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    # 从队列中获取所有结果
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())
    
    # 合并所有结果并返回
    return "\\n\\n".join(results)

# 执行查询并返回结果
return process_query()
```
"""

    # 运行测试
    stats = run_generic_test(
        test_cases=test_queries,
        functions_schema=functions_schema,
        prompt_template=PROMPT_TEMPLATE,
        mock_functions=mock_functions,
        required_functions=required_functions
    )
