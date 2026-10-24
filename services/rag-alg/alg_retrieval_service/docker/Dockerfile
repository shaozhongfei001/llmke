# ===== Builder 阶段 =====
ARG TARGETARCH
FROM harbor.gientech.com/rag-alg-service-api/alg_retrieval_service_base:latest-${TARGETARCH} AS builder

WORKDIR /app

# 复制源码
COPY . /app/
WORKDIR /app

RUN python3 docker/setup.py build_ext --inplace &&  \
    find app -name "*.py" ! -name "__init__.py" -delete && \
    rm -rf build


# ===== Runtime 阶段 =====
ARG TARGETARCH
FROM harbor.gientech.com/rag-alg-service-api/alg_retrieval_service_base:latest-${TARGETARCH}

WORKDIR /app

# 复制 Builder 阶段编译好的文件
COPY --from=builder /app/ /app/

RUN python3 -m pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 设置 nacos 配置
ENV NACOS_SERVER_ADDRESS="http://10.15.12.12:8848"
ENV NAMESPACE="rag-ai-dev"
ENV DATA_ID="alg_retrieval_config_py"
ENV GROUP="DEFAULT_GROUP"

EXPOSE 19995

# 启动应用
CMD ["gunicorn", "-c", "gunicorn_conf.py", "retrieval_api_start:retriever_app", "--access-logfile", "-"]
