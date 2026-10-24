#!/bin/bash

TIME_TODAY=`date +%Y%m%d`
BRANCH_NAME=`git symbolic-ref --short -q HEAD`
GIT_COMMIT_ID=`git rev-parse --short HEAD`
DOCKERFILE_PATH="docker/Dockerfile"

echo "branch name is: "$BRANCH_NAME", git commit id is: "$GIT_COMMIT_ID

# 检查分支名是否为空
if [ -z "$BRANCH_NAME" ] || [ "$BRANCH_NAME" = "HEAD" ]; then
  echo "Error: 当前分支名为空，可能是处于detached HEAD状态，请检查git仓库。"
  exit 1
fi

IMAGE_NAME="alg_llm_inference_service:${BRANCH_NAME}_${TIME_TODAY}_${GIT_COMMIT_ID}"
echo "image name is: "$IMAGE_NAME

docker build -f ${DOCKERFILE_PATH} -t ${IMAGE_NAME} .

echo "build ${IMAGE_NAME} success"

docker push ${IMAGE_NAME}

echo "push ${IMAGE_NAME} success"

# Update docker-compose.yaml with the new image
COMPOSE_FILE="../docker-compose.yaml"
if [ -f "$COMPOSE_FILE" ]; then
    echo "Updating docker-compose.yaml with new image: $IMAGE_NAME"
    sed -i.bak "s|image: alg_llm_inference_service:.*|image: $IMAGE_NAME|g" "$COMPOSE_FILE"
    echo "Updated docker-compose.yaml successfully"
else
    echo "Warning: docker-compose.yaml not found at $COMPOSE_FILE"
fi
