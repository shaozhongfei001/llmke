"""
规则版本识别
算法版本识别
"""
import re
import requests
import traceback
from langchain_core.documents import Document
import uuid
import json

from server.nacos_utils import DocParseConfig
import os

DocParse = DocParseConfig()
server_config = DocParse.config


def by_file_name(need_version_file_list):
    """
    通过文件名字进行版本计算
    获取核心内容，如果核心内容相同则认为相同
    正则表达式，剔除后续内容
    文件名与知识库中已有文件名相似
    是否相似可以使用正则判断规则。将文件名称去除掉下划线、横线、括号的后缀，如果剩余内容完全相同，则归类到一个父文件。
    例如：
    保险保障基金管理办法（2008年修订）与 保险保障基金管理办法（2020年修订）
    保险保障基金管理办法（保监会令 2008 年第 2 号） 与 保险保障基金管理办法（银保监会令 2022 年第 7 号）
    xx项目需求说明书V1.2 与 xx项目需求说明书V1.1
    返回是存在子节点的问题
    """
    pattern_list = [r'(（.*?）|\(.*?\))*\s*\.[^.]+$', r'V\d+\..*', r'\d+\.\w+$']
    def clean_filename(filename: str) -> str:
        """
        仅去除文件名首尾的年份、日期、版本号等信息（含“年/月/日”形式）
        保留主体部分，返回处理后的文件名
        """
        # 分离扩展名
        name, ext = os.path.splitext(filename)
        # 去掉首尾空格、下划线、横杠等
        name = name.strip(" -_.")
        # 定义正则：年份、日期、版本号
        patterns = [
            r'^(19|20)\d{2}(年)?',  # 年份开头 2023 / 2023年
            r'^\d{4}[-_/\.]?\d{2}[-_/\.]?\d{2}(日)?',  # 开头日期 20230101 / 2023-01-01 / 2023年01月01日
            r'^\d{2}[-_/\.]?\d{2}[-_/\.]?\d{2}',  # 开头 YYMMDD
            r'^(v|ver|version)[\s._-]?\d+(\.\d+)*',  # 开头版本号 v1 v2.0
            r'^\d{1,3}$',  # 单纯数字（小批次号）
            r'(19|20)\d{2}(年)?$',  # 结尾年份
            r'\d{4}[-_/\.]?\d{2}[-_/\.]?\d{2}(日)?$',  # 结尾日期
            r'\d{2}[-_/\.]?\d{2}[-_/\.]?\d{2}$',  # 结尾 YYMMDD
            r'(v|ver|version)[\s._-]?\d+(\.\d+)*$',  # 结尾版本号
            r'\d{1,3}$',  # 结尾数字
            r'(年|月|日)$'  # 结尾带中文日期单位
        ]

        # 迭代去掉首尾的多余信息，直到稳定
        changed = True
        while changed:
            old = name
            for pat in patterns:
                name = re.sub(pat, '', name, flags=re.IGNORECASE).strip(" -_.")
            changed = (name != old)
        return name

    file_dict = {}
    for file_name in need_version_file_list:
        change_file_true = False
        curr_file_name = file_name
        for pattern in pattern_list:
            new_file_name = re.sub(pattern, '', file_name).strip()
            new_file_name = clean_filename(new_file_name)
            if new_file_name != file_name:
                change_file_true = True
                if len(new_file_name) < len(curr_file_name):
                    curr_file_name = new_file_name
        file_dict[file_name] = curr_file_name
        if not change_file_true:
            file_dict[file_name] = file_name
    return file_dict

class VersionRec:

    def __init__(self, file_version_params):
        self.ori_file_n_chunk = file_version_params.ori_file_n_chunk
        self.recall_file_top_n_chunk = file_version_params.recall_file_top_n_chunk
        multi_version_dict = server_config.get("multi_version", {})
        if multi_version_dict.get("use_code_score", True):
            self.score_threshold = file_version_params.score_threshold
            self.max_score_threshold = file_version_params.max_score_threshold
        else:
            self.score_threshold = multi_version_dict.get("score_threshold", 120)
            self.max_score_threshold = multi_version_dict.get("max_score_threshold", 0.75)
        self.knowledge_base_name = file_version_params.knowledge_base_name
        self.need_version_document_list = file_version_params.need_version_doc
        self.have_version_document_list = file_version_params.have_version_doc
        self.status = file_version_params.status
        self.data: list[dict] = []
        self.success = True
        self.model_info = file_version_params.model_info

    def version_rec(self):
        return_file_name = []
        if self.status == "0":
            return_file_name = self.version_rec_file_name()
            self.data = return_file_name
        elif self.status == "1":
            return_file_name_by_file = self.version_rec_file_name()
            try:
                return_file_name = self.version_rec_file_content(return_file_name_by_file)
                self.data = return_file_name
            except Exception as e:
                traceback.print_exception(e)
                self.data = return_file_name_by_file
        return return_file_name

    def version_rec_file_name(self):
        """
        总控，先用文件名字进行识别，如果识别到了就不用文本内容进行合并，如果未识别到就可以用文本内容处理
        整理解析需要上传的文件内容,然后处理一下内容,用新的id进行处理
        1. 如果文件名存在就使用老的ID
        2. 如果文件名不存在那就使用内容相似度计算
        3. 如果都不存在就自动生成一个
        4. 返回文件ID以及对应的聚类ID
        need_version_document_list 参数样例 [{"id":"","name":""}]
        have_version_document_list 参数样例 [{"id":"","name":"","group_id":""}]
        返回值：[{"id":"","name":"","group_id":""}]
        """
        need_version_file_list = self.find_file_name(self.need_version_document_list)
        need_have_version_file_list = self.find_file_name(self.have_version_document_list)
        need_file_dict = by_file_name(need_version_file_list)
        have_file_dict = by_file_name(need_have_version_file_list)
        return_file_name = []
        for ori_file_name in need_file_dict.keys():
            bal_file_dict = {"id":"", "name":"", "group_id":""}
            bal_file_name = need_file_dict[ori_file_name]
            for need_version_file in self.need_version_document_list:
                if need_version_file["name"] == ori_file_name:
                    bal_file_dict["id"] = need_version_file["id"]
                    bal_file_dict["name"] = ori_file_name
            for ori_have_name in have_file_dict.keys():
                bal_have_file_name = have_file_dict[ori_have_name]
                if bal_file_name == bal_have_file_name:
                    for have_version_file in self.have_version_document_list:
                        if ori_have_name == have_version_file["name"]:
                            if len(have_version_file["group_id"]) > 0:
                                bal_file_dict["group_id"] = have_version_file["group_id"]
                            else:
                                bal_file_dict["group_id"] = self.create_version_id(bal_file_name)
                                have_version_file["group_id"] = bal_file_dict["group_id"]
                                return_file_name.append(have_version_file)
            # 内容补充到have_file_dict和have_version_document_list中
            have_file_dict[ori_file_name] = bal_file_name
            self.have_version_document_list.append(bal_file_dict)
            return_file_name.append(bal_file_dict)
        for file in return_file_name:
            file['version_date'] = self.get_version_date(file['name'], self.knowledge_base_name, server_config)
        return return_file_name



    def version_rec_file_content(self, return_file_name_by_file):
        """
        总控，先用文件名字进行识别，如果识别到了就不用文本内容进行合并，如果未识别到就可以用文本内容处理
        整理解析需要上传的文件内容,然后处理一下内容,用新的id进行处理
        1. 如果文件名存在就使用老的ID
        2. 如果文件名不存在那就使用内容相似度计算
        3. 如果都不存在就自动生成一个
        4. 返回文件ID以及对应的聚类ID
        返回值：[{"id":"","name":"","group_id":""}]
        """
        return_file_name = []
        has_id = []
        for need_version_document in return_file_name_by_file:
            if len(need_version_document["group_id"]) > 0:
                if need_version_document["id"] not in has_id:
                    has_id.append(need_version_document["id"])
                    return_file_name.append(need_version_document)
                continue
            new_need_version_document = {"id":"", "name":"", "group_id": ""}
            top_k = self.ori_file_n_chunk
            file_name = need_version_document["name"]
            file_id = need_version_document["id"]
            new_need_version_document["id"] = need_version_document["id"]
            new_need_version_document["name"] = need_version_document["name"]
            es_documents = self.retrieval_ori_chunk(self.knowledge_base_name, top_k, file_name, server_config)
            need_simi_file_chunk = []
            for es_document in es_documents:
                need_simi_file_chunk.append(es_document.page_content)
            sorted_items = self.by_file_content(server_config, need_simi_file_chunk, file_id)
            top1_simi_data = sorted_items[-1]
            simi_file_name = top1_simi_data[0]
            simi_file_score = top1_simi_data[1]
            if simi_file_score >= self.max_score_threshold:
                for have_version_document in self.have_version_document_list:
                    if simi_file_name == have_version_document["name"]:
                        if len(have_version_document["group_id"]) > 0:
                            new_need_version_document["group_id"] = have_version_document["group_id"]
                        else:
                            new_need_version_document["group_id"] = self.create_version_id(file_name)
                            have_version_document["group_id"] = new_need_version_document["group_id"]
                            if have_version_document["id"] not in has_id:
                                return_file_name.append(have_version_document)
                                has_id.append(have_version_document["id"])
                            if new_need_version_document["id"] not in has_id:
                                return_file_name.append(new_need_version_document)
                                has_id.append(new_need_version_document["id"])
            if new_need_version_document["id"] not in has_id:
                return_file_name.append(new_need_version_document)
                has_id.append(new_need_version_document["id"])
        for file in return_file_name:
            file['version_date'] = self.get_version_date(file['name'], self.knowledge_base_name, server_config)
        return return_file_name

    def find_file_name(self, need_version_document_list):
        need_version_file_list = []
        for need_version_document in need_version_document_list:
             need_version_file_list.append(need_version_document["name"])
        return need_version_file_list





    def by_file_content(self, server_config, need_simi_file_chunk, file_id):
        """
        通过文件内容进行版本计算
        一阶段，遍历知识库中的文档，随机抽取文档的N个chunk，使用chunk在该知识库中检索，设定阈值召回最相似的K个chunk。如果对应N个chunk都有召回的chunk来自同一个文件，那么这个文件就可以作为归档候选。
        1. 原始文件随机选取ori_file_n_chunk个chunk.
        2. 每个chunk进行召回recall_file_top_n_chunk.
        3. 计算相似度，如果相似度大于score_threshold就理解为相似。
        4. 统计topn相似度(相似占比)
        es相似度计算,搞一下内容
        """
        recall_file_count = {}
        need_simi_file_chunk_size = len(need_simi_file_chunk)
        for chunk in need_simi_file_chunk:
            have_source_file_list = []
            es_documents = self.retrieval_elastic(chunk, self.knowledge_base_name, self.recall_file_top_n_chunk, file_id, server_config)
            for es_document in es_documents:
                if es_document.metadata['search']['score'] > self.score_threshold:
                    source_file_name = es_document.metadata["parent_file_name"]
                    if source_file_name not in have_source_file_list:
                        if source_file_name in recall_file_count:
                            recall_file_count[source_file_name] = recall_file_count[source_file_name] + 1
                        else:
                            recall_file_count[source_file_name] = 1
                        have_source_file_list.append(source_file_name)
        for source_file_name in recall_file_count:
            recall_file_count[source_file_name] = recall_file_count[source_file_name]/need_simi_file_chunk_size
        sorted_items = sorted(recall_file_count.items(), key=lambda x: x[1])
        return sorted_items

    def retrieval_ori_chunk(self, knowledge_base_name, top_k, file_name, server_config):
        """
        根据知识库内容和文件内容,检索一下知识库，获取几个chunk
        """
        data = {
            "query_body": {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "metadata.parent_file_name": file_name
                                }
                            }
                        ]
                    }
                },
                "size": top_k
            },
            "index_name": [knowledge_base_name],
        }
        es_documents = self.es_requests(data, server_config, file_name)
        return es_documents


    def retrieval_elastic(self, chunk, knowledge_base_name, top_k, filter_file_id, server_config, table_pk_list=None,
                          query_condition=None):
        data = {
            "query_body": {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "page_content": chunk
                                }
                            }
                        ]
                    }
                },
                "size": top_k or server_config["retrieval_top_k"]
            },
            "index_name": [knowledge_base_name],
        }
        data["query_body"]["query"]["bool"]["must_not"] = [
            {"term": {"metadata.file_id": int(filter_file_id)}}]
        if table_pk_list:
            data["query_body"]["query"]["bool"]["filter"] = [
                {"terms": {"metadata.source": filter_file_id}}]
        elif query_condition:
            filter_param = []
            for k, v in query_condition.items():
                filter_param.append({"terms": {f"metadata.{k}.keyword": v}})
            if "filter" not in data["query_body"]["query"]["bool"].keys():
                data["query_body"]["query"]["bool"]["filter"] = filter_param
            else:
                data["query_body"]["query"]["bool"]["filter"].extend(filter_param)
        es_documents = self.es_requests(data, server_config, chunk)
        return es_documents

    def es_requests(self, data, server_config, question):
        es_documents = []
        es_url = 'http://' + server_config["es_config"]["host"] + ':' + str(server_config["es_config"]["port"]) + '/'
        response = requests.post(es_url + 'search_by_custom_param', json=data, timeout=30)
        try:
            if response.status_code == 200:
                try:
                    es_data = response.json()['data']['result_data']
                except Exception as e:
                    # logger.error(f"es查询报错{e},{response.text}")
                    # traceback.print_exception(e)
                    print(f"es查询报错{e},{response.text}")
                    return es_documents
            else:
                # logger.error(f"es查询报错,{response.text}")
                print(f"es查询报错,{response.text}")
                return es_documents
        except Exception as e:
            # logger.error(f"es查询报错{e},{response.text}")
            traceback.print_exception(e)
            return es_documents
        for i, x in enumerate(es_data):
            x['_source']['metadata']["search"] = {
                "type": ["es"],
                "query": question,
                "rank": [i],
                "score": x['_score']
            }
            es_documents.append(Document(page_content=x['_source']['page_content'], metadata=x['_source']['metadata']))
        return es_documents

    def create_version_id(self, file_name):
        """
        根据文件名称创建文件ID
        创建版本ID
        """
        def string_to_uuid(input_str: str):
            """
            根据字符串生成 UUID
            """
            namespace = uuid.NAMESPACE_URL  # 也可换用其他命名空间（如 NAMESPACE_OID）
            return uuid.uuid5(namespace, input_str)
        # 示例
        uuid_id = string_to_uuid(file_name)
        uuid_part = uuid_id.urn
        match = re.search(r'urn:uuid:(.*)', uuid_id.urn)
        if match:
            uuid_part = match.group(1)
        return uuid_part

    def get_version_date(self, file_name, knowledge_base_name, server_config):
        es_url = 'http://' + server_config["es_config"]["host"] + ':' + str(server_config["es_config"]["port"]) + '/'
        data = {
            "query_body": {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"metadata.parent_file_name.keyword": file_name}},
                            {"term": {"metadata.chunk_index": 0}}
                        ]
                    }
                },
                "size": 1  # 只取第一个chunk
            },
            "index_name": [knowledge_base_name]  # ES索引名
        }
        try:
            response = requests.post(es_url + 'search_by_custom_param', json=data)
            if response.status_code != 200:
                print(f"查询ES失败: {response.text}")
                return ""
            elif response.json()['code'] != 200:
                print(f"查询ES失败: {response.text}")
                return ""
        except Exception as e:
            print(f"查询ES失败: {e}")
            return ""
        try:
            response.raise_for_status()
            res = response.json().get("data", {}).get("result_data", [])
            # print(json.dumps(res, indent=4, ensure_ascii=False))
            if res:
                chunk = res[0]['_source']['page_content']
            else: 
                print(f"结果为空")
                return ""
            # print(f"Chunk: {chunk}")
            version_extract_prompt = f'''请你从给定的文件名 $file_name$ 以及文件中的一段文本块 $chunk$ 中提取出文件版本的时间信息。请你按照以下步骤完成：
    1. 如果文件名中含有文件版本的时间信息，请你直接返回该时间
    2. 如果文件名中不含有文件版本的时间信息，请你从给定的文本块中提取出文件版本的时间信息，并返回该时间
    3. 如果文件名和给定的文本块中都不包含文件版本的时间信息，请你直接返回False

    如果返回的不是False，请你按照以下的时间格式输出结果：
    1. 如果时间包含具体的年、月、日信息，则以 XXXX-XX-XX 的格式返回（如2025-07-06)
    2. 如果时间仅包含年份，则以 XXXX-01-01 的格式返回（如仅识别出2025年的时候，返回2025-01-01）
    
    仅输出时间结果，不要生成其他内容，否则会带来严重后果！
    '''
            user_prompt = f'''
    file_name: {file_name}
    chunk: {chunk}
    '''
            payload = {
                'model': self.model_info.model_id,
                "messages": 
                [
                    {"role": "system", "content": version_extract_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            }
            headers = {'Content-Type': 'application/json'}
            api_key = self.model_info.key
            if api_key:
                headers['Authorization'] = api_key
            llm_url = self.model_info.url
            base_response = requests.post(llm_url, json=payload, headers=headers)
            base_response = base_response.text.split('\r\n')[0]
            version_date =  json.loads(base_response)['choices'][0]['message']['content'].split('</think>')[-1].strip()
            if "False" in version_date:
                version_date = ""
            try:
                version_date = re.search(r'\b(\d{4}-\d{1,2}-\d{1,2})\b', version_date)[0]
            except Exception as e:
                print(f"版本时间：{version_date}")
                print(f"提取版本时间失败: {e}")
            return version_date
        except Exception as e:
            print(f"请求大模型失败: {e}")
            traceback.print_exc()
            return ""


if __name__ == "__main__":
    file_name_list = ["中华人民共和国反洗钱法 (2023 年修订) .pdf ","中华人民共和国反洗钱法 (2024 年修订) .png"]
    file_dict = by_file_name(file_name_list)
    print(file_dict)

