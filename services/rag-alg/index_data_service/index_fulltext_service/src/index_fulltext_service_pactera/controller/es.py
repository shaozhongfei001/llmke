#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: es.py
Time: 2025/12/16 15:23

ES 相关的异步控制逻辑：
- 异步批量插入文档
- 分批、并发控制
- 限流与重试
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import List, Tuple, Set

from elasticsearch.helpers import async_bulk

from base import BaseResponse, InsertDataModel, CreateIndexModel, OperateDataModel
from controller.es_query import query_es_sql
from controller.query_type import QueryType
from es_kb_config import (
    ES_INDEX_MAPPING,
    ES_INDEX_MAPPING_SUMMARY,
    ES_INDEX_MAPPING_CHUNKS,
    ES_INDEX_MAPPING_DATABASE,
)
from operators.common.log import logger
from utils import return_nacos_model, create_uuid


COMMUNITY_INDEX_PREFIX = "community_summary_"


def derive_doc_id(*parts) -> int:
    """R14-A：由给定字符串派生稳定的 63 位正整数主键（与 index_vector 侧同一算法，改一处必须同步另一侧）。

    用途：让"同一份解析结果重放"落到同一条记录上（ES `_id` 与 Milvus `pk` 取值一致），
    使重复事件幂等、旧引用不会因为重写而无声失效。
    """
    seed = "|".join("" if p is None else str(p) for p in parts)
    return int(hashlib.sha1(seed.encode("utf-8")).hexdigest()[:15], 16)


def community_doc_id(index_name, metadata) -> int:
    """R14-A：社区摘要的确定性主键 = f(kb, level, community_id)。

    R13 实测：社区摘要两侧主键都是随机 uuid，重跑一次就是一代新行，ES 7 条 / Milvus 65 条。
    社区逻辑身份由 community_id 承载，主键必须跟它一一对应，才能"按 community_id 去重/覆盖"。
    """
    return derive_doc_id("community", index_name, (metadata or {}).get("level"),
                         (metadata or {}).get("community_id"))


def is_index_lower(index_name):
    """将大写索引名转小写"""
    if isinstance(index_name, list):
        index_name = [name.lower() for name in index_name]
    else:
        if any(name.isupper() for name in index_name):
            index_name = index_name.lower()
    return index_name


async def is_index_async(index_name) -> bool:
    es = return_nacos_model().es_client_async()
    return await es.indices.exists(index=index_name)


async def create_index_async(index_model: CreateIndexModel) -> BaseResponse:
    index_name = is_index_lower(index_model.index_name)
    if "table_summary_" in index_name:
        body = ES_INDEX_MAPPING_SUMMARY
    elif "table_chunks_" in index_name:
        body = ES_INDEX_MAPPING_CHUNKS
    elif "database_" in index_name:
        body = ES_INDEX_MAPPING_DATABASE
    else:
        body = index_model.mapping_body or ES_INDEX_MAPPING
    es = return_nacos_model().es_client_async()
    if not await is_index_async(index_name):
        try:
            await es.indices.create(index=index_name, body=body)
            logger.info(f'索引{index_name}创建成功')
            return BaseResponse(code=200, msg=f'索引{index_name}创建成功')
        except Exception as ex:
            logger.error(f'索引{index_name}创建失败,{ex}')
            return BaseResponse(code=500, msg=f'索引{index_name}创建失败,{ex}')
    else:
        logger.error(f'索引{index_name}已存在')
        return BaseResponse(code=500, msg=f'索引{index_name}已存在')


async def get_index_mapping_field_async(index_name) -> Tuple[List[str], List[str]]:
    """
    获取当前 index 的 mapping 字段，如果索引不存在则按配置自动创建。
    返回:
        s_field_names: mappings-properties 顶层字段
        m_field_names: metadata-properties 字段
    """
    s_field_names: List[str] = []
    m_field_names: List[str] = []
    index_name = is_index_lower(index_name)
    es = return_nacos_model().es_client_async()
    if not await is_index_async(index_name):
        index_model = CreateIndexModel(index_name=index_name)
        data = await create_index_async(index_model)
        if data.code == 500:
            # R14-A-FIX-27：**并发创建同名索引是常态**（多篇文件同时首次入库），不是失败。
            # 原实现把 400 resource_already_exists 当异常抛出 -> 整批 insert 返回 500 ->
            # 上层 /parse_sync 仍 success=true -> 用户看到"解析成功但零写入"。实测 kb_22 三篇并发即命中。
            _msg = str(data.msg)
            # 注意 create_index_async 有两条"已存在"路径：ES 抛的英文异常、以及它自己的中文 '已存在' 分支。
            if ('resource_already_exists' in _msg or 'already_exists' in _msg
                    or '已存在' in _msg):
                logger.warning(f'索引 {index_name} 已被并发创建（资源已存在），继续取 mapping')
            else:
                raise ValueError(data.msg)
    # ES 建索引有刷新延迟：刚建好/被并发建好后立刻取 mapping 可能 404，重试几次再判失败。
    mapping = None
    _last_ex = None
    for _attempt in range(3):
        try:
            mapping = await es.indices.get_mapping(index=index_name)
            break
        except Exception as ex:  # noqa: BLE001
            _last_ex = ex
            await asyncio.sleep(0.5 * (_attempt + 1))
    if mapping is None:
        raise ValueError(f'索引 {index_name} 已创建但取不到 mapping: {_last_ex}')
    if mapping and index_name in mapping:
        mapping_properties = mapping[index_name]['mappings']['properties']
        for field_name, field_mapping in mapping_properties.items():
            s_field_names.append(field_name)
            if field_name == 'metadata':
                for f, v in field_mapping['properties'].items():
                    m_field_names.append(f)
    return s_field_names, m_field_names


def build_actions(insert_model: InsertDataModel, s_field_names, index_name) -> Tuple[list, Set[str]]:
    """
    构造文档逻辑，生成 bulk action 列表和 source 去重集合。
    """
    data_list = []
    source_paths: Set[str] = set()

    def build_columns_data(columns):
        columns_page_content = ""
        for column in columns:
            sample_values = " ".join(column.get("sample_values"))
            columns_page_content = columns_page_content + f"""
                                字段中文名称:{column.get("business_name", "")}
                                字段:{column.get("physical_name", "")}
                                字段描述:{column.get("description", "")}
                                字段采样值:{sample_values}
                                字段类型:{column.get("data_type", "")}
                                """
        return columns_page_content

    def build_database_content():
        if len(insert_model.document_list) > 0:
            data_dict = insert_model.document_list[0]
            columns = build_columns_data(data_dict.get("columns", []))
            columns_json = json.dumps(data_dict)
            page_content = f"""
                    表中文名称:{data_dict.get("database_name", "")}
                    表名称:{data_dict.get("physical_name", "")}
                    表描述:{data_dict.get("database_description", "")}
                    表字段信息:{columns}
                    """
            return page_content, columns_json
        else:
            return None, None

    if insert_model.type == "database":
        if len(insert_model.document_list) > 0:
            doc_dict = insert_model.document_list[0]
            doc_keys = doc_dict.keys()
            ids = create_uuid()
            actions_dict = {
                '_index': index_name,
                "_id": ids,
                '_source': {"page_content": "", "metadata": {}}
            }
            page_content, columns_json = build_database_content()
            for sf in s_field_names:
                if sf == 'page_content':
                    actions_dict['_source'][sf] = page_content
                elif sf == 'metadata':
                    for f, v in doc_dict.items():
                        if f == "columns":
                            actions_dict['_source'][sf][f] = columns_json
                        else:
                            actions_dict['_source'][sf][f] = v
                else:
                    if sf in doc_keys:
                        actions_dict['_source'][sf] = doc_dict[sf]
            now = datetime.now()
            if "create_time" not in actions_dict['_source']['metadata'].keys():
                actions_dict['_source']['metadata']["create_time"] = now.strftime(
                    "%Y-%m-%d %H:%M:%S.") + f"{now.microsecond:06d}"
            if "update_time" not in actions_dict['_source']['metadata'].keys():
                actions_dict['_source']['metadata']["update_time"] = now.strftime(
                    "%Y-%m-%d %H:%M:%S.") + f"{now.microsecond:06d}"
            # R14-A：database 类文档仍是随机 id（未纳入内容寻址），如实标注来源
            actions_dict['_source']['metadata']["id_origin"] = "random"
            data_list.append(actions_dict)
    else:
        for doc_dict in insert_model.document_list:
            doc_keys = doc_dict.keys()
            meta = doc_dict["metadata"]
            if meta.get("pk"):
                ids = meta["pk"]
                id_origin = "pk_from_caller"
            elif index_name.startswith(COMMUNITY_INDEX_PREFIX) and meta.get("community_id"):
                # R14-A：社区摘要主键由 (kb, level, community_id) 派生，重跑同一社区覆盖同一条
                ids = community_doc_id(index_name, meta)
                id_origin = "derived_community"
            elif (not index_name.startswith("faq_") and meta.get("document_id")
                  and (meta.get("parsed_chunk_index") is not None or meta.get("chunk_index") is not None)):
                # R14-A/F04：内容寻址主键。同一文件同一块的重复解析落到同一条，图侧 chunk_pk_list
                # 不再因为"重写一次就换一代 id"而无声悬空；内容或 file_id 变化才产生新 id。
                # 序号优先取 parsed_chunk_index（解析全序，controller.py:405 赋值、linking 之前就可用），
                # 缺失才退回 chunk_index（解析末尾重编号，controller.py:646）——必须与解析服务 pk 派生同字段。
                _seq = meta.get("parsed_chunk_index")
                if _seq is None:
                    _seq = meta.get("chunk_index")
                # R14-A-FIX-18：种子**不含 document_id**。document_id 由调用方传入的路径形态决定
                # （`r12-rag/kb_9/.../V1/x.docx` vs `x.docx`），同一文件同内容换个入口解析就会换一代 id，
                # 图侧 chunk_pk_list 立刻悬空。改用 file_id（缺失时退回 title）+ 序号 + 内容哈希。
                _fid = meta.get("file_id")
                if _fid in (None, ""):
                    _fid = meta.get("title")
                ids = derive_doc_id("chunk", index_name, _fid, _seq,
                                    hashlib.sha1(doc_dict["page_content"].encode("utf-8")).hexdigest())
                id_origin = "derived_parsed_chunk_index" if meta.get("parsed_chunk_index") is not None else "derived_chunk_index"
            else:
                ids = create_uuid()
                id_origin = "random"
            actions_dict = {
                '_index': index_name,
                "_id": ids,
                '_source': {"page_content": "", "metadata": {}}
            }
            for sf in s_field_names:
                if sf == 'page_content':
                    actions_dict['_source'][sf] = doc_dict['page_content']
                elif sf == 'metadata':
                    for f, v in doc_dict['metadata'].items():
                        if f in ('order_num', "status"):
                            actions_dict['_source'][sf][f] = int(v)
                        else:
                            actions_dict['_source'][sf][f] = v
                else:
                    if sf in doc_keys:
                        actions_dict['_source'][sf] = doc_dict[sf]
            meta_q = doc_dict.get('metadata', {}).get('question')
            if meta_q:
                actions_dict['_source']['question'] = meta_q
            if "status" not in doc_dict['metadata'].keys():
                actions_dict['_source']['metadata']["status"] = 0
            # R14-A：把"这个 _id 是怎么来的"写在写入点（唯一知情处），供图/审计侧判定
            # provenance，避免下游靠重算哈希去猜（猜错就会出现"两个都合法"的 id）。
            actions_dict['_source']['metadata']["id_origin"] = id_origin
            if "pk" not in doc_dict['metadata'].keys():
                actions_dict['_source']['metadata']["pk"] = ids
            now = datetime.now()
            if "create_time" not in actions_dict['_source']['metadata'].keys():
                actions_dict['_source']['metadata']["create_time"] = now.strftime(
                    "%Y-%m-%d %H:%M:%S.") + f"{now.microsecond:06d}"
            if "update_time" not in actions_dict['_source']['metadata'].keys():
                actions_dict['_source']['metadata']["update_time"] = now.strftime(
                    "%Y-%m-%d %H:%M:%S.") + f"{now.microsecond:06d}"
            source_path = actions_dict["_source"]["metadata"].get("source")
            if source_path:
                source_paths.add(source_path)
            data_list.append(actions_dict)
    return data_list, source_paths


async def delete_by_col_documents_async(operate_data: OperateDataModel) -> BaseResponse:
    """
    根据条件删除数据，供大批量写入前去重使用。
    """
    es = return_nacos_model().es_client_async()
    index_name = is_index_lower(operate_data.index_name)

    if not await is_index_async(index_name):
        logger.info(f'es索引{index_name}不存在，无需删除数据')
        return BaseResponse(code=200, msg=f'索引{index_name}不存在，无需删除数据')

    query_param_list = []
    try:
        if operate_data.col_name:
            query_param = query_es_sql(index_name, operate_data.col_name, operate_data.col_values, QueryType.METADATA)
            query_param_list.append(query_param)
        elif operate_data.condition_json:
            for con_dict in operate_data.condition_json:
                for col_name in con_dict:
                    col_values = con_dict[col_name]
                    query_param = query_es_sql(index_name, col_name, col_values, QueryType.METADATA)
                    query_param_list.append(query_param)
        else:
            return BaseResponse(code=500, msg=f'并没有传入删除条件，如果想删除该index，请调用删除index接口')
    except Exception as ex:
        logger.info(f'索引{index_name}构建查询条件失败,没有查到该条件下的数据,{ex}')
        return BaseResponse(code=500, msg=f'索引{index_name}构建查询条件失败, 没有查到该条件下的数据,{ex}')

    total_deleted = 0
    for query_param in query_param_list:
        delete_body = {'query': query_param}
        try:
            response = await es.delete_by_query(index=index_name, body=delete_body, refresh=True)
            deleted_count = response["deleted"]
            total_deleted += deleted_count
            logger.info(f'Deleted {deleted_count} documents.')
        except Exception as ex:
            logger.error(f'索引{index_name}删除失败,{ex}')
            return BaseResponse(code=500, msg=f'索引{index_name}删除失败,{ex}')

    if query_param_list:
        if total_deleted == 0:
            logger.info(f'索引{index_name}没有查到要删除的数据')
            return BaseResponse(code=200, msg=f'索引{index_name}没有查到要删除的数据',
                                data={"result_data": operate_data.col_values})
        else:
            return BaseResponse(code=200, msg=f'成功删除{total_deleted}条数据',
                                data={"result_data": operate_data.col_values})


async def _insert_batch_with_retry(
        es,
        batch,
        sem: asyncio.Semaphore,
        index_name: str,
        batch_no: int,
        max_retries: int,
) -> List[str]:
    attempt = 0
    last_err = None
    while attempt < max_retries:
        attempt += 1
        try:
            async with sem:
                success_count, errors = await async_bulk(
                    es, batch, refresh=False, raise_on_error=False
                )
            if errors:
                last_err = errors
                logger.error(f"{index_name} batch {batch_no} partial failure on attempt {attempt}: {errors}")
                await asyncio.sleep(0.2 * attempt)
                continue
            # 返回已插入的文档 id，便于上层失败时回滚
            return [str(action.get("_id")) for action in batch if action.get("_id")]
        except Exception as ex:
            last_err = ex
            logger.error(f"{index_name} batch {batch_no} failed on attempt {attempt}: {ex}")
            await asyncio.sleep(0.2 * attempt)
    raise RuntimeError(f"{index_name} batch {batch_no} failed after retries: {last_err}")


async def _rollback_documents_by_ids(es, index_name: str, doc_ids: List[str]) -> bool:
    """
    回滚已插入的文档，按 _id 批量删除。
    """
    if not doc_ids:
        return True

    actions = [
        {"_op_type": "delete", "_index": index_name, "_id": str(doc_id)}
        for doc_id in doc_ids
    ]
    try:
        _, errors = await async_bulk(es, actions, refresh=True, raise_on_error=False)
        if errors:
            logger.error(f"{index_name} rollback encountered errors: {errors}")
            return False
        return True
    except Exception as ex:
        logger.error(f"{index_name} rollback failed: {ex}")
        return False


async def _prune_stale_community_docs(es, index_name: str, keep_ids) -> Tuple[int, List[str]]:
    """R14-A：社区摘要按"整代替换"收敛，保证同一 community_id 只有一条且不留旧代。

    R13 实测问题：社区摘要每次重建都 insert 新行（_id 随机），ES 只能靠"删索引重建"清理，
    Milvus 侧从不清理 → 两侧 community_id 集合不一致（7 vs 65）。
    这里在写入后把"本次集合之外"以及"同一 community_id 但 _id 不是派生值"的旧行删掉。
    """
    keep = {str(x) for x in keep_ids}
    body = {"size": 5000, "_source": ["metadata.community_id"], "query": {"match_all": {}}}
    resp = await es.search(index=index_name, body=body)
    hits = ((resp or {}).get("hits") or {}).get("hits") or []
    stale_ids, stale_cids = [], []
    for hit in hits:
        if hit.get("_id") in keep:
            continue
        cid = (((hit.get("_source") or {}).get("metadata")) or {}).get("community_id")
        stale_ids.append(hit.get("_id"))
        if cid:
            stale_cids.append(cid)
    if not stale_ids:
        return 0, []
    delete_body = {"query": {"terms": {"_id": stale_ids}}}
    result = await es.delete_by_query(index=index_name, body=delete_body, refresh=True)
    return int((result or {}).get("deleted", 0) or 0), sorted(set(stale_cids))


# R14-A-FIX-35：同 source 并发写入必须**串行**，否则 FIX-34 的"写后剪枝"会互相把对方刚写的块删掉。
# 实测（2026-10-27 14:48，scratch 索引 r14a_conc_probe，同 source 并发 3 次，连续三轮）：
#   R1 -> 1 条 / R2 -> 0 条 / R3 -> 0 条，三次全部返回 200「共保存1条数据」**静默丢数据**。
# 机制：A/B/C 各自"保留自己的 _id、删掉同 source 的其他行"；三方交错时，
# 最后执行剪枝的那个人，自己的行可能已被别人删掉 -> 剪完剩 0 条。
# 即"最后完成者胜"这个语义无法保证"胜者的行还在"。
# 修法：进程内按 source 串行（本服务单进程），跨进程再去依赖 ES 的版本冲突重试。
_SOURCE_LOCKS: dict = {}


def _source_lock(src: str) -> asyncio.Lock:
    lock = _SOURCE_LOCKS.get(src)
    if lock is None:
        lock = asyncio.Lock()
        _SOURCE_LOCKS[src] = lock
    return lock


async def add_documents_async(insert_model: InsertDataModel) -> BaseResponse:
    """按 source 串行化后调用实现体（R14-A-FIX-35）。"""
    sources = set()
    for doc in (insert_model.document_list or []):
        try:
            src = str(((doc or {}).get("metadata") or {}).get("source") or "")
        except Exception:  # noqa: BLE001
            src = ""
        if src:
            sources.add(src)
    if not sources:
        return await _add_documents_async_impl(insert_model)
    locks = [_source_lock(s) for s in sorted(sources)]
    for lock in locks:
        await lock.acquire()
    try:
        return await _add_documents_async_impl(insert_model)
    finally:
        for lock in reversed(locks):
            lock.release()


async def _add_documents_async_impl(insert_model: InsertDataModel) -> BaseResponse:
    """
    批量添加数据（异步），带分批、并发与重试。
    """
    es_conn_config = return_nacos_model().get_config()["es_conn_config"]
    batch_size = es_conn_config.get("insert_batch_size", 500)
    max_concurrency = es_conn_config.get("insert_concurrency", 100)
    max_retries = es_conn_config.get("insert_max_retries", 3)

    es = return_nacos_model().es_client_async()
    index_name = is_index_lower(insert_model.index_name)
    try:
        s_field_names, _ = await get_index_mapping_field_async(index_name)
    except Exception as ex:
        logger.error(f'创建索引失败,{ex}')
        return BaseResponse(code=500, msg=f'创建索引失败,{ex}')
    if not s_field_names:
        logger.error(f'保存失败，没有获取对应的mapping字段，请检查index是否正确')
        return BaseResponse(code=500, msg=f'保存失败，没有获取对应的mapping字段，请检查index是否正确')

    data_list, source_paths = build_actions(insert_model, s_field_names, index_name)

    # 入库前按 source 去重
    if insert_model.type != "database":
        try:
            if "faq_" not in index_name and source_paths and insert_model.duplicate_flag:
                operate_data = OperateDataModel(index_name=index_name, col_name="source", col_values=list(source_paths))
                await delete_by_col_documents_async(operate_data)
        except Exception as ex:
            logger.error(f'{index_name}删除已入库文件失败,{ex}')
            return BaseResponse(code=500, msg=f'{index_name}删除已入库文件失败,{ex}')

    if not data_list:
        return BaseResponse(code=200, msg=f'{index_name}保存数据成功，共保存0条数据')

    batches = [data_list[i:i + batch_size] for i in range(0, len(data_list), batch_size)]
    semaphore = asyncio.Semaphore(max_concurrency)

    tasks = []
    for idx, batch in enumerate(batches):
        tasks.append(
            _insert_batch_with_retry(
                es,
                batch,
                semaphore,
                index_name,
                idx + 1,
                max_retries,
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        # 收集本次任务中已提交的 _id，以及失败批次的 _id 以便幂等回滚
        success_ids: List[str] = []
        failed_batch_ids: List[str] = []
        for idx, res in enumerate(results):
            batch_ids = [str(action.get("_id")) for action in batches[idx] if action.get("_id")]
            if isinstance(res, Exception):
                failed_batch_ids.extend(batch_ids)
            else:
                success_ids.extend(res or [])

        rollback_ids = list({*success_ids, *failed_batch_ids})
        rollback_ok = await _rollback_documents_by_ids(es, index_name, rollback_ids)
        logger.error(
            f'{index_name}存在失败批次，errors={errors}; rollback_ids={len(rollback_ids)}, rollback_ok={rollback_ok}'
        )
        msg_suffix = "（已回滚）" if rollback_ok else "（回滚可能不完全，请检查日志）"
        return BaseResponse(code=500, msg=f'{index_name}部分批次保存失败{msg_suffix}')

    try:
        await es.indices.refresh(index=index_name)
    except Exception as ex:
        logger.warning(f'{index_name}刷新索引失败，但插入结果已提交: {ex}')

    # R14-A-FIX-34：同一 source **并发**写入的收敛（写后剪枝）。
    # 原实现只有"写前按 source 删"：三个并发请求各自先删后写，后到的删除看到的是空，
    # 结果是 ES 留 3 条同 source 文档，而 Milvus 因插入串行收敛到 1 条 —— 两侧去重口径不一致
    # （实测：同文件并发 3 次 → ES 3 / Milvus 1）。这里在写后按 source 剪掉"不属于本批 _id"的行，
    # 语义为"最后完成者胜"，与 Milvus 对齐；并发写不同文件时各剪各的 source，互不影响。
    if (insert_model.type != "database" and "faq_" not in index_name
            and not index_name.startswith(COMMUNITY_INDEX_PREFIX)
            and source_paths and insert_model.duplicate_flag):
        try:
            keep_ids = [str(a["_id"]) for a in data_list if a.get("_id")]
            if keep_ids:
                # 注意两个坑（都实测过）：
                #  ① 本索引**没有顶层 source 字段**，source 在 metadata 下；
                #  ② `metadata.source` 是 text（带 keyword 子字段），直接 terms 精确值 **0 命中**，
                #     必须用 `metadata.source.keyword`（与 es_query.init_field_body 的 QueryType.METADATA 一致）。
                # 写错任一处都会静默 0 命中——"看起来剪了，其实没剪"。
                prune_body = {"query": {"bool": {
                    "filter": [{"terms": {"metadata.source.keyword": list(source_paths)}}],
                    "must_not": [{"ids": {"values": keep_ids}}],
                }}}
                prune_res = await es.delete_by_query(index=index_name, body=prune_body, refresh=True)
                pruned = int((prune_res or {}).get("deleted", 0) or 0)
                if pruned:
                    logger.info(f'{index_name}写后按 source 剪枝 {pruned} 条（同 source 并发写入收敛）')
        except Exception as ex:  # noqa: BLE001
            # 剪枝失败不影响本次写入结果（数据已落库），只记警告，避免把"清理没做"升级成"写入失败"
            logger.warning(f'{index_name}写后按 source 剪枝失败（不影响本次写入）: {ex}')

    total_saved = len(data_list)
    msg = f'{index_name}保存数据成功，共保存{total_saved}条数据'
    if index_name.startswith(COMMUNITY_INDEX_PREFIX):
        # R14-A：社区摘要整代替换，删掉本次集合之外的旧行（含 R13 遗留的随机 _id 重复行）
        try:
            deleted, stale = await _prune_stale_community_docs(es, index_name,
                                                               [a["_id"] for a in data_list])
            msg += f'，清理旧代 {deleted} 条'
            if stale:
                logger.info(f'{index_name}清理旧代 {deleted} 条，涉及 community_id={stale[:10]}')
        except Exception as ex:
            logger.error(f'{index_name}清理旧代失败: {ex}')
            return BaseResponse(code=500, msg=f'{index_name}写入成功但清理旧代失败: {ex}')
    return BaseResponse(code=200, msg=msg)
