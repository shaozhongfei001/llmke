import asyncio
from typing import List, Dict, Any

import httpx
import requests
from requests import Response

from log import logger
from server.exception.custom_exception import (
    IndexMilvusInsertFailedError, IndexESInsertFailedError,
)
from server.nacos_utils import DocParseConfig


async def _insert_es_batch_async(
    client,
    url: str,
    index_name: str,
    batch_docs: List[Dict[str, Any]],
    batch_idx: int,
    total_batches: int,
    duplicate_flag: bool
) -> int:
    """
    插入单个 ES 批次
    """
    payload = {
        'index_name': index_name,
        'document_list': batch_docs,
        'duplicate_flag': duplicate_flag
    }

    logger.debug(
        f'[Request] es index服务插入数据, URL: {url}, index_name: {index_name}, '
        f'批次: {batch_idx + 1}/{total_batches}, 数量: {len(batch_docs)}'
    )
    try:
        response = await client.post(url, json=payload)
        status_code = response.status_code
        if status_code != 200:
            error_msg = f"返回码错误: {response.text}, code: {status_code}, URL: {url}"
            logger.error(error_msg)
            raise IndexESInsertFailedError(error_msg)
        try:
            response_json = response.json()
        except ValueError as exc:
            error_msg = f'响应数据格式错误: {response.text}, URL: {url}'
            logger.error(error_msg)
            raise IndexESInsertFailedError(error_msg) from exc

        status_code = response_json['code']
        if status_code != 200:
            error_msg = f'返回码错误: {response_json.get("msg", response.text)}, URL: {url}'
            logger.error(error_msg)
            raise IndexESInsertFailedError(error_msg)
    except Exception as e:
        if isinstance(e, IndexESInsertFailedError):
            raise
        error_msg = f'请求失败: {str(e)}, URL: {url}'
        logger.error(error_msg)
        raise IndexESInsertFailedError(error_msg) from e
    
    return batch_idx



def normalize_for_es(document_list):
    """[R12-FIX-PARSE-08] ES 侧文档瘦身：剔除不适合动态 mapping 的深层数组字段。

    实测（`docx-image.docx` → r12_it_parse_004）：图片块的 `metadata.boxes` 是
    「多个 OCR 框 × 4 点 × 2 坐标」的四层数组，ES 动态 mapping 无法推断 dims，报
        Mapper for [metadata.boxes] conflicts with existing mapper: Cannot update parameter [dims] from [4] to [2]
    → 整批 400、回滚，含图片的文档**无法落库**。

    处置：**ES payload 中剔除 `boxes`**（检索侧不需要它，页内 bbox 已由 `position` 表达；
    API 响应里的 `boxes` 保持不变）。`base64` 同理剔除（体积大且 ES 不用）。
    """
    import copy
    out = []
    for doc in document_list:
        d = copy.deepcopy(doc)
        md = d.get('metadata')
        if isinstance(md, dict):
            md.pop('boxes', None)
            md.pop('base64', None)
        out.append(d)
    return out


async def index_es(
    index_name: str,
    document_list
) -> None:
    """ES 写入的外层幂等包装（R14-A-FIX-28）。

    多文件**并发首次入库**同一个新库时，谁先建索引谁赢，其余请求会收到
    `resource_already_exists_exception`（索引已存在）。这是**预期内的并发状态，不是失败**：
    索引此刻已就绪，隔一次重试即可正常写入。
    原实现把它当异常向上抛 -> 整批零写入 -> 上层 `/parse_sync` 仍 `success=true`，
    用户视角"传了 3 个只生效 1 个"。实测 kb_22 三篇并发即命中。
    """
    try:
        return await _index_es_once(index_name, document_list)
    except Exception as e:  # noqa: BLE001
        _msg = str(e)
        if any(k in _msg for k in ('resource_already_exists', 'already_exists', '已存在', '创建索引失败')):
            logger.warning(f'ES 索引并发创建冲突（预期状态），1s 后重试一次: {index_name} | {_msg[:200]}')
            await asyncio.sleep(1.0)
            return await _index_es_once(index_name, document_list)
        raise


async def _index_es_once(
    index_name: str,
    document_list
) -> None:
    """
    将解析后的 chunks 按批次并发写入 ES
    第一批次单独处理（去重），后续批次按 max_concurrency 分组并发执行
    """
    if not document_list:
        return

    document_list = normalize_for_es(document_list)

    doc_parse_config = DocParseConfig()
    es_ip = doc_parse_config.configs['java-common']['server']['host-ip']
    es_port = doc_parse_config.configs['index']['es_server']['port']
    url = doc_parse_config.config['es-insert'].format(ip=es_ip, port=es_port)

    # 允许通过配置下发批大小，默认 500
    batch_size = doc_parse_config.config.get('es_insert_batch_size', 500)
    max_concurrency = doc_parse_config.config.get('es_insert_concurrency', 5)
    es_insert_timeout = doc_parse_config.config.get('es_insert_timeout', 300)
    es_insert_retries = doc_parse_config.config.get('es_insert_retries', 2)
    es_insert_retry_backoff = doc_parse_config.config.get('es_insert_retry_backoff', 0.5)   # 重试间隔基线（秒），使用指数退避
    total = len(document_list)
    batches = (total + batch_size - 1) // batch_size

    async with httpx.AsyncClient(timeout=es_insert_timeout, limits=httpx.Limits(max_connections=max_concurrency)) as client:
        # 第一批次单独处理（去重）
        if batches > 0:
            start = 0
            end = min(batch_size, total)
            batch_docs = document_list[start:end]
            await _insert_es_batch_async(
                client=client,
                url=url,
                index_name=index_name,
                batch_docs=batch_docs,
                batch_idx=0,
                total_batches=batches,
                duplicate_flag=True
            )

        # 后续批次按 max_concurrency 并发处理（不去重）
        if batches > 1:
            # 滑动窗口：最多保持 max_concurrency 个正在执行的任务
            async def _run_es_batch(idx: int, batch_docs: List[Dict[str, Any]]):
                last_exc = None
                for attempt in range(es_insert_retries + 1):
                    try:
                        return await _insert_es_batch_async(
                            client=client,
                            url=url,
                            index_name=index_name,
                            batch_docs=batch_docs,
                            batch_idx=idx,
                            total_batches=batches,
                            duplicate_flag=False
                        )
                    except Exception as e:
                        last_exc = e
                        if attempt >= es_insert_retries:
                            raise
                        logger.warning(f'ES 批次 {idx} 插入失败，第 {attempt+1} 次重试，错误: {e}')
                        await asyncio.sleep(es_insert_retry_backoff * (2 ** attempt))

            # 准备批次参数的生成器
            def _make_batch_args(start_idx: int):
                for i in range(start_idx, batches):
                    s = i * batch_size
                    e = min(s + batch_size, total)
                    yield i, document_list[s:e]

            batch_iter = _make_batch_args(start_idx=1)
            in_flight = set()
            # 启动初始窗口
            for _ in range(min(max_concurrency, batches - 1)):
                try:
                    idx, batch_docs = next(batch_iter)
                except StopIteration:
                    break
                in_flight.add(asyncio.create_task(_run_es_batch(idx, batch_docs)))

            # 处理已完成的任务，并保持窗口填满
            while in_flight:
                done, pending = await asyncio.wait(in_flight, return_when=asyncio.FIRST_COMPLETED)
                # 先收集所有已完成任务的异常（不立即抛出）
                first_exc = None
                for d in done:
                    exc = d.exception()
                    if exc is not None and first_exc is None:
                        first_exc = exc
                # 读取所有已完成 task 的结果（吞掉异常，因为已记录在 first_exc）
                for d in done:
                    try:
                        d.result()
                    except Exception:
                        pass
                    finally:
                        in_flight.remove(d)

                if first_exc is not None:
                    logger.error(f'ES 并发插入失败: {first_exc}')
                    # 取消正在运行的任务并等待它们结束（消化取消异常）
                    for p in pending:
                        p.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)
                    raise first_exc

                # 填充窗口
                try:
                    idx, batch_docs = next(batch_iter)
                except StopIteration:
                    continue
                in_flight.add(asyncio.create_task(_run_es_batch(idx, batch_docs)))

    logger.info(f'es index服务插入数据成功，总批次：{batches}，总量：{total}')


async def _insert_milvus_batch_async(
    client: httpx.AsyncClient,
    url: str,
    index_name: str,
    embed_model: str,
    db_name: str,
    batch_docs: List[Dict[str, Any]],
    batch_idx: int,
    total_batches: int,
    duplicate_flag: bool
) -> int:
    """
    插入单个 Milvus 批次
    """
    payload = {
        'collection_name': index_name,
        "model_name": embed_model,
        'document_list': batch_docs,
        'db_name': db_name,
        'duplicate_flag': duplicate_flag
    }

    logger.debug(
        f'[Request] milvus index服务插入数据, URL: {url}, collection_name: {index_name}, '
        f'model_name: {embed_model}, 批次: {batch_idx + 1}/{total_batches}, 数量: {len(batch_docs)}, db_name: {db_name}'
    )
    try:
        response = await client.post(url, json=payload)
        status_code = response.status_code
        if status_code != 200:
            error_msg = f"返回码错误: {response.text}, code: {status_code}, URL: {url}"
            logger.error(error_msg)
            raise IndexMilvusInsertFailedError(error_msg)
        try:
            response_json = response.json()
        except ValueError as exc:
            error_msg = f'响应数据格式错误：{response.text}, URL: {url}'
            logger.error(error_msg)
            raise IndexMilvusInsertFailedError(error_msg) from exc

        status_code = response_json['code']
        if status_code != 200:
            error_msg = f'返回码错误：{response_json.get("msg", response.text)}, URL: {url}'
            logger.error(error_msg)
            raise IndexMilvusInsertFailedError(error_msg)
    except Exception as e:
        if isinstance(e, IndexMilvusInsertFailedError):
            raise
        error_msg = f'请求失败: {str(e)}, URL: {url}'
        logger.error(error_msg)
        raise IndexMilvusInsertFailedError(error_msg) from e
    
    return batch_idx


async def index_milvus(
    index_name: str,
    embed_model: str,
    document_list
) -> None:
    """
    将解析后的 chunks 按批次并发写入 Milvus
    第一批次单独处理（去重），后续批次按 max_concurrency 分组并发执行
    """
    if not document_list:
        return

    doc_parse_config = DocParseConfig()
    db_name = doc_parse_config.configs['index']['milvus_conn_config']['milvus_database']
    milvus_ip = doc_parse_config.configs['java-common']['server']['host-ip']
    milvus_port = doc_parse_config.configs['index']['milvus_server']['port']
    url = doc_parse_config.config['milvus-insert'].format(ip=milvus_ip, port=milvus_port)

    batch_size = doc_parse_config.config.get('milvus_insert_batch_size', 500)
    max_concurrency = doc_parse_config.config.get('milvus_insert_concurrency', 5)
    milvus_insert_timeout = doc_parse_config.config.get('milvus_insert_timeout', 300)
    milvus_insert_retries = doc_parse_config.config.get('milvus_insert_retries', 2)
    milvus_insert_retry_backoff = doc_parse_config.config.get('milvus_insert_retry_backoff', 0.5) # 重试间隔基线（秒），使用指数退避
    total = len(document_list)
    batches = (total + batch_size - 1) // batch_size

    async with httpx.AsyncClient(timeout=milvus_insert_timeout, limits=httpx.Limits(max_connections=max_concurrency)) as client:
        # 第一批次单独处理（去重）
        if batches > 0:
            start = 0
            end = min(batch_size, total)
            batch_docs = document_list[start:end]
            await _insert_milvus_batch_async(
                client=client,
                url=url,
                index_name=index_name,
                embed_model=embed_model,
                db_name=db_name,
                batch_docs=batch_docs,
                batch_idx=0,
                total_batches=batches,
                duplicate_flag=True # duplicate_flag = True 插入前删除相同 source 的旧数据
            )

        # 后续批次按 max_concurrency 并发处理（不去重）
        if batches > 1:
            async def _run_milvus_batch(idx: int, batch_docs: List[Dict[str, Any]]):
                for attempt in range(milvus_insert_retries + 1):
                    try:
                        return await _insert_milvus_batch_async(
                            client=client,
                            url=url,
                            index_name=index_name,
                            embed_model=embed_model,
                            db_name=db_name,
                            batch_docs=batch_docs,
                            batch_idx=idx,
                            total_batches=batches,
                            duplicate_flag=False
                        )
                    except Exception as e:
                        if attempt >= milvus_insert_retries:
                            raise
                        logger.warning(f'Milvus 批次 {idx} 插入失败，第 {attempt+1} 次重试，错误: {e}')
                        await asyncio.sleep(milvus_insert_retry_backoff * (2 ** attempt))

            def _make_batch_args(start_idx: int):
                for i in range(start_idx, batches):
                    s = i * batch_size
                    e = min(s + batch_size, total)
                    yield i, document_list[s:e]

            batch_iter = _make_batch_args(1)
            in_flight = set()
            for _ in range(min(max_concurrency, batches - 1)):
                try:
                    idx, batch_docs = next(batch_iter)
                except StopIteration:
                    break
                in_flight.add(asyncio.create_task(_run_milvus_batch(idx, batch_docs)))

            while in_flight:
                done, pending = await asyncio.wait(in_flight, return_when=asyncio.FIRST_COMPLETED)
                first_exc = None
                for d in done:
                    exc = d.exception()
                    if exc is not None and first_exc is None:
                        first_exc = exc
                for d in done:
                    try:
                        d.result()
                    except Exception:
                        pass
                    finally:
                        in_flight.remove(d)

                if first_exc is not None:
                    logger.error(f'Milvus 并发插入失败: {first_exc}')
                    for p in pending:
                        p.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)
                    raise first_exc

                try:
                    idx, batch_docs = next(batch_iter)
                except StopIteration:
                    continue
                in_flight.add(asyncio.create_task(_run_milvus_batch(idx, batch_docs)))

    logger.info(f'milvus index服务插入数据成功，总批次：{batches}，总量：{total}')
