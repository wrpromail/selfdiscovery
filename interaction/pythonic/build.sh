#!/bin/bash

# 设置 Docker 构建平台为 linux/amd64
export DOCKER_DEFAULT_PLATFORM=linux/amd64

# 生成时间戳标签 (YYYYMMDDHHMM 格式)
TAG=$(date +"%Y%m%d%H%M")

# 构建镜像
docker build \
  --platform linux/amd64 \
  -t pythonic-service:${TAG} \
  .

echo "Image built successfully: pythonic-service:${TAG}"
