# R13 Office -> PDF 预览转换服务
# 宿主 LibreOffice 缺 writer/impress 过滤器（无 sudo 密码无法安装），故把 LibreOffice 放进容器。
# 构建：bash platform/r12/preview/run.sh build
ARG BASE_IMAGE=docker.1ms.run/library/python:3.12-slim
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    HOME=/tmp \
    SAL_USE_VCLPLUGIN=svp \
    SAL_DISABLE_OPENCL=1 \
    PORT=18095

# 基础镜像为 Debian bookworm；走国内镜像避免构建期超时（可用 --build-arg 覆盖）
ARG APT_MIRROR=mirrors.aliyun.com
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i "s|//deb.debian.org|//${APT_MIRROR}|g; s|//security.debian.org|//${APT_MIRROR}|g" \
        /etc/apt/sources.list.d/debian.sources; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        libreoffice-writer \
        libreoffice-impress \
        libreoffice-calc \
        fonts-noto-cjk \
        fonts-noto-cjk-extra \
        poppler-utils \
        fontconfig \
        ca-certificates; \
    fc-cache -f >/dev/null 2>&1 || true; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir \
      -i https://pypi.tuna.tsinghua.edu.cn/simple \
      --trusted-host pypi.tuna.tsinghua.edu.cn \
      -r /app/requirements.txt

COPY app.py /app/app.py
WORKDIR /app

EXPOSE 18095

HEALTHCHECK --interval=30s --timeout=8s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:18095/healthz',timeout=5).status==200 else 1)"

# R13-SEC-NET-01：容器内进程只绑回环（host 网络下等价于仅本机可达）。
# 若要对外提供，必须显式 -e PREVIEW_HOST=0.0.0.0 并自行加前置鉴权。
CMD ["sh", "-c", "python -m uvicorn app:app --host ${PREVIEW_HOST:-127.0.0.1} --port ${PORT:-18095} --no-access-log"]
