#!/bin/bash

# 自动检测架构
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" || "$ARCH" == "aarch64" ]]; then
    ARCH_SUFFIX="arm64"
else
    ARCH_SUFFIX="amd64"
fi

DOCKERFILE_PATH="docker/Dockerfile_base"
IMAGE_NAME="harbor.gientech.com/rag-alg-service-api/index_data_service_base:latest-${ARCH_SUFFIX}"
echo "image name is: "$IMAGE_NAME

docker build -f ${DOCKERFILE_PATH} -t ${IMAGE_NAME} .
echo "build index_data_service_base image success"

docker push ${IMAGE_NAME}
echo "push index_data_service_base image success"

docker rmi ${IMAGE_NAME}
