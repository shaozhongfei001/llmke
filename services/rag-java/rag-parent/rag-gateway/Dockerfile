# 该镜像需要依赖的基础镜像
FROM openjdk:latest

# 作者
MAINTAINER ws

ARG nacos_addr="192.168.5.116:8848"
ARG nacos_namespace="rag-dev"

ENV PARAMS=""
ENV SPRING_PROFILES_ACTIVE="cust"

ENV nacos_addr=$nacos_addr
ENV nacos_namespace=$nacos_namespace
ENV nacos_user=$nacos_user
ENV nacos_password=$nacos_password

# ENV TZ=PRC
# RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV TZ Asia/Shanghai
ADD target/rag-gateway-0.0.1-SNAPSHOT.jar /rag-gateway.jar


ENTRYPOINT ["sh","-c","java -DnacosAddr=$nacos_addr  -Dreactor.netty.pool.leasingStrategy=lifo -DnacosNamespace=$nacos_namespace -DnacosUsername=$nacos_user -DnacosPassword=$nacos_password -jar -agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=5005 $JAVA_OPTS /rag-gateway.jar $PARAMS","--spring.profiles.active=${SPRING_PROFILES_ACTIVE}"]
