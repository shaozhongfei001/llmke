import copy
import json
import re
from typing import List

import numpy as np
import pandas as pd
from langchain.text_splitter import RecursiveCharacterTextSplitter
from xgboost import XGBClassifier

from deepdoc.output_object import ParsedText, ParsedTextMetadata
from .utils import naive_merge

# 标题的最大层级数
MAX_LEVEL = 12

# 不属于任何标题模式的文本层级
PLAIN_TEXT_LEVEL = 0

# 每一级标题的正则格式 project_pattern 和对应的等级level。
# level数值越小，标题越大。
PROJECT_PATTERNS = [
    (r"第+[零一二三四五六七八九十百0-9]+[章部分]+", 1),
    ("附件[：:]", 1),
    (r"第+[零一二三四五六七八九十百0-9]+[条节]+", 2),
    (r"[零一二三四五六七八九十百]+[、． 　]", 3),
    (r"[\(（][零一二三四五六七八九十百]+[）\)]", 4),
    (r"[0-9]+(、|\.[　 ]|．|\.[^0-9])", 5),
    (r"[0-9]+\.[0-9]+\.[0-9]+(、|[ 　]|[^0-9])", 7),
    (r"[0-9]+\.[0-9]+(、|[ 　]|[^0-9])", 6),
    (r"[0-9]+", 5),
    (r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+(、|[ 　]|[^0-9])", 8),
    (r".{,48}[：:?？]@", 9),
    (r"[0-9]+）", 10),
    (r"[\(（][0-9]+[）\)]", 11),
    (r"[零一二三四五六七八九十百]+是", 12),
    (r"[⚫•➢✓ ]", 12)
]

xg_splitter_model = XGBClassifier()
xg_splitter_model.load_model("deepdoc/splitter/xg_splitter.json")


def get_project_levels(lines):
    """判断每一行文本的标题层级，返回层级矩阵"""
    mat = [PLAIN_TEXT_LEVEL for _ in range(len(lines))]
    for i in range(len(lines)):
        mat[i] = get_project_level(lines[i])
    return mat


def get_project_level(line) -> int:
    """匹配标题等级，从高到底匹配"""
    cleaned_line = clean_outlier_text(line)
    for p, j in PROJECT_PATTERNS:
        if re.match(p, cleaned_line):
            return j
    return PLAIN_TEXT_LEVEL


# def _remove_tag_and_lf(text: str) -> str:
#     return re.sub('@@[\t0-9.-]+?##|[\r\n]', '', text)
#
#
# def _cut_string_by_length(string: str, length: int) -> list[str]:
#     return [string[i:i + length] for i in range(0, len(string), length)]
#
#
# def _garbage(txt):
#     patt = [
#         r"(在此保证|不得以任何形式翻版|请勿传阅|仅供内部使用|未经事先书面授权)",
#         r"(版权(归本公司)*所有|免责声明|保留一切权力|承担全部责任|特别声明|报告中涉及)",
#         r"(不承担任何责任|投资者的通知事项：|任何机构和个人|本报告仅为|不构成投资)",
#         r"(不构成对任何个人或机构投资建议|联系其所在国家|本报告由从事证券交易)",
#         r"(本研究报告由|「认可投资者」|所有研究报告均以|请发邮件至)",
#         r"(本报告仅供|市场有风险，投资需谨慎|本报告中提及的)",
#         r"(本报告反映|此信息仅供|证券分析师承诺|具备证券投资咨询业务资格)",
#         r"^(时间|签字|签章)[:：]",
#         r"(参考文献|目录索引|图表索引)",
#         r"[ ]*年[ ]+月[ ]+日",
#         r"^(中国证券业协会|[0-9]+年[0-9]+月[0-9]+日)$",
#         r"\.{10,}",
#         r"(———END|帮我转发|欢迎收藏|快来关注我吧|手机扫一扫打开此页)"
#     ]
#     return any([re.search(p, txt) for p in patt])


def clean_outlier_text(text: str) -> str:
    """清除读取中异常的情况:
        1. 叠词: '第第十十一一条条'  -> '第十一条'
    """
    text = re.sub("[\u3000\xa0]", " ", text).strip()
    reduplicated_matches = []
    count = 0

    # 正则判断连续的叠词
    for match in re.finditer(r"(\S)\1+", text):
        if count == 0:
            reduplicated_matches.append(match)
            count += 1
        else:
            if reduplicated_matches and match.start() == reduplicated_matches[-1].end():  # 连续的
                reduplicated_matches.append(match)
                count += 1
            else:
                if count <= 2:  # 过滤"快快乐乐" 这种情况
                    reduplicated_matches.pop()
                reduplicated_matches.append(match)
                count = 1

    if len(reduplicated_matches) == 1 or count == 1:
        reduplicated_matches.pop()

    cleaned_text = ""
    i = 0
    for match in reduplicated_matches:
        cleaned_text = cleaned_text + text[i:match.start()]
        if re.search("[0-9a-zA-Z]", match.group()):  # 英文数字不清洗
            cleaned_text = cleaned_text + match.group()
        else:
            cleaned_text = cleaned_text + match.group()[0]
        i = match.end()
    cleaned_text = cleaned_text + text[i:]
    return cleaned_text


class TreeNode:
    def __init__(self, text, chunk_positions, project_level,
                 children=None,
                 parent=None,
                 metadata: ParsedTextMetadata = None,
                 is_doc_root=False):
        self.text = text  # 当前节点的文本
        self.metadata = metadata or dict()
        self.project_level = project_level
        self.pos = chunk_positions
        self.is_doc_root = is_doc_root
        self.children = children or []
        self.parent = parent
        self.path = []
        self.tree = [self]

    def __repr__(self):
        return self.text

    @classmethod
    def from_root(cls, file_name = ""):
        """创建根节点 根节点默认为文件名节点"""
        return TreeNode(file_name, [[0, 0]], 0, is_doc_root=True)

    @property
    def node_chunk(self):
        """当前节点下所有子孙节点包含的文本，对于根节点来说，就是全文内容。"""
        return "\n".join(node.text for node in self.tree)


class DocTree:
    def __init__(self):
        self.page_content = ""
        self.root = TreeNode.from_root()
        self.nodes = []

    # @staticmethod
    # def _merge(lines, chunk_positions, projects):
    #     """
    #     将同一个层级的多行内容合并
    #         第二节 aaaa...
    #         aaaa
    #         第三节 bbb...
    #         bbb
    #         bbb
    #     """
    #     # merge continuous same level and non-title text
    #
    #     if not lines:
    #         return [], [], []
    #     merged_lines = []
    #     merged_positions = []
    #     merged_projects = []
    #
    #     for i, (line, proj, pos) in enumerate(zip(lines, projects, chunk_positions)):
    #         if i == 0:
    #             merged_lines.append(line)
    #             merged_projects.append(proj)
    #             merged_positions.append(pos)
    #             continue
    #
    #         if proj == 0:
    #             # 0 代表没有被任何标题模版匹配
    #             merged_lines[-1] = "\n".join([merged_lines[-1], line])
    #             # 更新chunk坐标位置
    #             merged_positions[-1][1] = pos[1]
    #         else:
    #             merged_lines.append(line)
    #             merged_positions.append(pos)
    #             merged_projects.append(proj)
    #     # for line, pos, proj in zip(merged_lines, merged_positions, merged_projects):
    #     #     print(proj, line, pos)
    #     return merged_lines, merged_positions, merged_projects

    @staticmethod
    def _merge_documents(documents: List[ParsedText], project_levels) -> (List[ParsedTextMetadata], List[int]):
        """
        将同一个层级的多行内容合并
            第二节 aaaa...
            aaaa
            第三节 bbb...
            bbb
            bbb
        """
        # merge continuous same level and non-title text
        if not documents:
            return []
        merged_projects = []
        merged_documents = []
        for i, (document, proj) in enumerate(zip(documents, project_levels)):
            line = document.page_content
            pos = document.metadata.offset

            if i == 0 or proj != PLAIN_TEXT_LEVEL:  # 第一个document or 是标题行
                merged_documents.append(copy.deepcopy(document))
                merged_projects.append(proj)
            else:
                merged_documents[-1].page_content = "\n".join([merged_documents[-1].page_content, line])
                # 更新chunk坐标位置
                merged_documents[-1].metadata.offset.extend(pos)
                merged_documents[-1].metadata.position += document.metadata.position
                merged_documents[-1].metadata.page_number += document.metadata.page_number
                merged_documents[-1].metadata.page_size += document.metadata.page_size
        return merged_documents, merged_projects

    # def build_from_text(self, text: str) -> TreeNode:
    #     lines = []
    #     chunk_positions = []
    #     last_position = 0
    #     self.page_content = text
    #     if not text:
    #         return self.root
    #
    #     """数据清洗和坐标记录"""
    #     if re.search('[\r\n]', text):
    #         for match in re.finditer('[\r\n]', text):  # 换行切分符
    #             start, end = last_position, match.start()
    #             line = text[start:end]
    #             line = re.sub("[\u3000\xa0]", " ", line).strip()
    #             line = clean_outlier_text(line)
    #             if line:  # 清洗无用语句
    #                 lines.append(line)
    #                 chunk_positions.append([start, end])
    #             last_position = end
    #     else:
    #         lines.append(text)
    #         chunk_positions.append([0, len(text)])
    #
    #     # 判断每一行是否是标题
    #     mat = self.get_project_levels(lines)
    #
    #     # 将非标题行合并入标题行中
    #     lines, chunk_positions, mat = self._merge(lines, chunk_positions, mat)
    #
    #     # 初始化tree
    #     temp = [None for _ in range(self.MAX_LVL + 1)]
    #     temp[0] = self.root
    #
    #     # 创建树结构
    #     for text, pos, proj in zip(lines, chunk_positions, mat):
    #         assert proj is not None, (proj, text)
    #         node = TreeNode(text, chunk_positions=pos, project_level=proj)
    #         self.nodes.append(node)
    #         if proj == 0:
    #             node.parent = temp[0]
    #             temp[0].children.append(node)
    #         else:
    #             i = proj - 1
    #             while temp[i] is None:  # 从大到小找最近的小于当前节点等级的标题，标题3按序找最近的标题2/1/0
    #                 i -= 1
    #             assert isinstance(temp[i], TreeNode)
    #             node.parent = temp[i]
    #             temp[i].children.append(node)
    #             temp[proj] = node
    #
    #     # 深度递归获取每个节点做根节点的文本长度
    #     self.update_tree(self.root, [])
    #     # print(self.root.__dict__)
    #     return self.root

    @classmethod
    def from_documents(cls, documents: List[ParsedText]):
        """构建文档树，利用行首的正则匹配结果来构建文档树"""
        doc_tree = DocTree()
        lines = [doc.page_content for doc in documents]
        doc_tree.page_content = "\n".join(lines)

        if not lines:
            return doc_tree

        # 判断每一行是否是标题
        mat = get_project_levels(lines)
        # 将非标题行合并入标题行中
        merged_documents, merged_mat = cls._merge_documents(documents, mat)

        # 创建层级结构
        for document, proj in zip(merged_documents, merged_mat):
            text = document.page_content
            assert proj is not None, (proj, text)
            node = TreeNode(text, chunk_positions=document.metadata.offset, project_level=proj,
                            metadata=document.metadata)

            if proj == PLAIN_TEXT_LEVEL:
                node.parent = doc_tree.root
                node.parent.children.append(node)
            else:
                i = len(doc_tree.nodes) - 1
                while i >= 0 and doc_tree.nodes[i].project_level >= proj:
                    i -= 1

                if i >= 0:
                    parent_node = doc_tree.nodes[i]
                else:
                    parent_node = doc_tree.root
                node.parent = parent_node
                parent_node.children.append(node)
            doc_tree.nodes.append(node)

        # 深度递归获取每个节点做根节点的文本长度
        doc_tree.update_tree(doc_tree.root, [])
        return doc_tree

    def update_tree(self, node: TreeNode, path):
        """更新根节点为node的文档树 深度递归"""

        node.path = path
        if not node.children:
            return node.tree
        for child in node.children:
            # child.tree = self.update_tree(child, path + [node.text])
            child.tree = self.update_tree(child, path + node.path)
            node.tree.extend(child.tree)
        return node.tree

    def verify(self, node: TreeNode):
        if node is None:
            return
        # print(1, text[node.pos[0]:node.pos[1]].strip())
        # print(2, node.text.strip())
        # print(node.path)
        print(node.project_level)
        for child in node.children:
            self.verify(child)


def get_tree_feature(doc_tree: DocTree):
    proj_count = dict()
    proj_count["file"] = {"all_node_count": len(doc_tree.nodes), "all_level": set()}

    for node in doc_tree.nodes:
        # print(node.project_level, len(node.node_chunk), node.text)
        if node.project_level == 0 and node.text == "<文件名>":
            pass
        elif node.project_level not in proj_count:
            proj_count[node.project_level] = {
                "chunk_lengths": [len(node.node_chunk)],
                "chunk_start": node.pos[0][0],
                "chunk_end": node.pos[-1][1]
            }
        else:
            proj_count[node.project_level]["chunk_lengths"].append(len(node.node_chunk))
            proj_count[node.project_level]["chunk_end"] = node.pos[-1][1]
        proj_count["file"]["all_level"].add(node.project_level)
    # print(proj_count)
    return proj_count


def create_feature(doc_tree):
    data = []
    doc_tree_feature = get_tree_feature(doc_tree)
    file_feature = doc_tree_feature.pop("file")
    node_projs = sorted(file_feature["all_level"])

    text = doc_tree.root.node_chunk
    # 构造特征
    for proj_level, feature_dict in doc_tree_feature.items():
        chunk_lengths = feature_dict.pop("chunk_lengths")
        f = {
            "file": "",
            "label": "",
            "content_length": len(text),
            "node_count": len(node_projs),
            "cur_node_level": node_projs.index(proj_level) / len(node_projs),
            "proj": proj_level,
            "count": len(chunk_lengths),
            "node_freq": len(chunk_lengths) / file_feature["all_node_count"],
            "avg": np.mean(chunk_lengths),
            "std": np.std(chunk_lengths),
            "min": min(chunk_lengths) / len(text),
            "max": max(chunk_lengths) / len(text),
            "median": np.median(chunk_lengths),
            "start": feature_dict["chunk_start"] / len(text),
            "end": feature_dict["chunk_end"] / len(text),
            "coverage_freq": sum(chunk_lengths) / len(text),
            "below_700": 1 if np.mean(chunk_lengths) <= 700 else 0,
        }
        data.append(f)

    return pd.DataFrame(data)


def get_split_label(doc_tree):
    feature_df = create_feature(doc_tree)
    y = xg_splitter_model.predict(feature_df.drop(["label", "file", "proj"], axis=1))
    splitter_labels = feature_df[y == 1]["proj"].tolist()
    return splitter_labels


class IntelSectionSplitter(RecursiveCharacterTextSplitter):
    """利用文章结构（章节条）切分chunk
        对于符合文本模版的文本优先按照结构切分
        如果没有找到匹配的模版，使用递归切分按照设定的separators进行切分。

    Usage:
        splitter = SectionSplitter(chunk_size=200, chunk_overlap=0, separators=["。", "？", "！", "，"])

    """

    def __init__(self, **kwargs):
        super(IntelSectionSplitter, self).__init__(**kwargs)
        self._chunk_size = kwargs.get("chunk_size", 500)
        self._chunk_overlap = kwargs.get("chunk_overlap", 0)
        self._keep_separator = "end"

    # def split_text(self, text: str, file_name=None) -> [str, [int, int], [str]]:
    #     """
    #     递归遍历树状节点，添加或者合并文本块
    #     return: 文本块, 文本块在全文中的字符串坐标, 从根节点出发访问该文本块的路径
    #     """
    #     chunk_nodes = []
    #
    #     def _split_by_tree(node_: TreeNode, cur_nodes: [TreeNode]):
    #         node_length = self._length_function(node_.node_chunk)
    #         cur_chunk_length = sum([self._length_function(node.text) for node in cur_nodes])
    #
    #         if cur_chunk_length >= self._chunk_size * 0.9:
    #             chunk_nodes.append(cur_nodes)
    #             return [], 0
    #
    #         # Scenario1: 将当前节点树中的所有文本都并入chunk中
    #         if node_length + cur_chunk_length < self._chunk_size * 0.9:
    #             cur_nodes.extend(node_.tree)
    #             cur_chunk_length += self._length_function(node_.node_chunk)
    #             return cur_nodes, cur_chunk_length
    #
    #         # Scenario2: 当前节点树本身字数和chunk_size比较接近，可以成为一个独立的chunk
    #         if 0.7 <= node_length / self._chunk_size <= 1.1:
    #             chunk_nodes.append(cur_nodes)  # chunk 不能包含不连贯的文本段，所以清空cur_chunk
    #             chunk_nodes.append(node_.tree)
    #             return [], 0
    #
    #         # Scenario3: 无法包括整棵节点树，就尽可能地合并连续孩子节点。针对孩子节点进行递归，重复。
    #         i = 0
    #         cur_nodes.append(node_)
    #         cur_chunk_length += self._length_function(node_.text)
    #
    #         while i < len(node_.children):
    #             if cur_chunk_length >= self._chunk_size * 0.9:
    #                 chunk_nodes.append(cur_nodes)
    #                 cur_nodes = []
    #                 # cur_chunk_length = 0
    #
    #             child = node_.children[i]
    #             cur_nodes, cur_chunk_length = _split_by_tree(child, cur_nodes)
    #             i += 1
    #
    #         # 同级的大多数chunk都被合并成前一条chunk的情况下和前一条合并，尽量保证一棵树完整地在一个chunk中。
    #         if len(chunk_nodes) != 0 and cur_chunk_length <= self._chunk_size * 0.2:
    #             chunk_nodes[-1].extend(cur_nodes)
    #         else:
    #             chunk_nodes.append(cur_nodes)
    #
    #         return [], 0
    #
    #     doc_tree = DocTree(file_name)
    #     doc_tree.create_by_text(text)
    #
    #     sub_nodes, _ = _split_by_tree(doc_tree.root, [])
    #
    #     if sub_nodes:
    #         chunk_nodes.append(sub_nodes)
    #
    #     chunks = []
    #     for i, nodes in enumerate(chunk_nodes):
    #         if not nodes:
    #             continue
    #
    #         chunk_text = "\n".join([node.text for node in nodes])
    #         chunk_offset = [nodes[0].pos[0], nodes[-1].pos[1]]
    #         chunk_path = nodes[0].path
    #
    #         if self._length_function(chunk_text) >= self._chunk_size * 3:
    #             texts = self._split_text(chunk_text, self._separators)
    #             start = chunk_offset[0]
    #
    #             for i, t in enumerate(texts):
    #                 if i == 0:
    #                     t = t.lstrip(doc_tree.root.text)
    #                 if len(t.strip()) <= 2:
    #                     continue
    #                 end = start + len(t)  # 这里的切分方式可能导致offset 记录不准，因为进行了数据清洗。
    #                 text_offset = [start, end]
    #                 chunks.append([t, text_offset, chunk_path])
    #                 start = end
    #         else:
    #             chunks.append([chunk_text, chunk_offset, chunk_path])
    #     return chunks

    @staticmethod
    def line_documents(parsed_results: List[ParsedText]) -> List[ParsedText]:
        """
            不同的文件解析后形式不一样，例：pdf解析后每行为一个document, txt解析后一整份文件为一个document。
            为处理以上情况将解析结果统一为每一行为一个documents，并且保证记录坐标。
        """
        lined_documents = []
        for doc in parsed_results:
            text = doc.page_content
            # assert len(doc.metadata["offset"]) == 1, doc  # offset: [[0, 0]]
            abs_start, abs_end = doc.metadata.offset[0]  # 在全文中的绝对位置

            if re.search('[\r\n\t]', text):
                p = 0
                for match in re.finditer('[\r\n\t]', text):  # 换行切分符
                    p_start, p_end = p, match.start()  # text 的相对位置
                    line = text[p_start:p_end]
                    # line = clean_outlier_text(line)
                    if line:
                        metadata = copy.deepcopy(doc.metadata)
                        metadata.offset = [[abs_start + p_start, abs_start + p_end]]
                        lined_documents.append(ParsedText(page_content=line, metadata=metadata))
                    p = match.end()

                line = text[p:]
                if line:
                    start, end = p, abs_end
                    metadata = copy.deepcopy(doc.metadata)
                    metadata.offset = [[abs_start + start, end]]
                    lined_documents.append(ParsedText(page_content=line, metadata=metadata))
            else:
                # line = clean_outlier_text(text)
                lined_documents.append(ParsedText(page_content=text, metadata=doc.metadata))
        # for i, line in enumerate(lined_documents):
        #     print(i, line.metadata["offset"], line.page_content)
        #     print("*"*100)
        return lined_documents

    def split_documents2(self, documents: List[ParsedText]):
        """文档树切分
        :param documents: 一份文件的文本读取结果
        """
        # with open("doc_parse.json", "w") as f:
        #     json.dump([dict(doc) for doc in documents], f, indent=4, ensure_ascii=False)
        chunk_nodes = []

        def _split_tree(node_: TreeNode, cur_nodes: [TreeNode]):
            """根据chunk size归并node为根节点的这棵文档子树，以node为最小单位"""
            node_length = self._length_function(node_.node_chunk)
            cur_chunk_length = sum([self._length_function(node.text) for node in cur_nodes])

            if cur_chunk_length >= 0.9 * self._chunk_size:
                chunk_nodes.append(cur_nodes)
                return [], 0

            # Scenario1: 将当前节点树中的所有文本都并入chunk中
            if node_length + cur_chunk_length < 1.3 * self._chunk_size:
                cur_nodes.extend(node_.tree)
                cur_chunk_length += self._length_function(node_.node_chunk)
                return cur_nodes, cur_chunk_length

            # Scenario2: 当前节点树本身字数和chunk_size比较接近，可以成为一个独立的chunk
            if 0.7 * self._chunk_size <= node_length <= 1.3 * self._chunk_size:
                chunk_nodes.append(cur_nodes)  # chunk 不能包含不连贯的文本段，所以清空cur_chunk
                chunk_nodes.append(node_.tree)
                return [], 0

            # Scenario3:
            if 0.4 * self._chunk_size <= node_length < 0.7 * self._chunk_size:
                chunk_nodes.append(cur_nodes)
                return node_.tree, node_length

            # Scenario4: 无法包括整棵节点树，就尽可能地合并连续孩子节点。针对孩子节点进行递归，重复。
            if cur_nodes != [] and node_.project_level < cur_nodes[0].project_level:
                chunk_nodes.append(cur_nodes)
                cur_nodes, node_length = _split_tree(node_, [])
            else:
                i = 0
                cur_nodes.append(node_)
                cur_chunk_length += self._length_function(node_.text)
                # fixme: 如果只把一颗子树的根节点加入前一个节点，那么就违背原则了
                while i < len(node_.children):
                    if cur_chunk_length >= self._chunk_size * 0.9:
                        chunk_nodes.append(cur_nodes)
                        cur_nodes = []
                        # cur_chunk_length = 0
                    # if i == 0:
                    #     child = node_.children[i]
                    #     child.text = node_.text + child.text
                    #     child.node_chunk = node_.text + child.node_chunk
                    #     child.tree.insert(0, node_)
                    # else:
                    #     child = node_.children[i]
                    child = node_.children[i]
                    cur_nodes, cur_chunk_length = _split_tree(child, cur_nodes)
                    i += 1

            # 同级的大多数chunk都被合并成前一条chunk的情况下和前一条合并，尽量保证一棵树完整地在一个chunk中。
            if len(chunk_nodes) != 0 and cur_chunk_length <= self._chunk_size * 0.2:
                chunk_nodes[-1].extend(cur_nodes)
            else:
                chunk_nodes.append(cur_nodes)

            return [], 0

        lined_documents = self.line_documents(documents)  # 按换行切分文件
        doc_tree = DocTree.from_documents(lined_documents)
        # get_tree_feature(doc_tree.root)
        sub_nodes, _ = _split_tree(doc_tree.root, [])
        if sub_nodes:
            chunk_nodes.append(sub_nodes)

        chunks = []
        for i, nodes in enumerate(chunk_nodes):
            if i == 0 and nodes != []:
                nodes.pop(0)
            if not nodes:
                continue

            chunk_texts = []
            chunk_offset = []
            for node in nodes:
                if node.is_doc_root:
                    continue
                chunk_texts.append(node.text)
                chunk_offset.extend(node.pos)

            chunk_text = "\n".join(chunk_texts)
            chunk_path = nodes[0].path
            if nodes[0].is_doc_root:
                metadata = nodes[-1].metadata  # 取-1 因为 0 可能是根节点，没有metadata
            else:
                metadata = nodes[0].metadata
            metadata.offset = chunk_offset

            merged_offset = []
            for i, (a, b) in enumerate(metadata.offset):
                if i == 0:
                    merged_offset.append([a, b])
                else:
                    if a == merged_offset[-1][1] or a == merged_offset[-1][1] + 1:
                        merged_offset[-1][1] = b
                    else:
                        merged_offset.append([a, b])

            # 长度超过chunk size的3倍以上，利用句子进行进一步切分。
            if self._length_function(chunk_text) >= self._chunk_size * 3 and len(merged_offset) == 1:
                texts = self._split_text(chunk_text, self._separators)
                start = merged_offset[0][0]

                for i, t in enumerate(texts):
                    end = start + len(t)
                    text_offset = [[start, end]]
                    if len(t.strip()) >= 2:
                        metadata.offset = text_offset
                        # metadata.title_path = chunk_path
                        t = chunk_path + t
                        chunks.append(ParsedText(page_content=t, metadata=copy.deepcopy(metadata)))
                    start = end
            else:
                metadata.offset = merged_offset
                # metadata.title_path = chunk_path
                chunks.append(ParsedText(page_content=chunk_text, metadata=metadata))
        return chunks

    def find_overlap(self, str1: str, str2: str, max_overlap: int = None, case_sensitive: bool = True) -> tuple[int, int, int, str]:
        """
        查找第一个字符串的结尾与第二个字符串的开头的最大重叠部分

        参数:
            str1: 第一个字符串（取结尾部分）
            str2: 第二个字符串（取开头部分）
            max_overlap: 最大允许的重叠长度（默认 None 表示不限制，取两个字符串长度的较小值）
            case_sensitive: 是否大小写敏感（默认 True，区分大小写）

        返回:
            tuple: (s1 长度,重叠长度, 重叠字符串)，无重叠时返回 (0, "")
        """
        # 处理大小写不敏感的情况
        if not case_sensitive:
            s1 = str1.lower()
            s2 = str2.lower()
        else:
            s1 = str1
            s2 = str2

        # 确定最大可能的重叠长度（不能超过任一字符串的长度）
        s1_len, s2_len = len(s1), len(s2)
        default_max = min(s1_len, s2_len)
        max_len = max_overlap if (max_overlap and max_overlap <= default_max) else default_max

        # 从最大可能长度开始递减查找（确保找到的是最长重叠）
        for overlap_len in range(max_len, 0, -1):
            # 取 str1 的最后 overlap_len 个字符，str2 的前 overlap_len 个字符
            suffix = s1[-overlap_len:] if overlap_len <= len(s1) else ""
            prefix = s2[:overlap_len] if overlap_len <= len(s2) else ""

            if suffix == prefix:
                # 返回原始字符串的重叠部分（保持大小写）
                original_overlap = str1[-overlap_len:] if overlap_len <= len(str1) else ""
                return s1_len, s2_len, overlap_len, original_overlap

        # 无重叠情况
        return s1_len, s2_len, 0, ""


    def split_documents(self, documents: List[ParsedText], file_name=None) -> List[ParsedText]:
        """
        文档树切分
        :param documents: 单文件来源的文本读取结果
        """
        # 打开一个文件，准备写入pickle数据
        # import pickle
        # with open('./documents.pkl', 'wb') as file:
        #     # 将对象序列化并写入文件
        #     pickle.dump(documents, file)
        lined_documents = self.line_documents(documents)  # 按换行切分文件
        doc_tree = DocTree.from_documents(lined_documents)
        # for node in doc_tree.nodes:
        #     print("*", node)
        split_labels = get_split_label(doc_tree)

        if len(split_labels) == 0 or 0 in split_labels:  # 没有找到合适的切分依据
            return naive_merge(documents, self._chunk_size, self._length_function)
        else:
            chunk_nodes = []
            visited_node = set()
            for node in doc_tree.nodes:
                if node in visited_node or node.is_doc_root:
                    continue
                if node.project_level in split_labels:
                    chunk_nodes.append(node.tree)
                    visited_node = visited_node.union(node.tree)
                elif node.project_level == 0:
                    chunk_nodes.append([node])
                    visited_node.add(node)
                elif node.project_level < min(split_labels):  # 当前标题级别大于切分层级
                    if len(node.node_chunk) <= self._chunk_size:
                        chunk_nodes.append(node.tree)
                        visited_node = visited_node.union(node.tree)
                    else:
                        chunk_nodes.append([node])
                        visited_node.add(node)
                else:
                    chunk_nodes.append([node])
                    visited_node.add(node)

        chunks = []
        chunk_index = 1
        sum_document_len = 0
        while chunk_nodes:
            nodes = chunk_nodes.pop(0)
            text = "\n".join(n.text for n in nodes)
            metadata = copy.deepcopy(nodes[0].metadata)
            proj_level = nodes[0].project_level
            chunk_path = nodes[0].path
            metadata.position = []
            metadata.page_number = []
            metadata.page_size = []
            offset = []
            for n in nodes:
                offset.extend(n.pos)
                metadata.position += n.metadata.position
                metadata.page_number += n.metadata.page_number
                metadata.page_size += n.metadata.page_size
            while chunk_nodes and len(text + "\n" + "\n".join(n.text for n in chunk_nodes[0])) <= self._chunk_size * 1 and chunk_nodes[0][0].project_level >= proj_level:
                nodes = chunk_nodes.pop(0)
                text = text + "\n" + "\n".join(n.text for n in nodes)
                chunk_path = nodes[0].path
                for n in nodes:
                    offset.extend(n.pos)
                    metadata.position += n.metadata.position
                    metadata.page_number += n.metadata.page_number
                    metadata.page_size += n.metadata.page_size

            # 长度超过chunk size的3倍以上，利用句子进行进一步切分。
            if self._length_function(text) > self._chunk_size * 1 :
                 # 创建一个新的meatdata
                # 定义获取位置范围内的坐标索引函数
                texts = self._split_text(text, self._separators)
                start = offset[0][0]
                for i, t in enumerate(texts):
                    new_meta_data = copy.deepcopy(metadata)
                    len_t = len(t.replace("\n", ""))
                    begin_add = False
                    new_meta_data.offset = []
                    new_meta_data.position = []
                    new_meta_data.page_number = []
                    new_meta_data.page_size = []
                    have_equal = False
                    documents_len = len(documents)
                    for document_index in range(documents_len):
                        document = documents[document_index]
                        if len(document.metadata.position) >  len(document.metadata.page_number):
                            document.metadata.position = document.metadata.position[0:len(document.metadata.page_number)]
                        start_add_position = document.metadata.offset[0][0]
                        if document_index + 1 < documents_len:
                            next_start_add_position = documents[document_index+1].metadata.offset[0][0]
                        else:
                            next_start_add_position = start_add_position
                        if start_add_position == start:
                            begin_add = True
                        elif start_add_position < start < next_start_add_position:
                            begin_add = True
                        if begin_add:
                            sum_document_len = sum_document_len + len(document.page_content.replace("\n", ""))
                        if sum_document_len > len_t:
                            if len(new_meta_data.offset) == 0:
                                new_meta_data.offset.extend(document.metadata.offset)
                                new_meta_data.position.extend(document.metadata.position)
                                new_meta_data.page_number.extend(document.metadata.page_number)
                                new_meta_data.page_size.extend(document.metadata.page_size)
                            if not have_equal:
                                s1_len, s2_len, up_overlap_len, up_original_overlap = self.find_overlap(t,
                                                                                  documents[document_index - 1].page_content.replace("\n",
                                                                                                                ""))
                                s1_len, s2_len, current_overlap_len, current_original_overlap = self.find_overlap(t,
                                                                                  documents[document_index].page_content.replace("\n",
                                                                                                                ""))
                                if document_index + 1 < documents_len:
                                    s1_len, s2_len, next_overlap_len, next_original_overlap = self.find_overlap(t,
                                                                                                                documents[
                                                                                                                    document_index + 1].page_content.replace(
                                                                                                                    "\n",
                                                                                                                    ""))
                                else:
                                    next_overlap_len = 0
                                sum_document_len = - (
                                            len(document.page_content.replace("\n", "")) - (sum_document_len - len_t))
                                new_meta_data.offset.extend(document.metadata.offset)
                                new_meta_data.position.extend(document.metadata.position)
                                new_meta_data.page_number.extend(document.metadata.page_number)
                                new_meta_data.page_size.extend(document.metadata.page_size)
                                start = document.metadata.offset[0][0]
                                if up_overlap_len == 0 and current_overlap_len ==0 and next_overlap_len > 0:
                                    new_meta_data.offset.extend(documents[document_index + 1].metadata.offset)
                                    new_meta_data.position.extend(documents[document_index + 1].metadata.position)
                                    new_meta_data.page_number.extend(documents[document_index + 1].metadata.page_number)
                                    new_meta_data.page_size.extend(documents[document_index + 1].metadata.page_size)
                                    sum_document_len = - next_overlap_len
                                    chunk_index += 1
                                    start = documents[document_index + 1].metadata.offset[0][0]
                                chunk_index += 1
                            else:
                                sum_document_len = 0
                                chunk_index += 1
                                start = document.metadata.offset[0][0]
                            chunks.append(ParsedText(page_content=t, metadata=copy.deepcopy(new_meta_data)))
                            break
                        elif begin_add and sum_document_len == len_t:
                            new_meta_data.offset.extend(document.metadata.offset)
                            new_meta_data.position.extend(document.metadata.position)
                            new_meta_data.page_number.extend(document.metadata.page_number)
                            new_meta_data.page_size.extend(document.metadata.page_size)
                            have_equal = True
                        elif begin_add:
                            new_meta_data.offset.extend(document.metadata.offset)
                            new_meta_data.position.extend(document.metadata.position)
                            new_meta_data.page_number.extend(document.metadata.page_number)
                            new_meta_data.page_size.extend(document.metadata.page_size)
            else:
                metadata.offset = offset
                metadata.title_path = "|$|".join(chunk_path) #
                metadata.chunk_index = chunk_index
                # try:
                #     t = "\n".join(chunk_path) + "\n" + text
                #     chunks.append(ParsedText(page_content=t, metadata=copy.deepcopy(metadata)))
                # except:
                #     chunks.append(ParsedText(page_content=text, metadata=copy.deepcopy(metadata)))
                chunks.append(ParsedText(page_content=text, metadata=copy.deepcopy(metadata)))
                chunk_index += 1
        #  对chunk的metadata的positon进行去重
        def remove_duplicate_bboxes(data, page):
                """
                根据bbox坐标去重，保持对应的页码信息
                """
                seen = set()
                unique_data = []
                unique_page = []
                len_page = len(page)

                for i, bbox in enumerate(data):
                    # 将bbox转换为可哈希的元组
                    bbox_tuple = tuple(tuple(point) for point in bbox)
                    
                    if bbox_tuple not in seen:
                        seen.add(bbox_tuple)
                        normalized_bbox = [list(point) for point in bbox_tuple]
                        unique_data.append(normalized_bbox)
                        if i < len_page:
                            unique_page.append(page[i])
                return unique_data, unique_page

        for i,chunk in enumerate(chunks):
            position = chunk.metadata.position
            new_pagenum = chunk.metadata.page_number
            # 确保去重后，position 和 page_number 数组里的顺序和长度保持一致
            # print(f"Before removing duplicates: chunk {i} has {len(position)} positions and {len(new_pagenum)} page numbers.")
            new_position,new_pagenum=remove_duplicate_bboxes(position,new_pagenum)
            chunk.metadata.position = new_position
            chunk.metadata.page_number = new_pagenum
            
        return chunks


if __name__ == '__main__':
    # pdf_loader = DirectoryLoader('test_files',
    #                              loader_cls=PDFPlumberLoader,
    #                              glob="**/[!.]*.pdf",
    #                              use_multithvisiteding=True,
    #                              silent_errors=True,
    #                              show_progress=True)
    # parsed_results = pdf_loader.load()
    # documents_group_by_source = {}
    # for document in parsed_results:
    #     if document.metadata['source'] not in documents_group_by_source.keys():
    #         documents_group_by_source[document.metadata['source']] = []
    #     documents_group_by_source[document.metadata['source']].append(document)
    #
    # for source in documents_group_by_source.keys():
    #     print('=' * 10, source, '=' * 10)
    #     joined_text = ''
    #     for document in documents_group_by_source[source]:
    #         joined_text += document.page_content
    #

    splitter = IntelSectionSplitter(chunk_size=500, chunk_overlap=0, separators=['。', '？', '！', '，', "\n"])

    # file = "/Users/daisyli/Coding/Gientech/rag_evaluate/商业银行金融资产风险分类办法.pdf.json"
    # file = "/Users/daisyli/Coding/Gientech/rag_evaluate/doc_parse.json"
    import pickle
    import sys
    # sys.path.append("/")
    file = "./data/documents.pkl"
    with open(file, "rb") as f:
        documents = pickle.load(f)
    # documents = [ParsedText(**item) for item in items]
    # print(len(text))

    res = splitter.split_documents(documents)
    # print(len(res))
    content = " ".join([d.page_content for d in res])
    print(len(content), len(" ".join([doc.page_content for doc in documents])))
    # for doc in documents:
    #     if "".join(doc.page_content.split("\t")) not in content:
    #         print("!!!!!", doc)

    for d in res:
        # print(d.metadata["offset"], len(d.page_content))
        print(d.page_content)
        print(d.metadata.chunk_index)
        print("=" * 100)
        # print(text[d.metadata["offset"][0][0]: d.metadata["offset"][-1][1]], "\n")
        print(d.metadata)
