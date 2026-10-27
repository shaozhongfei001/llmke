from retrieval_service import *
from retrieval_fun_tool import PROVENANCE_FIELDS, provenance_of
from utils import create_uuid, return_nacos_model

TABLE_CHUNKS_INDEX_TEMPLATE = "table_chunks_{}"
TABLE_SUMMARY_INDEX_TEMPLATE = "table_summary_{}"


async def retrieve_table_chunks(question, knowledge_base_name, top_k, server_config, document_id=None, verify_queries=None):
    """
    多路召回
    :param question: 用户初始问题
    :param knowledge_base_name: 知识库名称
    :param top_k: 返回个数
    :param server_config: 配置
    :param verify_queries: query重改后的结果，COVE
    :return: 多路召回的结果
    """
    documents = []
    verify_queries.append(question)
    table_chunk_list = [TABLE_CHUNKS_INDEX_TEMPLATE.format(kn) for kn in knowledge_base_name]
    tasks = [multiple_retrieval(query, table_chunk_list, top_k, server_config, document_id) for query in
             verify_queries]
    results = await asyncio.gather(*tasks)

    if results:
        for docs in results:
            documents.extend(docs)
    return documents


async def retrieve_table_summary(question, knowledge_base_name, server_config, top_k=1, score_threshold=0.8, verify_queries=None):
    """
    召回表格摘要
    """
    documents = []

    questions = [question]
    if verify_queries:
        questions.extend(verify_queries)

    table_summary_names = [TABLE_SUMMARY_INDEX_TEMPLATE.format(kn) for kn in knowledge_base_name]
    tasks = [multiple_retrieval(query, table_summary_names, top_k, server_config) for query in questions]
    results = await asyncio.gather(*tasks)
    # 处理验证查询的结果
    # 文档版本管理筛选
    if results:
        for docs in results:
            documents.extend(docs)
    print(documents)
    # external_pk = create_uuid()
    # log_list = og_process(external_pk, question, documents, server_config)
    log_list = []

    # todo 这里的log如何添加？
    documents = await merge_and_rerank(question, documents, top_k, score_threshold, server_config, log_list)
    return documents


async def table_multiple_retrieval_documents(qa_model: QARetrieveConfig):
    """
    多路召回检索服务
    :param qa_model:参数对象
    :return: 检索结果
    """
    log_list = []
    queries = []
    documents_list = []
    print("开始召回")
    server_config = return_nacos_model().get_config()

    if server_config["query_enrich"]:
        queries = await split_query(qa_model.query, qa_model.model_name, server_config)  # 回答修正，模型给出其他问题，query扩展和分布
        # cove_queries = await factored_chain_of_verification(qa_model.query, qa_model.model_name, server_config)  # 回答修正，模型给出其他问题，query扩展和分布
        # queries.extend(cove_queries)

    table_summary, log_list = await retrieve_table_summary(qa_model.query, qa_model.knowledge_base_name, server_config, verify_queries=queries)
    if table_summary:
        # 触发表格索引
        table_pk = table_summary[0].metadata["pk"]
        print(table_pk, table_summary[0].page_content)

        return BaseResponse(code=200, msg=f'查询成功', data={"documents_list": documents_list, "log_list": log_list})

    documents = await retrieve_table_chunks(qa_model.query,
                                     qa_model.knowledge_base_name,
                                     qa_model.top_k,
                                     server_config,
                                     verify_queries=queries)
    print(f"共召回：{len(documents)}条数据")
    documents_list_new = []
    if documents:
        documents = merge_and_get_rrf_score(qa_model.query, documents)
        external_pk = create_uuid()
        log_list = og_process(external_pk, qa_model.query, documents, server_config)

        documents, log_list = await merge_and_rerank(qa_model.query, documents, qa_model.top_k,
                                                     qa_model.score_threshold,
                                                     server_config, log_list)

        # documents_list = [dict(x) for x in documents if "answer" not in x.metadata.keys()]
        documents_list = [dict(x) for x in documents]

        print(f"多路合并排序完成")
        for x in documents_list:
            if "document_id" not in x["metadata"].keys():
                x["metadata"]["document_id"] = ""
            # R14-B6：这里原先是**四键白名单**（source/id/search_type/offset），
            # 把上游带来的溯源字段整批丢掉，导致下游只能靠 `pk ∩ ES._id` 反推，
            # 读 provenance_quality 会得到"假红"。改为在保留原四键的基础上**透传溯源字段**，
            # 缺省为 None（键始终存在，便于用 in 判支持、用值判是否兜底）。
            _md = x["metadata"]
            dict_new = {"page_content": x["page_content"],
                        "metadata": {"source": _md.get("source"),
                                     "id": _md.get("document_id"),
                                     "search_type": _md.get("search_type"),
                                     "offset": _md.get("offset", None),
                                     **provenance_of(_md, x),
                                     "chunk_index": _md.get("chunk_index"),
                                     "title": _md.get("title"),
                                     },
                        "type": x["type"],
                        "order_num": str(create_uuid()),
                        "faq_answer": x["metadata"].get("answer", None),
                        "id": x["metadata"]["document_id"],
                        "score": x["metadata"]["score"]
                        }
            documents_list_new.append(dict_new)
        documents_list_new = sorted(documents_list_new, key=lambda x: x["score"], reverse=True)[:qa_model.top_k]
    return BaseResponse(code=200, msg=f'查询成功', data={"documents_list": documents_list_new, "log_list": log_list})