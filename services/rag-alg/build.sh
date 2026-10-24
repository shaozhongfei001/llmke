#!/bin/bash

# 统一构建脚本 - 可以在根目录运行
# 用法: ./build.sh [service_name]
# 如果不指定service_name，会构建所有服务

TIME_TODAY=`date +%Y%m%d`
# 获取当前分支名
BRANCH_NAME="dev"
VERSION="v2.1.0"

echo "Branch name is: $BRANCH_NAME"

if [ -z "$BRANCH_NAME" ]; then
  echo "Error: Branch name is empty. Exiting."
  exit 1
fi

GIT_COMMIT_ID=`git rev-parse --short HEAD`

echo "Branch name: $BRANCH_NAME, Git commit id: $GIT_COMMIT_ID"

# 自动检测架构
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" || "$ARCH" == "aarch64" ]]; then
    ARCH_SUFFIX="arm64"
else
    ARCH_SUFFIX="amd64"
fi

TAG_SUFFIX="${BRANCH_NAME}_${TIME_TODAY}_${GIT_COMMIT_ID}_${VERSION}-${ARCH_SUFFIX}"

built_images=()
# 服务配置
services="alg_doc_parse_service alg_llm_inference_service alg_retrieval_service index_data_service"

# 如果指定了服务名，只构建该服务
if [ $# -eq 1 ]; then
    services=$1
fi

# 构建函数
build_service() {
    local service=$1
    local dockerfile_path="${service}/docker/Dockerfile"
    local build_context="${service}"

    # 根据服务名设置镜像名
    case $service in
        "alg_doc_parse_service")
            IMAGE_NAME="harbor.gientech.com/rag-alg-service-api/alg_doc_parse_service:${TAG_SUFFIX}"
            COMPOSE_IMAGE_PATTERN="alg_doc_parse_service"
            ;;
        "alg_llm_inference_service")
            IMAGE_NAME="harbor.gientech.com/rag-alg-service-api/alg_llm_inference_service:${TAG_SUFFIX}"
            COMPOSE_IMAGE_PATTERN="alg_llm_inference_service"
            ;;
        "alg_retrieval_service")
            IMAGE_NAME="harbor.gientech.com/rag-alg-service-api/alg_retrieval_service:${TAG_SUFFIX}"
            COMPOSE_IMAGE_PATTERN="alg_retrieval_service"
            ;;
        "index_data_service")
            IMAGE_NAME="harbor.gientech.com/rag-alg-service-api/index_data_service:${TAG_SUFFIX}"
            COMPOSE_IMAGE_PATTERN="index_data_service"
            ;;
        *)
            echo "Unknown service: $service"
            return 1
            ;;
    esac

    echo "Building $service..."
    echo "Dockerfile: $dockerfile_path"
    echo "Build context: $build_context"
    echo "Image name: $IMAGE_NAME"

    # 检查Dockerfile是否存在
    if [ ! -f "$dockerfile_path" ]; then
        echo "Error: Dockerfile not found at $dockerfile_path"
        return 1
    fi

    # 构建镜像
    DOCKER_BUILDKIT=0 docker build --pull -f "$dockerfile_path" --build-arg TARGETARCH=${ARCH_SUFFIX} -t "$IMAGE_NAME" "$build_context"

    # docker build -f "$dockerfile_path" -t "$IMAGE_NAME" "$build_context"
    # docker build --no-cache -f "$dockerfile_path" -t "$IMAGE_NAME" "$build_context"

    if [ $? -eq 0 ]; then
        echo "Build successful for $service: $IMAGE_NAME"

        # 更新 docker-compose.yaml
        if [ -f "docker-compose.yaml" ]; then
            echo "Updating docker-compose.yaml for service $service with new image: $IMAGE_NAME"

            # 使用 awk 或 sed 精确替换该服务下的 image
            awk -v svc="$service" -v img="$IMAGE_NAME" '
            $0 ~ "^[[:space:]]*"svc":" {in_service=1}
            in_service && $0 ~ "^[[:space:]]*image:" {sub(/image:.*/, "image: " img); in_service=0}
            {print}
            ' docker-compose.yaml > docker-compose.tmp && mv docker-compose.tmp docker-compose.yaml

            echo "Updated docker-compose.yaml successfully"
        else
            echo "Warning: docker-compose.yaml not found"
        fi

         docker push "$IMAGE_NAME"
        if [ $? -eq 0 ]; then
            echo "$IMAGE_NAME pushed successfully."
             docker rmi "$IMAGE_NAME" || echo "Warning: failed to remove local image $IMAGE_NAME"
        else
            echo "Failed to push image $IMAGE_NAME"
            exit 1
        fi

        built_images+=("$IMAGE_NAME")
    else
        echo "Build failed for $service"
        return 1
    fi

}

# 构建服务
for service in $services; do
    if [ -d "$service" ]; then
        build_service "$service"
        if [ $? -ne 0 ]; then
            echo "Failed to build $service"
            exit 1
        fi
    else
        echo "Service directory not found: $service"
        exit 1
    fi
done

echo "All builds completed successfully!"
echo "Built and pushed images:"
for img in "${built_images[@]}"; do
    echo "  - $img"
done
