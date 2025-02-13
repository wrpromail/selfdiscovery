import requests
from typing import Dict, Any
import time


def test_query(query: str, need_suggestion: bool = False) -> Dict[str, Any]:
    """
    测试单个查询
    
    Args:
        query: 查询文本
        need_suggestion: 是否需要生成建议
        
    Returns:
        API响应的JSON数据
    """
    url = "http://36.103.203.211:18535/api/query"
    headers = {"Content-Type": "application/json"}
    data = {
        "query": query,
        "need_suggestion": need_suggestion
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # 如果响应状态码不是200，抛出异常
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {str(e)}")
        return None


def run_test_cases():
    """运行测试用例"""
    # 测试用例列表
    test_cases = [
        "喂，客服吗？我这手机13800138000最近话费扣得有点快，能帮我查查余额吗？顺便看看最近都跟谁打电话了，通话时间长不长",
        "那个，我想问一下13900139000的套餐使用情况，我记得流量快用完了，你帮我看看。对了，我开通的那些增值服务都有啥用处啊，能给我介绍一下吗",
        "你好，我是13700137000的机主，这两天老是显示4G，想问问现在的网络状态咋样，能升5G不？还有我的信号老是时有时无的，这是咋回事啊",
        "麻烦帮我查一下13600136000这个月的流量和通话时间还剩多少，感觉用得特别快，帮我看看是不是有什么异常情况",
        "诶，我这个13500135000的亲情号码套餐还能加人吗？顺便帮我看看现在都有谁在共享流量，他们用了多少",
        "你好，13400134000这个号码能开通国际漫游吗？我下个月要出差，想提前了解一下。还有，现在有什么合适的境外流量包推荐吗",
        "帮我查查13300133000这个号，我记得开了好几个增值服务，但不太记得都有啥了，能不能帮我看看哪些用得少，可以取消的",
        "那个，能帮我看看13200132000的套餐使用情况吗？主要是流量，我这个月老是提醒我快超了，想问问是不是有什么更合适的套餐可以推荐",
        "你好，13100131000这号码前两天好像欠费了，但是我记得应该还有话费啊，能帮我查一下具体余额和最近的消费记录吗",
        "麻烦问一下，13000130000这个号码现在的网络制式是什么？我这边信号不太好，想看看是不是可以换个套餐或者升级一下网络，有什么建议吗"
    ]

    # 记录总体测试结果
    results = {
        "total_cases": len(test_cases),
        "successful": 0,
        "failed": 0,
        "total_time": 0,
        "average_time": 0,
        "function_stats": {}  # 记录每个函数被调用的次数
    }

    print("开始测试API服务...")
    print("=" * 50)

    # 测试每个用例
    for i, query in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}/{len(test_cases)}:")
        print(f"查询内容: {query}")
        print("-" * 30)

        start_time = time.time()
        response = test_query(query, need_suggestion=True)  # 启用建议功能
        test_time = time.time() - start_time

        if response:
            results["successful"] += 1
            results["total_time"] += test_time

            # 统计函数调用
            for func in response["executed_functions"]:
                results["function_stats"][func] = results["function_stats"].get(func, 0) + 1

            print(f"执行时间: {response['execution_time']:.2f}毫秒")
            print(f"使用的函数: {', '.join(response['executed_functions'])}")
            print(f"响应内容:\n{response['response']}")

            if response.get("suggestion"):
                print(f"\n智能建议:\n{response['suggestion']}")
        else:
            results["failed"] += 1
            print("测试失败")

        print("-" * 50)

    # 计算平均时间
    if results["successful"] > 0:
        results["average_time"] = results["total_time"] / results["successful"]

    # 打印测试统计
    print("\n测试统计:")
    print(f"总用例数: {results['total_cases']}")
    print(f"成功数: {results['successful']}")
    print(f"失败数: {results['failed']}")
    print(f"总耗时: {results['total_time']:.2f}秒")
    print(f"平均耗时: {results['average_time']:.2f}秒")

    print("\n函数调用统计:")
    for func, count in results["function_stats"].items():
        print(f"- {func}: 调用{count}次")


if __name__ == "__main__":
    run_test_cases()
