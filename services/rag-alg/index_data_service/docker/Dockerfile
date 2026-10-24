# ===== Builder 阶段 =====
ARG TARGETARCH
FROM harbor.gientech.com/rag-alg-service-api/index_data_service_base:latest-${TARGETARCH} AS builder

# 复制源码和 setup.py
COPY . /app/
WORKDIR /app

RUN python3 docker/setup.py build_ext --inplace


# ===== Runtime 阶段 =====
ARG TARGETARCH
FROM harbor.gientech.com/rag-alg-service-api/index_data_service_base:latest-${TARGETARCH}

WORKDIR /app

# 拷贝编译产物
COPY --from=builder /app/ /app/

RUN python3 -m pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
RUN chmod +x /app/start.sh

# 启动应用
CMD ["/app/start.sh"]
