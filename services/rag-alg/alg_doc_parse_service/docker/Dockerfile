ARG TARGETARCH
FROM harbor.gientech.com/rag-alg-service-api/alg_doc_parse_service_base:latest-${TARGETARCH}

RUN rm -rf /workdir && mkdir /workdir

COPY . /workdir
WORKDIR /workdir

# 注意 deepdoc/huqie 文件复制进来
RUN cp /root/huqie.txt deepdoc/huqie.txt && \
    cp /root/huqie.txt.trie deepdoc/huqie.txt.trie && \
    pip install --no-cache-dir -r requirements.txt && \
    python3 docker/setup.py build_ext --inplace

CMD ["gunicorn", "-c", "gunicorn_conf.py", "server.controller:app", "--access-logfile", "-"]
