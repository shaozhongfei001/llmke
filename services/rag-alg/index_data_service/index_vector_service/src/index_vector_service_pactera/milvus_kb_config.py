from utils import get_config


def get_vector_dim(model_name=None):
    """
    动态获取向量维度
    
    Args:
        model_name: 模型名称，如果为None则使用配置中的默认embedding_model
    
    Returns:
        向量维度
    """
    config = get_config()
    if model_name is None:
        model_name = config.get("embedding_model")
    return config["online_embedding_model"][model_name]["dim"]


def _init_faq_fields(model_name=None):
    """初始化FAQ字段配置，根据开关动态决定是否包含question_vector字段"""
    base_fields = {
        "pk": {
            "dtype": "DataType.INT64",
            "is_primary": True,
            "auto_id": False,
            "max_length": 10000
        },
        "text": {
            "dtype": "DataType.VARCHAR",
            "max_length": 50000
        },
        "vector": {
            "dtype": "DataType.FLOAT_VECTOR",
            "dim": get_vector_dim(model_name)
        },
        "question": {
            "dtype": "DataType.VARCHAR",
            "max_length": 50000
        },
        "answer": {
            "dtype": "DataType.VARCHAR",
            "max_length": 50000
        },
        "faq_type": {
            "dtype": "DataType.INT8",
            "max_length": 50
        },
        "folder_id": {
            "dtype": "DataType.VARCHAR",
            "max_length": 466
        },
        "source": {
            "dtype": "DataType.VARCHAR",
            "max_length": 5000
        },
        "title": {
            "dtype": "DataType.VARCHAR",
            "max_length": 5000
        },
        "chunk_doc_id": {
            "dtype": "DataType.VARCHAR",
            "max_length": 5000
        },
        "document_id": {
            "dtype": "DataType.VARCHAR",
            "max_length": 5000
        },
        "file_id": {
            "dtype": "DataType.VARCHAR",
            "max_length": 50
        },
        "type": {
            "dtype": "DataType.VARCHAR",
            "max_length": 1000
        },
        "knowledge_base_name": {
            "dtype": "DataType.VARCHAR",
            "max_length": 5000
        },
        "order_num": {
            "dtype": "DataType.VARCHAR",
            "max_length": 1000
        },
        "offset": {
            "dtype": "DataType.VARCHAR",
            "max_length": 55000
        },
        "related_pk": {
            "dtype": "DataType.VARCHAR",
            "max_length": 5000
        },
        "labels": {
            "dtype": "DataType.ARRAY",
            "element_type": "DataType.VARCHAR",
            "max_capacity": 1000,
            "max_length": 55000
        },
        "status": {
            "dtype": "DataType.INT8",
            "max_length": 100
        },
        "create_time": {
            "dtype": "DataType.VARCHAR",
            "max_length": 3500
        },
        "update_time": {
            "dtype": "DataType.VARCHAR",
            "max_length": 3500
        }
    }

    # 根据开关决定是否添加question_vector字段
    enable_question_vector = get_config().get("enable_question_vector", False)
    if enable_question_vector:
        base_fields["question_vector"] = {
            "dtype": "DataType.FLOAT_VECTOR",
            "dim": get_vector_dim(model_name)
        }

    return base_fields


MILVUS_FIELDS_FAQ = _init_faq_fields()
MILVUS_FIELDS = {
    "pk": {
        "dtype": "DataType.INT64",
        "is_primary": True,
        "auto_id": False,
        "max_length": 10000
    },
    "text": {
        "dtype": "DataType.VARCHAR",
        "max_length": 50000
    },
    "vector": {
        "dtype": "DataType.FLOAT_VECTOR",
        "dim": get_vector_dim()
    },
    "source": {
        "dtype": "DataType.VARCHAR",
        "max_length": 4500
    },
    "chunk_doc_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 5500
    },
    "document_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 4500
    },
    "folder_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 466
    },
    "title": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3000
    },
    "title_path": {
        "dtype": "DataType.VARCHAR",
        "max_length": 50000
    },
    "type": {
        "dtype": "DataType.VARCHAR",
        "max_length": 5500
    },
    "offset": {
        "dtype": "DataType.VARCHAR",
        "max_length": 55000
    },
    "pic_offset_list": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.INT64",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "labels": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "position": {
        "dtype": "DataType.VARCHAR",
        "max_length": 55000
    },
    "file_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 50
    },
    "page_number": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.INT64",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "knowledge_base_name": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "file_path": {
        "dtype": "DataType.VARCHAR",
        "max_length": 35000
    },
    "image_path": {
        "dtype": "DataType.VARCHAR",
        "max_length": 35000
    },
    "file_size": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "page_size": {
        "dtype": "DataType.VARCHAR",
        "max_length": 55000
    },
    "order_num": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "chunk_index": {
        "dtype": "DataType.INT64",
        "max_length": 3500
    },
    "parent_file_name": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "revise_date": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "create_time": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "update_time": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "table_name": {
        "dtype": "DataType.VARCHAR",
        "max_length": 5001
    },
    "pic_url_list": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "pic_children_id_list": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.INT64",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "text_parent_id_list": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.INT64",
        "max_capacity": 1000,
        "max_length": 50000
    },
    "att_id": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "main_id": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    }
}

MILVUS_FIELDS_GRAPH_ENTITY = {
    "pk": {
        "dtype": "DataType.INT64",
        "is_primary": True,
        "auto_id": False,
        "max_length": 10000
    },
    "text": {
        "dtype": "DataType.VARCHAR",
        "max_length": 50000
    },
    "vector": {
        "dtype": "DataType.FLOAT_VECTOR",
        "dim": get_vector_dim()
    },
    "chunk_pk_list": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "type": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "title": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "labels": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "file_id": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "entity_type": {
        "dtype": "DataType.VARCHAR",
        "max_length": 50
    },
    "folder_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 466
    },
    "create_time": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "update_time": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    }
}
MILVUS_FIELDS_GRAPH_TRIPLES = {
    "pk": {
        "dtype": "DataType.INT64",
        "is_primary": True,
        "auto_id": False,
        "max_length": 10000
    },
    "text": {
        "dtype": "DataType.VARCHAR",
        "max_length": 50000
    },
    "vector": {
        "dtype": "DataType.FLOAT_VECTOR",
        "dim": get_vector_dim()
    },
    "chunk_pk_list": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "title": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "file_id": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "labels": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "page_num": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "source_entity": {
        "dtype": "DataType.VARCHAR",
        "max_length": 5000
    },
    "relationship": {
        "dtype": "DataType.VARCHAR",
        "max_length": 5000
    },
    "target_entity": {
        "dtype": "DataType.VARCHAR",
        "max_length": 5000
    },
    "folder_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 466
    },
    "create_time": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "update_time": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    }
}

MILVUS_FIELDS_TABLE_SUMMARY = {
    "pk": {
        "dtype": "DataType.INT64",
        "is_primary": True,
        "auto_id": False,
        "max_length": 10000
    },
    "text": {
        "dtype": "DataType.VARCHAR",
        "max_length": 50000
    },
    "vector": {
        "dtype": "DataType.FLOAT_VECTOR",
        "dim": get_vector_dim()
    },
    "source": {
        "dtype": "DataType.VARCHAR",
        "max_length": 4500
    },
    "chunk_doc_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 5500
    },
    "chunk_index": {
        "dtype": "DataType.INT64",
        "max_length": 3500
    },
    "document_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 4500
    },
    "title": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3000
    },
    "labels": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "folder_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 466
    },
    "title_path": {
        "dtype": "DataType.VARCHAR",
        "max_length": 50000
    },
    "type": {
        "dtype": "DataType.VARCHAR",
        "max_length": 5500
    },
    "offset": {
        "dtype": "DataType.VARCHAR",
        "max_length": 55000
    },
    "position": {
        "dtype": "DataType.VARCHAR",
        "max_length": 55000
    },
    "page_size": {
        "dtype": "DataType.VARCHAR",
        "max_length": 55000
    },
    "file_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 50
    },
    "page_number": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.INT64",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "knowledge_base_name": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "file_path": {
        "dtype": "DataType.VARCHAR",
        "max_length": 35000
    },
    "file_size": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "order_num": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "parent_file_name": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "revise_date": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "table_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 10000
    },
    "text_chunk_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 10000
    },
    "create_time": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "update_time": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "table_name": {
        "dtype": "DataType.VARCHAR",
        "max_length": 5001
    },
    "pic_url_list": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "pic_children_id_list": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.INT64",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "text_parent_id_list": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.INT64",
        "max_capacity": 1000,
        "max_length": 50000
    },
    "att_id": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "main_id": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    }
}

MILVUS_FIELDS_TABLE_CHUNKS = {
    "pk": {
        "dtype": "DataType.INT64",
        "is_primary": True,
        "auto_id": False,
        "max_length": 10000
    },
    "text": {
        "dtype": "DataType.VARCHAR",
        "max_length": 50000
    },
    "vector": {
        "dtype": "DataType.FLOAT_VECTOR",
        "dim": get_vector_dim()
    },
    "table_summary_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 10000
    },
    "source": {
        "dtype": "DataType.VARCHAR",
        "max_length": 4500
    },
    "chunk_doc_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 5500
    },
    "chunk_index": {
        "dtype": "DataType.INT64",
        "max_length": 3500
    },
    "document_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 4500
    },
    "folder_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 466
    },
    "title": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3000
    },
    "title_path": {
        "dtype": "DataType.VARCHAR",
        "max_length": 50000
    },
    "labels": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "type": {
        "dtype": "DataType.VARCHAR",
        "max_length": 5500
    },
    "page_size": {
        "dtype": "DataType.VARCHAR",
        "max_length": 55000
    },
    "offset": {
        "dtype": "DataType.VARCHAR",
        "max_length": 55000
    },
    "position": {
        "dtype": "DataType.VARCHAR",
        "max_length": 55000
    },
    "file_id": {
        "dtype": "DataType.VARCHAR",
        "max_length": 50
    },
    "page_number": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.INT64",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "knowledge_base_name": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "file_path": {
        "dtype": "DataType.VARCHAR",
        "max_length": 35000
    },
    "file_size": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "order_num": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "parent_file_name": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "revise_date": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "pic_url_list": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "pic_children_id_list": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.INT64",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "table_name": {
        "dtype": "DataType.VARCHAR",
        "max_length": 5001
    },
    "text_parent_id_list": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.INT64",
        "max_capacity": 1000,
        "max_length": 50000
    },
    "create_time": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "update_time": {
        "dtype": "DataType.VARCHAR",
        "max_length": 3500
    },
    "att_id": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    },
    "main_id": {
        "dtype": "DataType.ARRAY",
        "element_type": "DataType.VARCHAR",
        "max_capacity": 1000,
        "max_length": 55000
    }
}
