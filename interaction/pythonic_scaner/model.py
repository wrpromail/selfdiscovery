from langchain_openai import ChatOpenAI


codegeex_private_32b = {
    'base_url': 'http://36.103.234.69:28080/chat_lb_32b/v1',
    'model': 'codegeex4_32b',
    'temperature': 0.2,
    'api_key': 'codegeex4_32b'
}

glm4 = {
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "api_key": "b144d56dad6a10f8cb66c0ce43e8af40.lioxu3uoIRHf80GY",
    "model": "glm-4-air",
    "temperature": 0.2,
}

# 阿里云qwen无法持续调用
qwen_25_coder = {
    'api_key': 'sk-960782c2acab4e16bcb39c8730859e21',
    'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'model': 'qwen-coder-plus-latest',
}

deepseek = {
    'api_key': 'sk-af118cf1f96c47c1810f124156ae712a',
    'base_url': 'https://api.deepseek.com/v1',
    'model': 'deepseek-chat', # v3
}

openai_proxy = {
    'api_key': 'sk-Pz5xqVUDIFkUiqIq1e4GJToEFpAcSTmoA6M8oTypKfNogQzD',
    'base_url': 'https://api.oaipro.com/v1',
    'model': 'gpt-4o-mini'
}


hunyuan_model = {
    'base_url': 'https://api.hunyuan.cloud.tencent.com/v1',
    'api_key': 'sk-v4TkoB14DVCAN3am8CkHERzXLvuEl743uEA3mc1ruFNKChMW',
    'model': 'hunyuan-code',

}


chat = ChatOpenAI(**codegeex_private_32b)
suggest = ChatOpenAI(**glm4)