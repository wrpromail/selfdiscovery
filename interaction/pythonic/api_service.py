from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from mservice import handle_query, generate_suggestions

app = FastAPI(
    title="Pythonic Service API",
    description="提供自然语言查询到Python代码的转换和执行服务",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许的前端地址，可以改为 "*" 以允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许的 HTTP 方法
    allow_headers=["*"]   # 允许的 HTTP 请求头
)


class QueryRequest(BaseModel):
    query: str
    need_suggestion: bool = False  # 默认不生成建议


class QueryResponse(BaseModel):
    execution_time: float
    response: str
    executed_functions: List[str]
    suggestion: Optional[str] = None  # 可选的建议字段


@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """
    处理用户的自然语言查询请求
    
    Args:
        request: 包含查询文本的请求体
        
    Returns:
        包含执行时间、响应文本、执行函数列表和可选建议的响应
        
    Raises:
        HTTPException: 当处理查询出错时抛出
    """
    try:
        execution_time, response, executed_functions = handle_query(request.query)

        # 如果需要生成建议
        suggestion = None
        if request.need_suggestion:
            suggestion = generate_suggestions(request.query, response)

        return QueryResponse(
            execution_time=execution_time,
            response=response,
            executed_functions=executed_functions,
            suggestion=suggestion
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"处理查询时出错: {str(e)}"
        )


@app.get("/ping")
async def ping():
    """用于健康检查的ping接口"""
    return "pong"


@app.get("/")
async def root():
    """API 服务根路径，返回简单的欢迎信息"""
    return {
        "message": "欢迎使用 Pythonic Service API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
