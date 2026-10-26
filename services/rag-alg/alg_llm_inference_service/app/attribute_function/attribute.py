import ast
import re
import numpy as np
from dataclasses import dataclass
from typing import List, Dict
import traceback
import requests

from utils import get_config

server_config = get_config()
print(server_config)

return_template = '[retrive-tag id="{}" image_urls="{}" fromType="{}"][{}][/retrive-tag]'


class DocumentType:
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"


@dataclass
class ReferenceText:
    text: str
    chunk_id: str
    chunk_i: int
    chunk_type: str
    image_urls = []


def get_rerank_result(query: str, documents: List[str], rerank_model_info=None) -> List[Dict]:
    """
    调用重排序模型
    Args:
        query:
        documents:
        rerank_model_info:
    Returns: 重排序结果，按照分数从高到底排列，index 为原始文本列表的索引位置。
        [
            {
                "index": 1,
                "relevance_score": 0.9995704293251038,
                "document": null
            },
            {
                "index": 0,
                "relevance_score": 0.00016358164430130273,
                "document": null
            }
        ]
    """
    rerank_model_name = None
    rerank_url = None
    api_key = None
    if rerank_model_info:
        rerank_model_name = rerank_model_info.get("model_id", None)
        rerank_url = rerank_model_info.get("url", None)
        api_key = rerank_model_info.get("key", None)
    if not rerank_url:
        rerank_model_name = server_config["rerank_model"]["model_name"]
        rerank_url = server_config["rerank_server"][rerank_model_name]["server_url"]
        api_key = server_config["rerank_server"][rerank_model_name].get("key", None)
    headers = {
        'Content-Type': 'application/json'
    }
    if api_key:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': api_key
        }
    batch_size = 10
    rerank_results = []


    for i in range(0, len(documents), batch_size):
        rerank_request = {
            "model": rerank_model_name,
            "query": query,
            "documents": documents[i: i + batch_size]
        }

        rerank_response = requests.post(rerank_url, json=rerank_request, headers=headers)
        try:
            results = rerank_response.json()['results']
            for result in results:
                result["index"] += i
                rerank_results.append(result)
        except Exception as e:
            print(f"Error occurred during Rerank!\n"
                  f"Error Message: {e}\n"
                  f"Traceback: {traceback.format_exc()}\n"
                  f"Documents: {documents}\n"
                  f"reranker_response: {rerank_response.text}")
    return rerank_results


def tokenize(text):
    """文本按句切分"""
    start_idx = 0
    sentences = []
    offsets = []
    for res_match in re.finditer("[。？！]", text):
        sentences.append(text[start_idx: res_match.end()].strip())
        offsets.append([start_idx, res_match.end()])
        start_idx = res_match.end()

    if text[start_idx:].strip() != "":
        sentences.append(text[start_idx:])
        offsets.append([start_idx, len(text)])
    return sentences, offsets


def tokenize_table(table_markdown_string):
    """
    表格切分
    切分方式：保留标题行，内容行按行切分
    """
    table_markdown_lines = table_markdown_string.replace("\\n", "\n").split("\n")
    head_line = table_markdown_lines.pop(0)
    try:
        table_markdown_lines.pop(0)
    except Exception as e:
        print("Error Occurred in Attribute -> TokenizeTable: ", e)
        pass
    offsets = []
    if "".join(head_line.split("|")).strip() == "":
        head_line = table_markdown_lines.pop(0)

    lines = []
    for i, line in enumerate(table_markdown_lines):
        if "".join(line.split("|")).strip() == "":
            continue
        lines.append(head_line + "\n" + line)
        offsets.append(i + 2)  # 去掉了一个表头行和一个分割行
    return lines, offsets


def map_text_to_document_offset(document_offsets):
    """
    对应绝对位置和字符串的相对位置，切分中由于表格、图片、换页等问题导致坐标不连续。
    """
    offset_list = []
    if isinstance(document_offsets, str):
        document_offsets = ast.literal_eval(document_offsets)
    for doc_start, doc_end in document_offsets:
        for di in range(doc_start, doc_end + 1):
            offset_list.append(di)
    return offset_list


def find_related_images(pic_url_list, pic_offset_list, text_offset, document_offsets):
    image_urls = []
    if pic_url_list is None or pic_offset_list is None or len(pic_offset_list) != len(pic_url_list):
        return image_urls

    for pic_url, pic_offset in zip(pic_url_list, pic_offset_list):
        if text_offset[0] >= len(document_offsets) or text_offset[1] >= len(document_offsets):
            continue
        if document_offsets[text_offset[0]] <= pic_offset <= document_offsets[text_offset[1]]:
            image_urls.append(pic_url)
    return image_urls


def preprocess_answer(text):
    text = text.strip()
    text = re.sub("[\*\-]", "", text)
    return text


class AttributeParameter:
    def __init__(self, reference_chunks):
        self.attr_sentences = []
        self.matched_results = set()  # 记录溯源命中结果
        self.reference_chunks = reference_chunks
        self.reference_sentences = []
        self.count = 0
        self.split_documents()

        # 记录reference 每个句子针对每句回答的最高的分
        self.reference_sentence_scores = [0] * len(self.reference_sentences)

    def split_documents(self):
        """对参考进行分句"""
        for i, item in enumerate(self.reference_chunks):
            # R13-FIX-QA-09：[R12] 语义简化模式下 QA 只下发 page_content/order_num（SimpleDocumentFilter），
            # 这里直接 item["metadata"] 会 KeyError，整个 SSE 流中断 -> 用户只看到"模型暂时无法返回"。
            # 缺失时补空元数据：仍可切句，只是没有精确 offset（引用落到 chunk 级）。
            if not isinstance(item.get("metadata"), dict):
                item["metadata"] = {}
            if "type" in item and item["type"] == "web_search":
                doc = item["page_content"]
                order_num = item.get("order_num")
                doc_type = item["metadata"].get("chunk_type", DocumentType.TEXT)
                sentences, offsets = tokenize(doc)
                for sentence, offset in zip(sentences, offsets):
                    text_obj = ReferenceText(sentence,
                                             chunk_id=order_num,
                                             chunk_i=i,
                                             chunk_type=doc_type)
                    self.reference_sentences.append(text_obj)
            if "offset" not in item["metadata"] or not item["metadata"]["offset"]:
                continue
            doc = item["page_content"]
            order_num = item.get("order_num")
            pic_url_list = item.get("pic_url_list")
            pic_offset_list = item["metadata"].get("pic_offset_list")
            doc_type = item["metadata"].get("chunk_type", DocumentType.TEXT)
            abs_string_offsets = map_text_to_document_offset(item["metadata"]["offset"])

            if doc_type == DocumentType.TEXT:
                sentences, offsets = tokenize(doc)
            elif doc_type == DocumentType.IMAGE:
                sentences, offsets = tokenize(doc)
            elif doc_type == DocumentType.TABLE:
                sentences, offsets = tokenize_table(doc)
            else:
                raise KeyError(f"DocType must in ['text', 'image', 'table'], the input is {doc_type}")

            for sentence, offset in zip(sentences, offsets):
                text_obj = ReferenceText(sentence,
                                         chunk_id=order_num,
                                         chunk_i=i,
                                         chunk_type=doc_type)
                if doc_type == DocumentType.TEXT:
                    text_obj.image_urls = find_related_images(pic_url_list, pic_offset_list, offset, abs_string_offsets)
                elif doc_type == DocumentType.IMAGE:
                    text_obj.image_urls = [item["metadata"].get("image_path", None)]
                self.reference_sentences.append(text_obj)


def preprocess_answer(text):
    text = text.strip()
    text = re.sub("[\*\-]", "", text)
    return text


def last_attribute(attr_text, attr_params: AttributeParameter, last_k=1, last_threshold=0.3):
    """在回答末尾如果没有命中任何溯源，那么利用历史的最高分返回k个"""
    if len(attr_params.reference_chunks) == 0:
        return "", attr_params

    if attr_params.count == 0:
        attr_result, attr_param = attribute(attr_text, attr_params)
        if attr_result:
            return attr_result, attr_params

    attributed_passages_list = []
    for i in np.argsort(attr_params.reference_sentence_scores)[::-1][:last_k]:
        if attr_params.reference_sentence_scores[i] >= last_threshold:
            reference_text = attr_params.reference_sentences[i]
            image_urls = reference_text.image_urls
            if image_urls and isinstance(image_urls, list) and all(url is not None for url in image_urls):
                image_url_list = set(image_urls)
                image_url_string = ";".join(image_url_list)
            else:
                image_url_string = ""
            if "type" in attr_params.attr_sentences[i] and attr_params.attr_sentences[
                i] == "web_search":
                attributed_passages_list.append(return_template.format(reference_text.chunk_id, image_url_string, 1, i))
            else:
                attributed_passages_list.append(return_template.format(reference_text.chunk_id, image_url_string, 0, i))

    return "".join(attributed_passages_list), attr_params


def attribute(answer: str, attr_params: AttributeParameter, threshold=0.97, image_threshold=0.96, table_threshold=0.64, top_k=3, rerank_model_info=None):
    answer = preprocess_answer(answer)
    attr_params.attr_sentences.append(answer)
    attr_params.count += 1

    sorted_results = get_rerank_result(answer, [rt.text for rt in attr_params.reference_sentences], rerank_model_info=rerank_model_info)

    matched_chunk_dict = {}
    for result in sorted_results:
        text_i = result["index"]
        reference_text = attr_params.reference_sentences[text_i]
        doc_type = reference_text.chunk_type
        chunk_pos = (reference_text.chunk_id, reference_text.chunk_i)
        score = result["relevance_score"]
        # print("=" * 20)
        # print("类型：", doc_type)
        # print("reference_text:", reference_text.text, "\n")
        # print("answer:", answer)
        # print("score:", result["relevance_score"])
        # print("image_url", reference_text.image_urls)

        # 更新reference text对每个回答的句子最高的相似度得分
        attr_params.reference_sentence_scores[text_i] = max(score, attr_params.reference_sentence_scores[text_i])

        if doc_type in DocumentType.TEXT and score <= threshold:
            continue
        if doc_type == DocumentType.TABLE and score <= table_threshold:
            continue
        if doc_type == DocumentType.IMAGE and score <= image_threshold:
            continue
        # todo  这几个分是怎么确定的？ 答： 通过实验计算
        if doc_type == DocumentType.IMAGE:
            _threshold = image_threshold
        elif doc_type == DocumentType.TEXT:
            _threshold = threshold
        else:
            _threshold = table_threshold

        if chunk_pos not in matched_chunk_dict:
            matched_chunk_dict[chunk_pos] = (reference_text.image_urls[:], score, (score - _threshold) / _threshold)  # todo: 这里要修改溯源top_k限制后图片命中的逻辑
        else:
            matched_chunk_dict[chunk_pos][0].extend(reference_text.image_urls)

    # 过滤命中太多数据的情况
    matched_chunk_items = sorted(matched_chunk_dict.items(), key=lambda x: x[1][2])[:top_k]

    # 显示溯源结果
    attributed_passages = sorted(matched_chunk_items, key=lambda x: x[0])

    attributed_passages_list = []
    # image_set = set()
    for pos, (image_urls, score, diff_score) in attributed_passages:
        i, doc_id_cus = pos
        if image_urls and isinstance(image_urls, list) and all(url is not None for url in image_urls):
            image_url_list = set(image_urls)
            # image_set = image_set.union(image_url_list)
            image_url_string = ";".join(image_url_list)
        else:
            image_url_string = ""
        try:
            if "type" in attr_params.reference_chunks[doc_id_cus] and attr_params.reference_chunks[
                doc_id_cus]["type"] == "web_search":
                attributed_passages_list.append(return_template.format(i, image_url_string, 1, doc_id_cus))
            else:
                attributed_passages_list.append(return_template.format(i, image_url_string, 0, doc_id_cus))
        except:
            attributed_passages_list.append(return_template.format(i, image_url_string, 0, doc_id_cus))

        attr_params.matched_results.add(doc_id_cus)

    # print(f"一共{len(image_set)}图片")
    # for image in image_set:
    #     print(image)

    # if answer.strip().endswith("|"):
    #     return "\n\n" + "".join(attributed_passages_list)
    # else:
    return "".join(attributed_passages_list), attr_params


def attribute_by_llm(document_i, attr_params):
    if document_i >= len(attr_params.reference_chunks):
        return "", attr_params

    item = attr_params.reference_chunks[document_i]
    if "type" not in item or item["type"] != "web_search":
        if "offset" not in item["metadata"] or not item["metadata"]["offset"]:
            return "", attr_params
    order_num = item.get("order_num")
    pic_url_list = item.get("pic_url_list")
    if pic_url_list and isinstance(pic_url_list, list):
        image_url_list = set(pic_url_list)
        image_url_string = ";".join(image_url_list)
    else:
        image_url_string = ""

    attr_params.matched_results.add(order_num)
    if "type" in item and item["type"] == "web_search":
        return return_template.format(order_num, image_url_string, 1, document_i), attr_params
    else:
        return return_template.format(order_num, image_url_string, 0, document_i), attr_params

# if __name__ == '__main__':
#     answer = """浙商惠盈纯债债券型证券投资基金的管理费年费率为0.3%，托管费年费率为0.1%。"""
#     with open("/Users/daisyli/Coding/Gientech/rag_evaluate/retrieve.json", "r") as f:
#         documents = json.load(f)
#     ans = attribute_function(answer, documents)
#     print(ans)
