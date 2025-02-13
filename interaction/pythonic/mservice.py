from datetime import datetime, timedelta
import random
from typing import Optional, List
import time
from langchain.schema import HumanMessage, SystemMessage
from model import chat, suggest
from test_mservice import extract_python_code, validate_generated_code, execute_code

functions_schema = """
def search_phone_number_balance(phone_number: str) -> str:
    \"\"\"
    查询指定手机号码的账户余额
    
    Args:
        phone_number: 手机号码
        
    Returns:
        账户余额信息
    \"\"\"
    pass

def query_value_added_services(phone_number: str) -> List[str]:
    \"\"\"
    查询用户开通的增值服务列表
    
    Args:
        phone_number: 手机号码
        
    Returns:
        已开通的增值服务名称列表
    \"\"\"
    pass

def query_basic_package_usage(phone_number: str) -> str:
    \"\"\"
    查询用户基本套餐的使用情况
    
    Args:
        phone_number: 手机号码
        
    Returns:
        各项服务使用情况
    \"\"\"
    pass

def query_addon_package_usage(phone_number: str, package_type: Optional[str] = None) -> str:
    \"\"\"
    查询用户增值包的使用情况
    
    Args:
        phone_number: 手机号码
        package_type: 可选，包类型(data/voice/sms)
        
    Returns:
        指定类型的使用情况
    \"\"\"
    pass

def get_package_recommendations(phone_number: str) -> str:
    \"\"\"
    获取套餐推荐
    
    Args:
        phone_number: 手机号码
        
    Returns:
        推荐套餐列表
    \"\"\"
    pass

def check_network_status(phone_number: str) -> str:
    \"\"\"
    查询用户当前网络状态
    
    Args:
        phone_number: 手机号码
        
    Returns:
        网络状态信息
    \"\"\"
    pass

def query_last_calls(phone_number: str, limit: int = 5) -> str:
    \"\"\"
    查询最近通话记录
    
    Args:
        phone_number: 手机号码
        limit: 返回记录数量
        
    Returns:
        通话记录列表
    \"\"\"
    pass

def check_service_availability(phone_number: str, service_type: str) -> str:
    \"\"\"
    检查特定服务是否可用于该号码
    
    Args:
        phone_number: 手机号码
        service_type: 服务类型
        
    Returns:
        服务可用性
    \"\"\"
    pass

def query_value_added_service_usage(phone_number: str, service_name: str) -> str:
    \"\"\"
    查询特定增值服务的使用情况
    
    Args:
        phone_number: 手机号码
        service_name: 增值服务名称
        
    Returns:
        服务使用情况描述
    \"\"\"
    pass

def query_data_sharing_members(phone_number: str) -> List[dict]:
    \"\"\"
    查询流量共享成员列表及使用情况
    
    Args:
        phone_number: 主号码
        
    Returns:
        成员使用情况列表
    \"\"\"
    pass

def manage_family_numbers(phone_number: str, action: str = "query", target_number: str = None) -> str:
    \"\"\"
    管理亲情号码
    
    Args:
        phone_number: 主号码
        action: 操作类型 (query/add/remove)
        target_number: 目标亲情号码
        
    Returns:
        操作结果描述
    \"\"\"
    pass

"""

functions_name_list = [
    'search_phone_number_balance',
    'query_value_added_services',
    'query_basic_package_usage',
    'query_addon_package_usage',
    'get_package_recommendations',
    'check_network_status',
    'query_last_calls',
    'check_service_availability',
    'query_value_added_service_usage',
    'query_data_sharing_members',
    'manage_family_numbers'
]

test_queries = [
    "喂，帮我看看13800138000这个号码还有多少话费啊，顺便看看最近都跟谁打电话了，对了，现在是5G还是4G啊",
    "那个，我想问下13900139000的套餐用得怎么样了，流量快没了吗？我看我好像开了好几个增值服务，都有啥啊，能给我推荐个合适的套餐不",
    "你好，我这个13700137000好像欠费了，帮我查查欠了多少，如果补上的话能马上开通5G不，这边信号老是不太好",
    "麻烦帮我查一下13600136000，流量和通话时间还剩多少，最近这话费花得有点快，帮我看看都打给谁了",
    "诶，13500135000这个号码的套餐情况帮我查一下呗，主要看看流量语音短信这些，还有最近新开的那些业务都查一下",
    "客服你好，13800138000这月余额有点不对劲，帮我查下通话记录，还有现在用的是4G还是5G，信号咋样，有啥合适的套餐推荐不",
    "那什么，13900139000这号码是不是欠费停机了啊，要是欠费了得充多少，顺便问下我那个流量包还够用不",
    "帮我查下这个13700137000，套餐用得差不多了，想看看基本套餐和那些增值服务都咋样了，是不是该换个套餐了",
    "13600136000这信号老差，都没法用，你给我看看是不是可以升级到5G，顺便查查最近这话费和余额呗",
    "你好，能帮我看看13500135000的各项使用情况吗，就是流量啊短信啊这些，再看看有什么优惠套餐",
    "诶，那个13800138000，流量眼看着就要没了，帮我看下还剩多少，能推荐个实惠的套餐不，对了，这信号老是时好时差",
    "您好，我想问下13900139000这号码，就是余额和欠费的情况，还有我记得上次客服给我开了几个业务，都有啥啊，能给我推荐个划算的套餐吗",
    "麻烦查一下13700137000的整体情况，余额啊套餐啊网络状态啊都看看，感觉这套餐不太合适，老是超",
    "13600136000这号码，这月话费花得特别快，帮我查查通话记录和余额呗，看看都花哪去了，有啥便宜的套餐能推荐的",
    "那个，13500135000这手机，流量和通话使用得咋样了，信号老是不好，你给我看看开了啥业务没",
    "喂，13800138000现在是啥网络啊，老是卡，信号咋样，我这套餐都快用完了，看看还有啥合适的套餐",
    "帮我查一下13900139000，就是余额欠费这些，还有套餐用得咋样了，最近跟谁打电话了，都记不清了",
    "那什么，13700137000这号码，能帮我看看各种使用情况不，主要是基本套餐和那些增值服务的用量，再看看有啥优惠活动",
    "13600136000这手机好像出问题了，帮我查查余额和消费记录呗，看看是不是有啥异常，网络状态也帮我瞅瞅",
    "你好，能帮我查一下13500135000的所有情况吗，就是账户状态啊，套餐使用情况啊，网络状态啊，感觉哪里不太对",
    "诶，那个15900000001，我想问下现在信号怎么样，老是断断续续的，顺便看看流量和通话时间够用不",
    "你好，帮我查查18611112222这号码呗，主要是看看余额，还有最近这信号老是不好，能升级到5G不",
    "麻烦问下13688889999，这月套餐快到期了，想看看用得咋样，顺便推荐个合适的套餐",
    "喂，17755556666这号码，能帮我看看是不是有什么异常啊，话费扣得特别快，通话记录和余额都帮我查查",
    "那个，13866667777这手机，信号特别差，都快没法用了，帮我看看是不是可以换个套餐或者升级一下",
    "您好，能帮我查一下15922223333的使用情况吗，感觉这月用得特别快，想看看是不是哪里出问题了",
    "帮我看看18977778888这号码呗，好像有点问题，余额扣得特别快，通话记录和流量都帮我查查",
    "13855554444这手机，能帮我看看现在是什么情况不，套餐用得差不多了，想换个合适的",
    "诶，那个17733334444，帮我查查余额和套餐使用情况呗，感觉这月用得不太对劲",
    "你好，15944445555这号码的情况帮我看看，主要是流量和通话记录，还有现在信号咋样"
]

# 简化的套餐类型
PACKAGE_TYPES = {
    "data": "流量包",
    "voice": "通话包",
    "sms": "短信包"
}


def load_functions():
    """加载所有函数"""
    return {
        'search_phone_number_balance': search_phone_number_balance,
        'query_value_added_services': query_value_added_services,
        'query_basic_package_usage': query_basic_package_usage,
        'query_addon_package_usage': query_addon_package_usage,
        'get_package_recommendations': get_package_recommendations,
        'check_network_status': check_network_status,
        'query_last_calls': query_last_calls,
        'check_service_availability': check_service_availability,
        'query_value_added_service_usage': query_value_added_service_usage,
        'query_data_sharing_members': query_data_sharing_members,
        'manage_family_numbers': manage_family_numbers
    }


def search_phone_number_balance(phone_number: str) -> str:
    """查询指定手机号码的账户余额"""
    time.sleep(random.uniform(0.75, 1.25))
    balance = round(random.uniform(-10, 50), 2)
    status = "欠费" if balance < 0 else "正常"
    return f"[执行函数：search_phone_number_balance]手机号{phone_number}的账户余额查询结果：\n余额：{balance}元\n账户状态：{status}\n"


def query_value_added_services(phone_number: str) -> List[str]:
    """
    查询用户开通的增值服务列表
    
    Args:
        phone_number: 手机号码
        
    Returns:
        已开通的增值服务名称列表
    """
    services = ["5G畅游包", "流量共享", "亲情号码", "来电提醒"]
    return random.sample(services, random.randint(1, len(services)))


def query_basic_package_usage(phone_number: str) -> str:
    """查询用户基本套餐的使用情况"""
    time.sleep(random.uniform(0.75, 1.25))
    data = f"{random.randint(0, 100)}GB/{random.randint(100, 200)}GB"
    voice = f"{random.randint(0, 100)}分钟/{random.randint(100, 200)}分钟"
    sms = f"{random.randint(0, 100)}条/{random.randint(100, 200)}条"
    
    return f"""[执行函数：query_basic_package_usage]\n手机号{phone_number}的基本套餐使用情况：
流量使用：{data}
通话使用：{voice}
短信使用：{sms}
"""


def query_addon_package_usage(phone_number: str, package_type: Optional[str] = None) -> str:
    """查询用户增值包的使用情况"""
    time.sleep(random.uniform(0.75, 1.25))
    
    # 参数验证
    valid_types = list(PACKAGE_TYPES.keys())
    if package_type and package_type not in valid_types:
        return f"错误：无效的套餐类型 {package_type}，有效类型为：{', '.join(valid_types)}\n[执行函数：query_addon_package_usage]"
    
    if not package_type:
        package_type = random.choice(valid_types)
    
    type_name = PACKAGE_TYPES.get(package_type, "未知类型")
    
    if package_type == "data":
        usage = f"{random.randint(0, 50)}GB/{random.randint(50, 100)}GB"
    elif package_type == "voice":
        usage = f"{random.randint(0, 100)}分钟/{random.randint(100, 200)}分钟"
    else:  # sms
        usage = f"{random.randint(0, 100)}条/{random.randint(100, 200)}条"
    
    return f"""\n手机号{phone_number}的{type_name}增值包使用情况：
使用量：{usage}
"""


def get_package_recommendations(phone_number: str) -> str:
    """获取套餐推荐"""
    time.sleep(random.uniform(0.75, 1.25))
    recommendations = []
    for pkg_type, type_name in PACKAGE_TYPES.items():
        if random.choice([True, False]):
            price = round(random.uniform(10, 100), 2)
            desc = f"{type_name}{random.randint(1, 5)}"
            recommendations.append(f"- {desc}：{price}元/月")
    
    result = f"[执行函数：get_package_recommendations]\n手机号{phone_number}的套餐推荐：\n"
    if recommendations:
        result += "\n".join(recommendations)
    else:
        result += "暂无合适的套餐推荐"
    result += "\n"
    return result


def check_network_status(phone_number: str) -> str:
    """查询用户当前网络状态"""
    time.sleep(random.uniform(0.75, 1.25))
    network_types = ["5G", "4G", "3G", "2G"]
    network_type = random.choice(network_types)
    signal_strength = random.randint(1, 5)
    location = random.choice(["室内", "室外"])
    
    return f"""[执行函数：check_network_status]\n手机号{phone_number}的网络状态：
网络类型：{network_type}
信号强度：{signal_strength}格
当前位置：{location}
"""


def query_last_calls(phone_number: str, limit: int = 5) -> str:
    """查询最近通话记录"""
    time.sleep(random.uniform(0.75, 1.25))  # 随机延时500-1500ms
    
    # 参数验证
    try:
        limit = int(limit)
        if limit < 1 or limit > 20:
            limit = 5
    except (ValueError, TypeError):
        limit = 5
    
    calls = []
    for _ in range(limit):
        duration = random.randint(1, 60)
        call_type = random.choice(["呼入", "呼出"])
        call_time = datetime.now() - timedelta(hours=random.randint(1, 24))
        number = f"1{random.randint(3, 9)}{''.join([str(random.randint(0, 9)) for _ in range(9)])}"
        calls.append(f"- {call_time.strftime('%Y-%m-%d %H:%M:%S')} {call_type} {number} 通话{duration}分钟")
    
    return f"""[执行函数：query_last_calls]\n手机号{phone_number}的最近{limit}条通话记录：\n{"".join(f"{call}\n" for call in calls)}"""


def check_service_availability(phone_number: str, service_type: str) -> str:
    """检查特定服务是否可用于该号码"""
    time.sleep(random.uniform(0.75, 1.25))  
    
    # 参数验证
    if not service_type:
        return f"错误：服务类型不能为空\n[执行函数：check_service_availability]"
    
    is_available = random.choice([True, False])
    can_subscribe = random.choice([True, False]) if is_available else False
    
    result = f"[执行函数：check_service_availability]\n手机号{phone_number}的{service_type}服务查询结果：\n"
    if is_available:
        result += f"该服务当前可用"
        if can_subscribe:
            result += "，并且可以立即开通"
        else:
            result += "，但暂时无法开通"
    else:
        result += "该服务当前不可用"

    return result


def query_value_added_service_usage(phone_number: str, service_name: str) -> str:
    """
    查询特定增值服务的使用情况
    
    Args:
        phone_number: 手机号码
        service_name: 增值服务名称
        
    Returns:
        服务使用情况描述
    """
    usage_templates = {
        "5G畅游包": "本月已使用{usage}GB，剩余{remaining}GB",
        "流量共享": "已分享{usage}GB给{num}个成员",
        "亲情号码": "已拨打亲情号码{duration}分钟，优惠{amount}元",
        "来电提醒": "本月已转发{count}次提醒"
    }
    
    if service_name not in usage_templates:
        return f"未找到{service_name}的使用记录"
        
    template = usage_templates[service_name]
    if service_name == "5G畅游包":
        return template.format(usage=random.randint(10, 50), remaining=random.randint(0, 20))
    elif service_name == "流量共享":
        return template.format(usage=random.randint(1, 10), num=random.randint(1, 3))
    elif service_name == "亲情号码":
        return template.format(duration=random.randint(60, 300), amount=random.randint(10, 50))
    else:
        return template.format(count=random.randint(5, 20))


def query_data_sharing_members(phone_number: str) -> List[dict]:
    """
    查询流量共享成员列表及使用情况
    
    Args:
        phone_number: 主号码
        
    Returns:
        成员使用情况列表
    """
    members = []
    for i in range(random.randint(1, 3)):
        member = {
            "phone": f"135{random.randint(10000000, 99999999)}",
            "used_data": random.randint(1, 10),
            "remaining_data": random.randint(0, 5)
        }
        members.append(member)
    return members


def manage_family_numbers(phone_number: str, action: str = "query", target_number: str = None) -> str:
    """
    管理亲情号码
    
    Args:
        phone_number: 主号码
        action: 操作类型 (query/add/remove)
        target_number: 目标亲情号码
        
    Returns:
        操作结果描述
    """
    family_numbers = [f"134{random.randint(10000000, 99999999)}" for _ in range(random.randint(1, 3))]
    
    if action == "query":
        return f"当前亲情号码列表：{', '.join(family_numbers)}"
    elif action == "add":
        return f"已添加亲情号码：{target_number}"
    elif action == "remove":
        return f"已移除亲情号码：{target_number}"
    else:
        return "不支持的操作类型"


def handle_query(query: str) -> tuple[float, str, list[str]]:
    """
    处理单个查询请求，返回执行时间、响应文本和执行的函数列表
    
    Args:
        query: 用户查询文本
        
    Returns:
        tuple: (执行时间（毫秒）, 响应文本, 执行的函数列表)
    """
    # 使用预定义的提示词模板
    prompt_template = """你是一个移动通信服务的智能助手。你的任务是理解用户需求，并生成相应的Python代码来完成服务查询流程。

可用的函数定义如下：
{functions_schema}

用户查询：{user_query}

请生成Python代码来处理这个查询。要求：
1. 代码应该调用上述预定义的函数来完成查询
2. 将所有查询结果拼接成一个字符串并返回
3. 使用 markdown 格式输出代码，例如：
```python
# 处理用户查询
result = []  # 存储所有查询结果

# 调用相关函数并收集结果
result.append(...)
result.append(...)

# 返回拼接后的结果
return "\\n".join(result)
```"""
    
    # 构造完整提示词
    prompt = prompt_template.format(
        functions_schema=functions_schema,
        user_query=query
    )

    # 构建消息
    messages = [
        SystemMessage(content="你是一个移动通信服务的智能助手"),
        HumanMessage(content=prompt)
    ]
    
    start_time = time.time()
    
    try:
        # 获取模型响应
        response = chat.invoke(messages)  # 使用 invoke 而不是直接调用
        
        # 提取代码
        code = extract_python_code(response.content)
        if not code:
            raise Exception("未找到可执行代码")
            
        # 验证代码
        valid, message = validate_generated_code(code, functions_name_list)
        if not valid:
            raise Exception(f"代码验证失败: {message}")
            
        # 执行代码
        mock_functions = load_functions()
        local_vars = execute_code(code, mock_functions.copy())
        
        # 获取执行结果
        response_text = local_vars.get('_return_value', '执行完成，但没有返回值')
        
        # 提取执行的函数列表
        executed_functions = []
        for func in functions_name_list:
            if func in code:
                executed_functions.append(func)
        
        # 计算总执行时间（毫秒）
        execution_time = (time.time() - start_time) * 1000
        
        return execution_time, str(response_text), executed_functions
        
    except Exception as e:
        # 计算执行时间（即使发生错误）
        execution_time = (time.time() - start_time) * 1000
        error_message = f"处理查询时出错: {str(e)}"
        return execution_time, error_message, []


def generate_suggestions(user_query: str, query_response: str) -> str:
    """
    根据用户查询和查询结果生成智能建议
    
    Args:
        user_query: 用户的原始查询文本
        query_response: 查询的响应结果
        
    Returns:
        str: 生成的建议内容
    """
    _system_message = """你是一个移动通信服务的智能助手, 接下来会传递针对用户的查询的响应内容。
    你需要根据查询结果，生成一句话建议。诸如：
    1. 如果用户欠费则建议用户尽快进行充值，并提供一些充值渠道建议。
    2. 如果用户的某增值服务用量小于三分之一，则建议用户升级该增值服务。
    3. 如果用户购买了多项增值服务，可以建议用户评估下是否需要调整套餐。
    """
    messages = [
        SystemMessage(content=_system_message),
        HumanMessage(content=f"用户查询内容:\n{user_query}\n查询结果:\n{query_response}")
    ]
    response = suggest.invoke(messages)
    return response.content


if __name__ == "__main__":
    # 测试两个查询
    test_queries = [
        "查询13800138000的话费余额",
        "查看13900139000的套餐使用情况和增值服务"
    ]
    
    for query in test_queries:
        print(f"\n处理查询: {query}")
        print("-" * 50)
        
        # 执行查询
        execution_time, response, executed_functions = handle_query(query)
        
        print(f"执行时间: {execution_time:.2f}毫秒")
        print(f"使用的函数: {', '.join(executed_functions)}")
        print(f"响应内容:\n{response}")
        
        # 生成建议
        suggestion = generate_suggestions(query, response)
        print(f"\n智能建议:\n{suggestion}")
        print("-" * 50)
