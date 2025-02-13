# 使用阿里云镜像并采用多阶段构建
FROM registry.cn-beijing.aliyuncs.com/wrrepo/python:3.12.8-slim AS builder

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    sed -i 's@deb.debian.org@mirrors.aliyun.com@g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev vim && \
    python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    python -m pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 使用阿里云镜像
FROM registry.cn-beijing.aliyuncs.com/wrrepo/python:3.12.8-slim

# 设置工作目录
WORKDIR /app

# 修正Python版本路径和bin路径
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    sed -i 's@deb.debian.org@mirrors.aliyun.com@g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl telnet vim && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 复制所有Python文件
COPY *.py /app/

# 设置目录权限
RUN chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "api_service:app", "--host", "0.0.0.0", "--port", "8000"]
