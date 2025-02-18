from typing import Dict, TypedDict, Annotated, List, Optional
from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from time import time
import json

from handlers import get_disk_usage, scan_large_files_fast, get_gpu_info, get_process_info
from model import chat

# 定义函数 schema
functions_schema = '''
以下是可用的系统函数：

1. get_disk_usage()
   功能: 获取物理磁盘使用情况，排除系统相关分区和虚拟设备
   返回: 磁盘信息列表，每个磁盘包含：
        - mount_point: 挂载点
        - total_gb: 总容量(GB)
        - used_gb: 已用容量(GB)
        - usage_percent: 使用百分比
        - filesystem: 文件系统

2. scan_large_files_fast(mount_point: str, total_size_gb: float = None, max_depth: int = 3, limit: int = 30)
   功能: 快速扫描指定挂载点下的大文件和目录
   参数：
        - mount_point: 挂载点路径
        - total_size_gb: 磁盘总容量（GB），不指定则使用10GB作为基准
        - max_depth: 最大递归深度，默认为3
        - limit: 返回结果的最大数量，默认30
   返回: 大文件和目录列表

3. get_gpu_info()
   功能: 获取GPU信息并返回结构化数据
   返回: 包含所有GPU信息的字典：
        - timestamp: 时间戳
        - gpus: GPU列表，每个GPU包含：
            - id: GPU ID
            - name: GPU名称
            - temperature: 温度
            - fan_speed: 风扇速度
            - power: 功率信息
            - utilization: 使用率
            - memory: 内存使用情况
            - processes: 进程列表

4. get_process_info(pid_list: List[int])
   功能: 获取指定PID列表的进程信息
   参数：
        - pid_list: PID列表
   返回: 进程信息列表，每个进程包含：
        - pid: 进程ID
        - exists: 是否存在
        - user: 所属用户
        - create_time: 创建时间
        - cmdline: 完整命令行
        - error: 错误信息（如果有）
'''

# 定义图状态
class GraphState(TypedDict):
    chat_model: any  # LLM模型
    request: str  # 用户请求
    messages: Annotated[list, add_messages]  # 消息历史
    generated_code: str  # 生成的代码
    execution_result: any  # 执行结果
    used_functions: List[str]  # 使用的函数列表
    start_time: float  # 开始时间
    end_time: float  # 结束时间

def extract_python_code(text: str) -> str:
    """从文本中提取Python代码"""
    import re
    pattern = r"```python\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches[0] if matches else text

def execute_code(code: str, global_context: dict) -> any:
    """执行代码并返回结果"""
    try:
        # 创建本地命名空间
        local_namespace = {}
        # 在提供的上下文中执行代码
        exec(code, global_context, local_namespace)
        # 返回最后一个赋值的变量
        return local_namespace.get('result', None)
    except Exception as e:
        return f"执行错误: {str(e)}"

def code_generator(state: GraphState) -> GraphState:
    """生成代码的节点"""
    # 系统提示词
    system_prompt = f"""你是一个Python代码生成器。基于用户的请求，生成调用本地函数的Python代码。
可用的函数如下：
{functions_schema}

生成的代码必须：
1. 使用上述函数之一或多个
2. 将最终结果赋值给名为 'result' 的变量
3. 必须是可执行的Python代码
4. 代码要简洁且高效
5. 使用markdown格式输出代码（用```python包裹）
"""
    # 用户请求
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state['request'])
    ]
    
    # 调用模型生成代码
    response = state['chat_model'].invoke(messages)
    
    # 提取代码
    generated_code = extract_python_code(response.content)
    
    # 更新状态
    state['generated_code'] = generated_code
    state['messages'] = [response]
    
    return state

def code_executor(state: GraphState) -> GraphState:
    """执行代码的节点"""
    # 准备全局上下文
    global_context = {
        'get_disk_usage': get_disk_usage,
        'scan_large_files_fast': scan_large_files_fast,
        'get_gpu_info': get_gpu_info,
        'get_process_info': get_process_info,
        'datetime': datetime,
        'json': json
    }
    
    # 执行代码
    result = execute_code(state['generated_code'], global_context)
    
    # 记录使用的函数
    used_functions = []
    for func_name in ['get_disk_usage', 'scan_large_files_fast', 'get_gpu_info', 'get_process_info']:
        if func_name in state['generated_code']:
            used_functions.append(func_name)
    
    # 更新状态
    state['execution_result'] = result
    state['used_functions'] = used_functions
    state['end_time'] = time()
    
    return state

def create_graph():
    """创建工作流图"""
    # 创建图
    builder = StateGraph(GraphState)
    
    # 添加节点
    builder.add_node("code_generator", code_generator)
    builder.add_node("code_executor", code_executor)
    
    # 设置边
    builder.set_entry_point("code_generator")
    builder.add_edge('code_generator', 'code_executor')
    builder.set_finish_point("code_executor")
    
    # 编译图
    return builder.compile()

def process_request(request: str) -> Dict:
    """处理用户请求并返回结果"""
    # 创建图
    graph = create_graph()
    
    # 准备初始状态
    state = {
        'chat_model': chat,
        'request': request,
        'messages': [],
        'generated_code': '',
        'execution_result': None,
        'used_functions': [],
        'start_time': time(),
        'end_time': 0
    }
    
    # 执行图
    final_state = graph.invoke(state)
    
    # 准备返回结果
    return {
        'request': request,
        'generated_code': final_state['generated_code'],
        'execution_result': final_state['execution_result'],
        'used_functions': final_state['used_functions'],
        'execution_time': final_state['end_time'] - final_state['start_time']
    }

if __name__ == "__main__":
    # 测试命令列表
    test_requests = [
        # 磁盘使用分析相关
        """分析所有磁盘的使用情况，重点关注使用率超过80%的分区，并列出这些分区下占用空间最大的3个目录""",
        
        """扫描 /home 目录下最近7天内创建的大文件（大于1GB），按大小降序排列，并显示文件所有者""",
        
        """找出 /var/log 目录下所有大于100MB的日志文件，并统计总共占用了多少空间""",
        
        # GPU资源分析相关
        """分析所有GPU的使用情况，找出显存占用超过4GB的进程，并显示这些进程的详细信息（命令行、运行时长等）""",
        
        """检查所有GPU的温度和风扇速度，如果温度超过80度或风扇速度超过90%，列出在该GPU上运行的所有进程""",
        
        """统计每个GPU上运行的深度学习训练进程（包含python、pytorch或tensorflow字样），计算它们的显存占用总量""",
        
        # 综合分析相关
        """全面分析系统资源：
        1. 列出所有磁盘使用率超过70%的分区
        2. 找出每个分区下最大的5个文件或目录
        3. 检查所有GPU的使用情况，包括显存占用、温度和运行进程
        4. 重点关注运行时间超过24小时的GPU进程""",
        
        """分析 /data 目录的存储情况：
        1. 统计该目录总共占用空间
        2. 列出最大的10个子目录
        3. 如果该目录下有GPU相关进程（如训练进程），显示这些进程的资源占用情况""",
        
        # 特定场景分析
        """检查深度学习训练环境：
        1. 扫描 /home/*/projects 下的模型文件（*.pt、*.pth、*.ckpt）
        2. 统计每个用户的模型文件总大小
        3. 分析当前GPU上运行的训练进程
        4. 预测剩余存储空间是否足够支撑24小时的训练""",
        
        """分析数据处理管道的资源使用：
        1. 检查 /data/pipeline 目录的存储使用情况
        2. 找出最近24小时内产生的大文件
        3. 监控数据处理相关的GPU进程
        4. 评估存储空间增长趋势"""
    ]
    
    # 运行测试
    for i, request in enumerate(test_requests, 1):
        print(f"\n=== 测试用例 {i} ===")
        print(f"请求: {request}")
        result = process_request(request)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("="*50)
