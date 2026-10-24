# ===== Builder 阶段 =====
ARG TARGETARCH
FROM harbor.gientech.com/rag-alg-service-api/alg_llm_inference_service_base:latest-${TARGETARCH} AS builder

COPY . /app/
WORKDIR /app

RUN python3 docker/setup.py build_ext --inplace &&  \
    find app -name "*.py" ! -name "__init__.py" -delete && \
    rm -rf build

# ===== Runtime 阶段 =====
ARG TARGETARCH
FROM harbor.gientech.com/rag-alg-service-api/alg_llm_inference_service_base:latest-${TARGETARCH}

WORKDIR /app
COPY --from=builder /app/ /app/

RUN python3 -m pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

CMD ["gunicorn", "-c", "gunicorn_conf.py", "llm_api_start:llm_app", "--access-logfile", "-"]
