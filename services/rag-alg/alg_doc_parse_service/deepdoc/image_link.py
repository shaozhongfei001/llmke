import re
import time

import jieba
import numpy as np

from deepdoc.output_object import ParsedText, ParsedImage
from deepdoc.splitter.utils import group_documents
from deepdoc.utils import embedding_func
from log import logger
from server.api_param import ModelInfo


def get_cosine_similarity(image_text: str, potential_texts: list[str], embedding_model_info: ModelInfo):
    """
    image_text: 待匹配的图片文本
    potential_texts: 文档块候选项
    """
    if len(potential_texts) == 0:
        return None
    elif len(potential_texts) == 1:
        return 0

    embeddings = embedding_func([image_text] + potential_texts, embedding_model_info)
    image_embed_vector, text_embed_vectors = np.array(embeddings[0]), np.array(embeddings[1:])

    # Normalize the input vector a
    image_embed_vector = image_embed_vector / np.linalg.norm(image_embed_vector)

    # Calculate cosine similarity
    similarities = []
    for text_embed in text_embed_vectors:
        text_embed = text_embed / np.linalg.norm(text_embed)
        similarity = np.dot(image_embed_vector, text_embed)
        similarities.append(similarity)

    # Find the index of the maximum similarity
    most_similar_idx = np.argmax(similarities)
    if similarities[most_similar_idx] < 0.5:
        most_similar_idx = -1
    return most_similar_idx


def get_jaccard_similarity(image_text, potential_texts):
    image_text_gram = set(jieba.cut_for_search(image_text))
    logger.info(f'图片内容包含{len(image_text_gram)}个token')

    potential_texts_gram = [set(jieba.cut_for_search(potential_text)) for potential_text in potential_texts]
    logger.info(
        f'窗口中chunks分别有{[len(potential_text_gram) for potential_text_gram in potential_texts_gram]}个token')

    redundant_gram = set.intersection(*potential_texts_gram)
    logger.info(f'窗口中的chunks有{len(redundant_gram)}个冗余的token')

    redundant_gram -= set.intersection(redundant_gram, image_text_gram)
    logger.info(f'去掉图片内容的token之后，冗余的token有{len(redundant_gram)}个。')

    potential_texts_gram = [potential_text_gram - redundant_gram for potential_text_gram in potential_texts_gram]

    jaccard_similarities = [
        len(image_text_gram & potential_text_gram) / len(image_text_gram | potential_text_gram)
        for potential_text_gram in potential_texts_gram
    ]
    logger.info(f'jaccard相似度：{jaccard_similarities}')

    return np.argmax(jaccard_similarities)

def link_images_text_ppt(parsed_objs: list[ParsedText], embedding_model_info: ModelInfo, window_size=3) -> list[ParsedText]:
    timer = time.perf_counter()

    documents_group_by_source = group_documents(parsed_objs)
    for _, parsed_objs in documents_group_by_source.items():
        """关联图片和文本"""
        parsed_objs_length = len(parsed_objs)
        for i, parsed_obj in enumerate(parsed_objs):
            if isinstance(parsed_obj, ParsedImage) and parsed_obj.page_content:
                image_pk = parsed_obj.metadata.pk
                image_path = parsed_obj.metadata.image_path
                logger.info("=" * 200)
                logger.info(f"图片地址：{parsed_obj.metadata.image_path}")
                logger.info(f"图片内容：{parsed_obj.page_content}")

                caption_nearby = parsed_obj.metadata.caption_nearby
                if caption_nearby:
                    nearby_obj = None
                    if caption_nearby == 'previous':
                        for nearby_index in range(i - 1, -1, -1):
                            if parsed_objs[nearby_index].metadata.type == "text":
                                nearby_obj = parsed_objs[nearby_index]
                                break
                    else:
                        for nearby_index in range(i + 1, parsed_objs_length):
                            if parsed_objs[nearby_index].metadata.type == "text":
                                nearby_obj = parsed_objs[nearby_index]
                                break
                    assert nearby_obj is not None

                    parsed_obj.metadata.text_parent_id_list.append(nearby_obj.metadata.pk)
                    nearby_obj.metadata.pic_url_list.append(image_path)
                    nearby_obj.metadata.pic_children_id_list.append(image_pk)
                    logger.info(
                        f'关联文本：{nearby_obj.page_content}\n'
                        f'文本ID：{nearby_obj.metadata.pk}\n图片ID：{image_pk}'
                    )

                # 和相邻的text判断关联性, 与前后window_size距离内（前后各三个）所有text中最相关的text chunk关联
                text_pool = []
                page_number = parsed_obj.metadata.page_number[0]
                for one_parsed_obj in parsed_objs:
                    if isinstance(one_parsed_obj, ParsedText) and one_parsed_obj.page_content:
                        if page_number in one_parsed_obj.metadata.page_number:
                            text_pool.append(one_parsed_obj)
                            break
                if text_pool:
                    text_idx = get_cosine_similarity(
                        parsed_obj.page_content,
                        [text.page_content for text in text_pool],
                        embedding_model_info
                    )
                    if text_idx >= 0:
                        # 文本 -> 图片
                        text_pool[text_idx].metadata.pic_url_list.append(image_path)
                        text_pool[text_idx].metadata.pic_children_id_list.append(image_pk)

                        # 关联chunk中的某个句子
                        sentences = re.split('(?<=[。？?！!；;])', text_pool[text_idx].page_content)
                        sentence_index = get_cosine_similarity(
                            parsed_obj.page_content,
                            sentences,
                            embedding_model_info
                        )
                        start_offset = len(''.join(sentences[:sentence_index]))
                        text_pool[text_idx].metadata.pic_offset_list.append(start_offset)
                        logger.info(f"图片坐标：{start_offset}")

                        # 图片 -> 文本
                        parsed_obj.metadata.text_parent_id_list.append(text_pool[text_idx].metadata.pk)
                        logger.info(
                            f'关联文本：{text_pool[text_idx].page_content}\n'
                            f'文本ID：{text_pool[text_idx].metadata.pk}\n图片ID：{image_pk}'
                        )


    logger.info(f'图片关联花费时间：{(time.perf_counter() - timer):.2f}s')

    return parsed_objs


def link_images_text(parsed_objs: list[ParsedText], embedding_model_info: ModelInfo, window_size=3) -> list[ParsedText]:
    timer = time.perf_counter()

    documents_group_by_source = group_documents(parsed_objs)
    for _, objs in documents_group_by_source.items():
        """关联图片和文本"""
        objs_length = len(objs)
        for i, parsed_obj in enumerate(objs):
            if isinstance(parsed_obj, ParsedImage) and parsed_obj.page_content:
                image_pk = parsed_obj.metadata.pk
                image_path = parsed_obj.metadata.image_path
                logger.info("=" * 200)
                logger.info(f"图片地址：{parsed_obj.metadata.image_path}")
                logger.info(f"图片内容：{parsed_obj.page_content}")

                # 寻找图片相关的图片标题或者说明文字
                caption_nearby = parsed_obj.metadata.caption_nearby
                if caption_nearby:
                    nearby_obj = None
                    if caption_nearby == 'previous':
                        for nearby_index in range(i - 1, -1, -1):
                            if objs[nearby_index].metadata.type == "text":
                                nearby_obj = objs[nearby_index]
                                break
                    else:
                        for nearby_index in range(i + 1, objs_length):
                            if objs[nearby_index].metadata.type == "text":
                                nearby_obj = objs[nearby_index]
                                break
                    assert nearby_obj is not None

                    parsed_obj.metadata.text_parent_id_list.append(nearby_obj.metadata.pk)
                    nearby_obj.metadata.pic_url_list.append(image_path)
                    nearby_obj.metadata.pic_children_id_list.append(image_pk)
                    logger.info(
                        f'关联文本：{nearby_obj.page_content}\n'
                        f'文本ID：{nearby_obj.metadata.pk}\n图片ID：{image_pk}'
                    )
                    continue

                # 和相邻的text判断关联性, 与前后window_size距离内（前后各三个）所有text中最相关的text chunk关联
                text_pool = []
                if caption_nearby == 'previous':
                    start_index = i - 2
                else:
                    start_index = i - 1
                for d_i in range(start_index, -1, -1):
                    if len(text_pool) == window_size:
                        break
                    if objs[d_i].metadata.type == "text":
                        text_pool.append(objs[d_i])

                previous_window_used = len(text_pool)
                if caption_nearby == 'next':
                    start_index = i + 2
                else:
                    start_index = i + 1
                for d_i in range(start_index, objs_length):
                    if len(text_pool) - previous_window_used == window_size:
                        break
                    if objs[d_i].metadata.type == "text":
                        text_pool.append(objs[d_i])

                
                if text_pool:
                    text_idx = get_cosine_similarity(
                        parsed_obj.page_content,
                        [text.page_content for text in text_pool],
                        embedding_model_info
                    )
                    # 文本 -> 图片
                    # 有可能存在已经根据caption关联过的情况，这里再关联一次会出现重复关联
                    if image_path not in text_pool[text_idx].metadata.pic_url_list:
                        text_pool[text_idx].metadata.pic_url_list.append(image_path)
                        text_pool[text_idx].metadata.pic_children_id_list.append(image_pk)

                    # 关联chunk中的某个句子
                    sentences = re.split('(?<=[。？?！!；;])', text_pool[text_idx].page_content)
                    sentence_index = get_cosine_similarity(
                        parsed_obj.page_content,
                        sentences,
                        embedding_model_info
                    )
                    start_offset = len(''.join(sentences[:sentence_index]))
                    text_pool[text_idx].metadata.pic_offset_list.append(start_offset)
                    logger.info(f"图片坐标：{start_offset}")

                    # 图片 -> 文本
                    parsed_obj.metadata.text_parent_id_list.append(text_pool[text_idx].metadata.pk)
                    logger.info(
                        f'关联文本：{text_pool[text_idx].page_content}\n'
                        f'文本ID：{text_pool[text_idx].metadata.pk}\n图片ID：{image_pk}'
                    )

    logger.info(f'图片关联花费时间：{(time.perf_counter() - timer):.2f}s')

    return parsed_objs
