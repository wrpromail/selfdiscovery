## pythonic 函数调用
由 https://github.com/karminski/one-small-step/blob/main/20250117-what-is-pythonic-function-call/what-is-pythonic-function-call.md 启发
通过让模型直接生成 python 代码来实现函数调用

### 描述
1. 小尺寸模型通常只能应用于简单的函数调用场景，特别函数之间关联性不强
2. 多个工具并行调用涉及客户端和模型的多次通信，延迟可能较高

### 注意事项
model.py 文件未上传，里面是模型配置
mservice.py 是移动客服查询场景的模拟函数
pythonic.py 是航空订票场景的模拟函数



### 探索列表
#### 并发调用函数
#### 部分并发调用函数
#### 函数之间有一定依赖关系
#### 对函数理解上限
#### 安全控制
#### 不同模型效果、性能评估