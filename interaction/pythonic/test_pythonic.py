import re
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
from langchain.schema import HumanMessage, SystemMessage
import random
from time import time
from model import chat

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

    found_functions = []
    for func in required_functions:
        if func in code:
            found_functions.append(func)

    if not found_functions:
        return False, "没有使用任何预定义函数"

    try:
        compile(code, '<string>', 'exec')
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
        本地变量字典
    """
    try:
        global_context.update({
            'datetime': datetime,
            'timedelta': timedelta,
            'random': random,
            'print': print
        })

        local_context = {}
        print("开始执行生成的代码...")
        exec(code, global_context, local_context)
        print("代码执行完成")
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
                SystemMessage(content="你是一个智能助手"),
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
            print("-" * 30)

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
    # 示例用法
    from pythonic import (
        search_flights,
        check_seat_availability,
        create_booking,
        generate_payment_link,
        send_booking_notification,
        functions_schema,
        PROMPT_TEMPLATE
    )
    
    # 加载mock函数
    mock_functions = {
        'search_flights': search_flights,
        'check_seat_availability': check_seat_availability,
        'create_booking': create_booking,
        'generate_payment_link': generate_payment_link,
        'send_booking_notification': send_booking_notification
    }
    
    # 定义必需的函数
    required_functions = [
        'search_flights',
        'check_seat_availability',
        'create_booking',
        'generate_payment_link',
        'send_booking_notification'
    ]
    
    # 定义测试用例
    test_cases = [
        "我想订明天从北京到上海的商务舱机票，2个人，发送预订信息到我的邮箱",
        "帮我查一下后天从广州到深圳的经济舱航班，一个人"
    ]
    
    # 运行测试
    stats = run_generic_test(
        test_cases=test_cases,
        functions_schema=functions_schema,
        prompt_template=PROMPT_TEMPLATE,
        mock_functions=mock_functions,
        required_functions=required_functions
    )
