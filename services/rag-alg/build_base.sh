#!/bin/bash

echo "Starting to build base images for all services..."

# Build alg_doc_parse_service base image
echo "Building alg_doc_parse_service base image..."
cd alg_doc_parse_service
chmod +x docker/build_base.sh
./docker/build_base.sh
if [ $? -ne 0 ]; then
    echo "Failed to build alg_doc_parse_service base image"
    exit 1
fi
cd ..

# Build alg_llm_inference_service base image
echo "Building alg_llm_inference_service base image..."
cd alg_llm_inference_service
chmod +x docker/build_base.sh
./docker/build_base.sh
if [ $? -ne 0 ]; then
    echo "Failed to build alg_llm_inference_service base image"
    exit 1
fi
cd ..

# Build alg_retrieval_service base image
echo "Building alg_retrieval_service base image..."
cd alg_retrieval_service
chmod +x docker/build_base.sh
./docker/build_base.sh
if [ $? -ne 0 ]; then
    echo "Failed to build alg_retrieval_service base image"
    exit 1
fi
cd ..

# Build index_data_service base image
echo "Building index_data_service base image..."
cd index_data_service
chmod +x docker/build_base.sh
./docker/build_base.sh
if [ $? -ne 0 ]; then
    echo "Failed to build index_data_service base image"
    exit 1
fi

cd ..

echo "All base images built and push successfully!"
