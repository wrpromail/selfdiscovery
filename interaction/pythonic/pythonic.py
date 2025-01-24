import re
from typing import Optional
from datetime import datetime, timedelta
from langchain.schema import HumanMessage, SystemMessage
import random
from time import time
from model import chat

functions_schema = """
def search_flights(departure: str, destination: str, date: str, passengers: int = 1, class_type: str = "economy") -> list[dict]:
    \"\"\"
    搜索特定条件的航班

    Args:
        departure: 出发城市
        destination: 目的城市 
        date: 出发日期(YYYY-MM-DD格式)    
        passengers: 乘客数量
        class_type: 舱位类型(economy/business/first)

    Returns:
        航班信息列表,每个航班包含:
        - flight_no: 航班号
        - price: 价格
        - seats: 剩余座位数
        - departure_time: 起飞时间
        - arrival_time: 到达时间
    \"\"\"
    pass

def check_seat_availability(flight_no: str, class_type: str, num_seats: int) -> dict:
    \"\"\"
    检查指定航班的座位可用性

    Args:
        flight_no: 航班号
        class_type: 舱位类型
        num_seats: 所需座位数

    Returns:
        座位可用性信息:
        - available: 是否有足够座位
        - price: 当前价格
        - remaining_seats: 剩余座位数
    \"\"\"
    pass

def create_booking(flight_no: str, passenger_info: list[dict], class_type: str, contact: dict) -> dict:
    \"\"\"
    创建机票预订

    Args:
        flight_no: 航班号
        passenger_info: 乘客信息列表,每个乘客包含:
            - name: 姓名
            - id_type: 证件类型
            - id_number: 证件号码
        class_type: 舱位类型
        contact: 联系人信息:
            - name: 姓名
            - phone: 电话
            - email: 邮箱

    Returns:
        预订信息:
        - booking_id: 预订编号
        - total_price: 总价
        - status: 预订状态
    \"\"\"
    pass

def generate_payment_link(booking_id: str, payment_method: str) -> dict:
    \"\"\"
    生成支付链接

    Args:
        booking_id: 预订编号
        payment_method: 支付方式(alipay/wechat/credit_card)

    Returns:
        支付信息:
        - payment_url: 支付链接
        - expire_time: 过期时间
        - amount: 支付金额
    \"\"\"
    pass

def send_booking_notification(booking_id: str, notification_type: str = "email", language: str = "zh_CN") -> bool:
    \"\"\"
    发送预订通知

    Args:
        booking_id: 预订编号
        notification_type: 通知类型(email/sms/both)
        language: 语言代码

    Returns:
        发送是否成功
    \"\"\"
    pass
"""




def search_flights(departure: str, destination: str, date: str, passengers: int = 1, class_type: str = "economy") -> \
list[dict]:
    """模拟航班搜索"""
    print(f"\n执行 search_flights:")
    print(f"- departure: {departure}")
    print(f"- destination: {destination}")
    print(f"- date: {date}")
    print(f"- passengers: {passengers}")
    print(f"- class_type: {class_type}")
    # 生成3个模拟航班
    base_price = {
        "economy": 1000,
        "business": 3000,
        "first": 8000
    }

    flights = []
    for i in range(3):
        # 生成起飞时间（早上8点到晚上8点之间）
        hour = random.randint(8, 20)
        base_time = datetime.strptime(f"{date} {hour:02d}:00", "%Y-%m-%d %H:%M")

        flight = {
            "flight_no": f"CA{random.randint(1000, 9999)}",
            "price": base_price[class_type] + random.randint(-200, 200),
            "seats": random.randint(2, 10),
            "departure_time": base_time.strftime("%Y-%m-%d %H:%M"),
            "arrival_time": (base_time + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        }
        flights.append(flight)

    return flights


def check_seat_availability(flight_no: str, class_type: str, num_seats: int) -> dict:
    """模拟座位查询"""
    # 随机生成座位信息
    print(f"\n执行 check_seat_availability:")
    print(f"- flight_no: {flight_no}")
    print(f"- class_type: {class_type}")
    print(f"- num_seats: {num_seats}")
    remaining = random.randint(0, 10)
    base_price = {
        "economy": 1000,
        "business": 3000,
        "first": 8000
    }

    return {
        "available": remaining >= num_seats,
        "price": base_price[class_type] + random.randint(-200, 200),
        "remaining_seats": remaining
    }


def create_booking(flight_no: str, passenger_info: list[dict], class_type: str, contact: dict) -> dict:
    """模拟创建预订"""
    print(f"\n执行 create_booking:")
    print(f"- flight_no: {flight_no}")
    print(f"- passenger_info: {passenger_info}")
    print(f"- class_type: {class_type}")
    print(f"- contact: {contact}")
    booking_id = f"B{random.randint(100000, 999999)}"
    base_price = {
        "economy": 1000,
        "business": 3000,
        "first": 8000
    }

    return {
        "booking_id": booking_id,
        "total_price": base_price[class_type] * len(passenger_info),
        "status": "pending_payment"
    }


def generate_payment_link(booking_id: str, payment_method: str) -> dict:
    """模拟生成支付链接"""
    print(f"\n执行 generate_payment_link:")
    print(f"- booking_id: {booking_id}")
    print(f"- payment_method: {payment_method}")
    return {
        "payment_url": f"https://fake-payment.com/{booking_id}",
        "expire_time": (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"),
        "amount": random.randint(1000, 10000)
    }


def send_booking_notification(booking_id: str, notification_type: str = "email", language: str = "zh_CN") -> bool:
    """模拟发送通知"""
    print(f"\n执行 send_booking_notification:")
    print(f"- booking_id: {booking_id}")
    print(f"- notification_type: {notification_type}")
    print(f"- language: {language}")
    # 模拟95%的成功率
    return random.random() < 0.95


PROMPT_TEMPLATE = """你是一个航空订票系统的智能助手。你的任务是理解用户需求，并生成相应的Python代码来完成订票流程。

你可以使用的系统函数如下:
{functions_schema}

要求：
1. 仔细分析用户的需求，确保理解所有关键信息
2. 生成完整的Python代码来实现需求
3. 代码中只能使用上述定义的函数来实现业务逻辑
4. 可以使用Python基础库来处理日期、时间等通用逻辑
5. 需要考虑错误处理，确保代码的健壮性
6. 所有生成的代码都必须放在markdown代码块中，使用```python 和 ``` 包裹

用户需求是：
{user_query}

请生成相应的Python代码来完成这个需求。"""


def load_functions():
    return {
        'search_flights': search_flights,
        'check_seat_availability': check_seat_availability,
        'create_booking': create_booking,
        'generate_payment_link': generate_payment_link,
        'send_booking_notification': send_booking_notification
    }


def extract_python_code(text: str) -> Optional[str]:
    """从文本中提取markdown格式的Python代码"""
    pattern = r"```python\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches[0] if matches else None


def execute_code(code: str, global_context: dict):
    """在提供的上下文中执行代码"""
    try:
        # 添加一些基础模块到执行环境
        global_context.update({
            'datetime': datetime,
            'timedelta': timedelta,
            'random': random,  # 添加random模块
            'print': print  # 允许代码中使用print
        })

        # 创建本地变量空间
        local_context = {}

        # 执行代码
        print("开始执行生成的代码...")
        exec(code, global_context, local_context)
        print("代码执行完成")

        # 返回本地变量，方便调试
        return local_context
    except Exception as e:
        print(f"执行出错: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        raise



def validate_generated_code(code: str) -> tuple[bool, str]:
    """验证生成的代码质量"""
    if not code:
        return False, "空代码"

    # 检查是否包含必要的函数调用
    required_functions = ['search_flights', 'check_seat_availability',
                          'create_booking', 'generate_payment_link',
                          'send_booking_notification']

    found_functions = []
    for func in required_functions:
        if func in code:
            found_functions.append(func)

    if not found_functions:
        return False, "没有使用任何预定义函数"

    # 基本的语法检查
    try:
        compile(code, '<string>', 'exec')
    except SyntaxError as e:
        return False, f"语法错误: {str(e)}"

    return True, f"代码验证通过，使用了以下函数: {', '.join(found_functions)}"



def main():
    test_queries = [
        "我想订明天从北京到上海的商务舱机票，2个人，发送预订信息到我的邮箱",
        "帮我查一下后天从广州到深圳的经济舱航班，一个人",
        "预订下周五从成都到北京的头等舱，3个人，需要短信通知",
        "查询今天杭州到厦门的经济舱航班情况",
        "帮我订后天早上的重庆到武汉的商务舱，2个人，微信支付",
        "查一下下周三从南京到天津的航班，经济舱，就我一个人",
        "预订明天下午的西安到长沙的商务舱，2人，需要邮件确认",
        "帮我看看后天从昆明到贵阳的经济舱机票，3个人",
        "订下周一早上的济南到青岛的头等舱，1人，支付宝支付",
        "查询明天从哈尔滨到大连的商务舱航班，2人",
        "帮我查下今晚深圳到长沙的经济舱航班，1人",
        "预订下周二早上成都到重庆的头等舱，需要邮件通知，2人",
        "查询后天下午从武汉到西安的商务舱，就我自己",
        "订明天早上8点之后的北京到郑州的经济舱，3人，短信通知",
        "帮忙看看下周四从厦门到福州的商务舱航班，2位乘客",
        "预订后天中午的上海到南京的头等舱，1人，支付宝支付",
        "查一下明天从长春到沈阳的经济舱航班情况，4人出行",
        "帮我订今晚的贵阳到成都的商务舱，2人，需要邮件确认",
        "查询下周六早上的天津到大连的经济舱，1人",
        "预订下周三的兰州到西宁的头等舱，2人，微信支付",
        "帮我查询明天从南宁到桂林的商务舱，3位乘客",
        "订后天下午的温州到杭州的经济舱航班，1人，短信通知",
        "查一下今天晚上的合肥到南京的头等舱，2人",
        "帮我预订明天中午的太原到西安的商务舱，1人，支付宝",
        "查询下周五从海口到三亚的经济舱航班，4人家庭出行",
        "预订后天早上的南昌到武汉的头等舱，2人，需要邮件确认",
        "帮我看看明天从徐州到青岛的商务舱，单人出行",
        "订今晚从宁波到福州的经济舱，3人，微信支付",
        "查一下下周一早上的哈尔滨到沈阳的头等舱航班，2人",
        "帮我预订明天从珠海到厦门的商务舱，1人，需要短信通知"
    ]
    # 统计信息
    stats = {
        'total': len(test_queries),
        'success': 0,
        'failed': 0,
        'failed_queries': [],
        'timing': {
            'total_time': 0,
            'average_time': 0,
            'min_time': float('inf'),
            'max_time': 0,
            'per_query_time': []
        }
    }

    # 加载mock函数
    mock_functions = load_functions()

    total_start_time = time()

    for idx, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 20} 测试用例 {idx}/{stats['total']} {'=' * 20}")
        print(f"查询内容: {query}")
        print("-" * 50)

        query_start_time = time()

        try:
            # 构造完整提示词
            prompt = PROMPT_TEMPLATE.format(
                functions_schema=functions_schema,
                user_query=query
            )

            # 获取模型响应
            messages = [
                SystemMessage(content="你是一个航空订票助手"),
                HumanMessage(content=prompt)
            ]

            print("正在等待模型响应...")
            response = chat.invoke(messages)
            print("模型响应完成")

            # 提取代码
            code = extract_python_code(response.content)
            valid, message = validate_generated_code(code)
            print(f"\n代码验证结果: {message}")
            if not valid:
                raise Exception(f"代码验证失败: {message}")
            if not code:
                print("未找到可执行代码")
                stats['failed'] += 1
                stats['failed_queries'].append((query, "未找到可执行代码"))
                continue

            print("\n生成的代码:")
            print("-" * 30)
            print(code)
            print("-" * 30)

            print("\n执行结果:")
            print("-" * 30)
            # 执行代码并获取本地变量
            local_vars = execute_code(code, mock_functions.copy())
            print("-" * 30)

            # 执行成功
            stats['success'] += 1

        except Exception as e:
            stats['failed'] += 1
            stats['failed_queries'].append((query, str(e)))
            print(f"\n处理失败: {str(e)}")
            import traceback
            print(f"详细错误信息:\n{traceback.format_exc()}")
            continue
        finally:
            # 计算并记录本次查询的耗时
            query_time = time() - query_start_time
            stats['timing']['per_query_time'].append((query, query_time))
            stats['timing']['min_time'] = min(stats['timing']['min_time'], query_time)
            stats['timing']['max_time'] = max(stats['timing']['max_time'], query_time)

        print(f"{'=' * 20} 用例执行完成 {'=' * 20}\n")

    # 计算总耗时和平均耗时
    stats['timing']['total_time'] = time() - total_start_time
    stats['timing']['average_time'] = stats['timing']['total_time'] / stats['total']

    # 打印统计信息
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

    if stats['failed_queries']:
        print("\n失败用例详情:")
        for idx, (query, error) in enumerate(stats['failed_queries'], 1):
            print(f"\n{idx}. 查询: {query}")
            print(f"   错误: {error}")

    # 可选：打印每个查询的具体耗时
    print("\n每个查询的耗时详情:")
    for query, time_taken in sorted(stats['timing']['per_query_time'],
                                    key=lambda x: x[1],
                                    reverse=True)[:5]:  # 只显示耗时最长的5个
        print(f"- {time_taken:.2f}秒: {query}")

    return stats

if __name__ == "__main__":
    result = main()
    print(result)
