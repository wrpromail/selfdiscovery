from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from typing import Dict, TypedDict, Annotated, Optional
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

import time
from contextlib import contextmanager
from datetime import datetime


def get_today_date_string():
    """
    获取当天的日期字符串，格式为 "XXXX年XX月XX日"。

    返回:
        str: 格式化的日期字符串。
    """
    # 获取当前日期
    today = datetime.now()
    # 格式化日期为 "XXXX年XX月XX日"
    date_str = today.strftime("%Y年%m月%d日")
    return date_str


# 定义状态类型
class GraphState(TypedDict):
    chat_model: BaseChatModel
    valuation_date: str
    original_text: str
    revised_text: str
    messages: Annotated[list, add_messages]
    extracted_data: Dict[str, str]
    final_result: str
    additional_keys: Optional[Dict[str, str]]


asset_text_rewrite_template = """
请从评估报告文本中提取以下信息：
1. 评估对象：资产的具体名称或描述
2. 评估方法：如市场法、收益法等
3. 最终评估值：将金额转换为浮点数，单位为元，保留两位小数

按照如下格式返回（每行一个键值对）：
评估对象：xxx
评估方法：xxx
评估值：xxx.xx

注意：
- 如果文本中出现多个评估结果，请提取最终采用的评估结论
- 金额单位统一转换为元，单位若是万元，则转换成元后需要在原数值后添加 0000

输入文本：
{text}
"""


def calculator(operation: str, number1: float, number2: float):
    """执行基础数学运算，支持的运算有 add (加法), subtract (减法), multiply (乘法), divide (除法)"""
    if operation == "add":
        return number1 + number2
    elif operation == "subtract":
        return number1 - number2
    elif operation == "multiply":
        return number1 * number2
    elif operation == "divide":
        if number2 == 0:
            return '除数为0，无法计算'
        return number1 / number2
    else:
        raise ValueError(f"Unknown operation: {operation}")


def extract_valuation_conclusions(text: str) -> str:
    """
    从OCR文本中提取评估结论及其对应的金额
    Args:
        text: OCR识别得到的文本字符串
    Returns:
        包含评估结论及金额的字符串
    """
    # 输入验证
    if not isinstance(text, str) or not text.strip():
        return ""
    try:
        # 按行分割，去除空行和每行中的空格
        lines = [line.strip().replace(' ', '') for line in text.split('\n') if line.strip()]
        if not lines:
            return ""
        # 存储筛选后的结果
        selected_lines = []

        def has_number_and_yuan(line: str) -> bool:
            """检查行是否包含数字和"元"字"""
            try:
                return any(c.isdigit() for c in line) and '元' in line
            except (TypeError, AttributeError):
                return False

        # 遍历所有行
        for i, current_line in enumerate(lines):
            try:
                if '评估结论' in current_line:
                    # 情况1：当前行包含数字和"元"
                    if has_number_and_yuan(current_line):
                        selected_lines.append(current_line)
                    # 情况2：检查后续行是否包含数字和"元"
                    elif i + 2 < len(lines):
                        # 检查后两行
                        next_line = lines[i + 1]
                        next_next_line = lines[i + 2]

                        if has_number_and_yuan(next_next_line):
                            selected_lines.append(current_line)
                            selected_lines.append(next_line)
                        elif has_number_and_yuan(next_line):
                            selected_lines.append(current_line)
                            selected_lines.append(next_line)
            except Exception as e:
                print(f"处理行 {i} 时出错: {str(e)}")
                continue

        # 将筛选出的行合并为字符串
        result = '\n'.join(selected_lines) if selected_lines else ""
        return result

    except Exception as e:
        print(f"提取评估结论时出错: {str(e)}")
        return ""


def extract_data(state: GraphState):
    if not state['extracted_data']:
        state['extracted_data'] = {}

    state['extracted_data']['original_context'] = extract_valuation_conclusions(state['original_text'])
    state['extracted_data']['revised_context'] = extract_valuation_conclusions(state['revised_text'])
    # print('extracted\n')
    # print(state['extracted_data'])
    return state


def rewrite_data(state: GraphState):
    model = state['chat_model']

    def rewrite(filter_context):
        prompt = asset_text_rewrite_template.format(text=filter_context)
        return model.invoke(prompt).content

    state['extracted_data']['original_context'] = rewrite(state['extracted_data']['original_context'])
    state['extracted_data']['revised_context'] = rewrite(state['extracted_data']['revised_context'])
    return state


tools = [calculator]
sys_msg = SystemMessage(
    content="You are a helpful assistant tasked with using search and performing arithmetic on a set of inputs.")

reason_template = """## 任务背景
你是一个文本写作助手，接下来会传递两段和项目资产评估相关的文本行，请你仔细阅读提取出资产评估金额后，根据要求任务要求生成文本。

## 原始资产报告相关文本
{origin_context}
    
## 修订资产报告相关文本
{revised_context}

## 评估基准日信息
{valuation_date}

## 任务要求
1. 从文本中提取原始资产金额和修订后的资产金额。
2. {tool_prompt}
3. 请生成一句话描述修订报告相对原始报告的变化情况。需要描述评估结果变化情况、评估估值变化情况。
4. 使用"核增"或"核减"描述变化项目估值的变化情况，数值保留两位小数。如果没有变化，则指明'无增减'。
5. 注意如果数值是从 0 增加或减少到某个值，不好计算增减率，则可不描述增减率。
6. 请务必使用正式的文案描述，避免口语化的描述。

## 模板
最终审核修订后的资产评估报告于{now_date_str}(请项目经理修改)提交我公司，评估结果[是否变动]。审核修订后的资产评估报告，在评估基准日[评估基准日信息]，[目标公司全程]的股东全部权益评估价值[描述估值情况，是否变化，变化值与变化率]。
"""


def reasoner(state: GraphState):
    print("reasoner invoked")
    """推理节点的处理函数"""
    model = state['chat_model']

    if isinstance(model, ChatOllama):
        tool_prompt = "使用工具计算差值（修订金额减去原始金额）和变化率，一定注意计算变化率时被除数是否选择正确，变化率保留两位小数。"
    else:
        tool_prompt = "计算差值（修订金额减去原始金额）和变化率，一定注意计算变化率时被除数是否选择正确，变化率保留两位小数。"

    user_prompt = reason_template.format(
        origin_context=state['extracted_data'].get('original_context', ''),
        revised_context=state['extracted_data'].get('revised_context', ''),
        tool_prompt=tool_prompt,
        valuation_date=state.get('valuation_date', 'XXXX年XX月XX日'),
        now_date_str=get_today_date_string()
    )
    print(user_prompt)

    # 第一次调用模型获取计算需求
    response = state['chat_model'].invoke([sys_msg, HumanMessage(content=user_prompt)])

    # 如果需要进行工具调用
    if hasattr(response, 'tool_calls') and response.tool_calls:
        # 存储所有工具调用的结果
        tool_results = []

        # 执行每个工具调用
        for tool_call in response.tool_calls:
            print(tool_call)
            if tool_call['name'] == 'calculator':
                args = tool_call['args']  # 直接使用args字典
                result = calculator(
                    args['operation'],
                    args['number1'],
                    args['number2']
                )
                tool_results.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call['id'],
                    name='calculator'
                ))

        # 将工具调用结果添加到消息历史
        messages = [response] + tool_results

        # 再次调用模型生成最终结果
        final_response = state['chat_model'].invoke([
            sys_msg,
            HumanMessage(content=user_prompt),
            *messages
        ])

        # 设置最终结果
        state["final_result"] = final_response.content
        state['messages'] = messages + [final_response]
        print(state['messages'])
    else:
        # 如果不需要工具调用，直接使用响应作为最终结果
        state["final_result"] = response.content
        state['messages'] = [response]

    return state


def process_result(state: GraphState) -> GraphState:
    """
    处理最终结果的节点
    1. 从对话历史中提取最终的分析结果
    2. 格式化并存储结果
    """
    messages = state["messages"]

    # 获取最后一条非工具消息作为最终结果
    final_message = None
    for message in reversed(messages):
        if hasattr(message, 'content') and message.content:
            final_message = message.content
            break

    # 存储最终结果
    state["final_result"] = final_message

    return state


clean_prompt = """
## 任务背景
你是一个文本处理助手，根据输入的文本与要求，生成符合要求的数据。

## 任务要求
1. 接下来输入的文本是某个任务通过大模型处理后的得到的文本，因为其中包含计算等过程，生成的内容可能并不规范。
2. 比如会有注释、计算逻辑介绍等无关内容。
3. 请仔细阅读后，去除所有无关内容，只保留一段话描述 最终报告提交时间、评估结果是否变动、在基准日目标的股东全部权益评估价值的变化情况（数值与变化率）。
4. 请务必生成正式、专业的文本，避免口语化表达，不要解释修订目的等。
5. 并且还会给你额外补充一些内容，是评估报告的评估目的和评估对象，这些信息中可能包含了被审计公司更为完整的名称，如果你认为比原文本中的名称更为正式，请使用你的提取结果。
6. 请将涉及金额的部分，单位修改为万元，并且每隔三位数字加一个逗号。

## 额外内容
{additional_keys}

## 输入文本
{raw_content}

"""


def post_cleaning(state: GraphState) -> GraphState:
    final_message = state.get("final_result", None)
    if not final_message:
        pass
    model = state['chat_model']
    additional_keys = state.get('additional_keys', None)
    if additional_keys:
        additional_keys = '\n'.join([f"{value}" for key, value in additional_keys.items()])
    else:
        additional_keys = ""

    state["final_result"] = model.invoke(clean_prompt.format(raw_content=final_message,
                                                             additional_keys=additional_keys)).content

    return state


def route_message(state: GraphState) -> str:
    """
    路由控制函数
    决定是继续工具调用还是进入结果处理
    """
    # 如果已经有最终结果，进入结果处理
    if state.get("final_result"):
        return "process_result"

    # 所有其他情况结束
    return END


# 创建图并添加节点
builder = StateGraph(GraphState)
builder.add_node("start", extract_data)
builder.add_node("rewrite", rewrite_data)
builder.add_node("reasoner", reasoner)
builder.add_node("tools", ToolNode(tools))
builder.add_node("process_result", process_result)
builder.add_node("post_cleaning", post_cleaning)

# 添加边和条件
builder.add_edge(START, "start")
builder.add_edge("start", "rewrite")
builder.add_edge("rewrite", "reasoner")
builder.add_conditional_edges(
    "reasoner",
    route_message,
    {
        "tools": "tools",
        "process_result": "process_result",
        END: END
    }
)
builder.add_conditional_edges(  # 修改这里，为 tools 节点添加条件边
    "tools",
    route_message,
    {
        "tools": "tools",
        "process_result": "process_result",
        END: END
    }
)
builder.add_edge("process_result", "post_cleaning")
builder.add_edge("post_cleaning", END)

# 编译图
graph = builder.compile()


@contextmanager
def task_timer(task_name: str):
    """计时器上下文管理器"""
    print(f"Starting {task_name}")
    start_time = time.time()
    try:
        yield
    finally:
        elapsed = (time.time() - start_time) * 1000
        print(f"Completed {task_name} in {elapsed:.2f}ms")


def extract_shareholder_info(text):
    # 将文本按行分割
    lines = text.split('\n')

    # 存储结果
    results = []

    # 遍历所有行
    for i in range(len(lines)):
        # 检查当前行是否包含关键字
        if '股东名称' in lines[i]:
            # 提取当前行及后续4行
            # 使用min确保不会超出文本总行数
            extract = lines[i:min(i + 5, len(lines))]
            results.extend(extract)
            # 添加一个空行作为不同部分的分隔
            results.append('')

    return results


def asset_value_compare(task_id: str, valuation_date: str, model: BaseChatModel,
                        original_text: str, revise_text: str, logger=None, **additional_keys):
    if isinstance(model, ChatOllama):
        llm_with_tools = model.bind_tools(tools)
    else:
        llm_with_tools = model

    initial_state = {
        'valuation_date': valuation_date,
        'original_text': original_text,
        'revised_text': revise_text,
        'chat_model': llm_with_tools,
        'messages': [],  # 添加空的消息列表
        'extracted_data': {},  # 添加空的提取数据字典
        'final_result': "",  # 添加空的最终结果字符串
        'additional_keys': additional_keys
    }
    result_dict = {'asset_value_compare': graph.invoke(initial_state).get('final_result', '')}
    return result_dict


if __name__ == "__main__":
    ollama_model = ChatOllama(model='qwen2.5:14b')

    big_model = {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": "b144d56dad6a10f8cb66c0ce43e8af40.lioxu3uoIRHf80GY",
        "model": "glm-4-air",  # 可以先使用 glm-4-flash\ glm-4-0520 \ glm-4-plus 做验证
        "temperature": 0.1,
    }
    chat_model = ChatOpenAI(**big_model)

    from src.asset_valuation_review.entity_agent.sample import revise_report, final_report

    print(asset_value_compare('test', 'xx年xx月xx日', ollama_model, revise_report, final_report,
                              rated_purpose='为兰州原子高科医药有限公司拟减资行为提供价值参考依据',
                              rated_object='兰州原子高科医药有限公司的股东全部权益'))
