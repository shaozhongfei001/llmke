# 该镜像需要依赖的基础镜像
FROM 10.64.7.121:30085/little_whale_ai_assistant/frontend/rag-nginx:1.0.1

# 作者
MAINTAINER ws

#将项目根目录下
COPY dist/ /usr/share/nginx/html/rag/
COPY default.conf /etc/nginx/conf.d

#指定容器的工作目录
WORKDIR /etc/nginx

#指定于外界交互的端口，即容器在运行时监听的端口
EXPOSE 80