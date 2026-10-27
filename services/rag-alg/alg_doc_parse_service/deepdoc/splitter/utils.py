import copy
import random
import re
from typing import Any, Callable
from itertools import chain
from log import logger
import tiktoken
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from deepdoc import rag_tokenizer
from deepdoc.output_object import ParsedText, ParsedTextMetadata
from deepdoc.splitter.table_utils.table_index import is_mutli_page_table, merge_multi_page_table

BULLET_PATTERN = [[
    r"第[零一二三四五六七八九十百0-9]+(分?编|部分)",
    r"第[零一二三四五六七八九十百0-9]+章",
    r"第[零一二三四五六七八九十百0-9]+节",
    r"第[零一二三四五六七八九十百0-9]+条",
    r"[\(（][零一二三四五六七八九十百]+[\)）]",
], [
    r"第[0-9]+章",
    r"第[0-9]+节",
    r"[0-9]{,2}[\. 、]",
    r"[0-9]{,2}\.[0-9]{,2}[^a-zA-Z/%~-]",
    r"[0-9]{,2}\.[0-9]{,2}\.[0-9]{,2}",
    r"[0-9]{,2}\.[0-9]{,2}\.[0-9]{,2}\.[0-9]{,2}",
], [
    r"第[零一二三四五六七八九十百0-9]+章",
    r"第[零一二三四五六七八九十百0-9]+节",
    r"[零一二三四五六七八九十百]+[ 、]",
    r"[\(（][零一二三四五六七八九十百]+[\)）]",
    r"[\(（][0-9]{,2}[\)）]",
], [
    r"PART (ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)",
    r"Chapter (I+V?|VI*|XI|IX|X)",
    r"Section [0-9]+",
    r"Article [0-9]+"
]]


def tokenize(d, t, eng):
    d["content_with_weight"] = t
    t = re.sub(r"</?(table|td|caption|tr|th)( [^<>]{0,12})?>", " ", t)
    d["content_ltks"] = rag_tokenizer.tokenize(t)
    d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])


def add_positions(d, poss):
    if not poss:
        return
    d["page_num_int"] = []
    d["position_int"] = []
    d["top_int"] = []
    for pn, left, right, top, bottom in poss:
        d["page_num_int"].append(int(pn + 1))
        d["top_int"].append(int(top))
        d["position_int"].append((int(pn + 1), int(left), int(right), int(top), int(bottom)))


def tokenize(d, t):
    t = re.sub(r"</?(table|td|caption|tr|th)( [^<>]{0,12})?>", " ", t)
    d["content_ltks"] = rag_tokenizer.tokenize(t)
    d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])


def tokenize_chunks(chunks: list[Document], metadata: dict[str, Any], pdf_parser=None) -> list[Document]:
    # wrap up as es documents
    for chunk in chunks:
        if len(chunk.page_content.strip()) == 0:
            continue
        d = copy.deepcopy(metadata)

        # TODO 这部分代码在ragflow的作用是将文本对应的截图提取出来 由于parser和splitter的解耦 这部分暂时停止使用
        if pdf_parser:
            d["image"], poss = pdf_parser.crop(chunk, need_position=True)
            add_positions(d, poss)
        chunk.page_content = re.sub('@@[\t0-9.-]+?##', "", chunk.page_content)
        tokenize(d, chunk.page_content)
        chunk.metadata.update(d)

    return chunks


def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    return len(tiktoken.encoding_for_model('o1').encode(string))


LENGTH_FUNCTIONS = {
    'char': len,
    'token': num_tokens_from_string
}

def query_position_by_offset(slice_offset_start, slice_offset_end, documents):
    new_position = []
    new_page_size = []
    new_page_number = []
    _flag = False
    try:
        
        def find_index(offset, intervals):
            for i, (start, end) in enumerate(intervals):
                if start <= offset <= end:
                    return i
            return -1
        intervals = [doc.metadata.offset[0] for doc in documents]
        start_idx = find_index(slice_offset_start, intervals)
        end_idx = find_index(slice_offset_end, intervals)
        for idx, doc in enumerate(documents):
            if start_idx <= idx <= end_idx:
                new_position.append(doc.metadata.position[0])
                new_page_size.append(doc.metadata.page_size[0])
                new_page_number.append(doc.metadata.page_number[0])
                _flag = True
    except Exception as e:
        logger.exception(f'query_position_by_offset{e}')

    return _flag, new_position, new_page_size, new_page_number


def query_position_by_content(slice_offset_start, slice_offset_end, documents, length_function):
    new_position = []
    new_page_size = []
    new_page_number = []
    _flag = False
    try:

        def find_index(offset, intervals, content_intervals):
            index = -1
            # for i, (start, end) in enumerate(intervals):
            #     if start <= offset <= end:
            #         index = i
            #         break
            if index == -1:
                for i, (start, end) in enumerate(content_intervals):
                    if start <= offset <= end:
                        index = i
                        break
            return index

        # R14-C-FIX-26（A 定位）：短文档/某些段落没有 offset/position/page_size/page_number，
        # 原实现 `doc.metadata.offset[0]` 裸下标 → IndexError → 整个函数 except 后返回
        # `_flag=False` + 三个空列表 → 下游拿到空 position 的块失败 → **ES/Milvus 零写入**，
        # 而 `/parse_sync` 仍返回 success=true（假成功）。日志里该异常累计出现过 1296 次
        # （最早 10-25 10:34），一直被当成"索引失败噪声"。
        # 这里逐条做空值保护：缺失的按空处理并 warn 一次，**不再让单条数据质量问题吃掉整批写入**。
        _miss = [i for i, doc in enumerate(documents)
                 if not (doc.metadata.offset and doc.metadata.position
                         and doc.metadata.page_size and doc.metadata.page_number)]
        if _miss:
            logger.warning(f"query_position_by_content: {len(_miss)}/{len(documents)} 条文档缺 "
                           f"offset/position/page_size/page_number（索引={_miss[:10]}），按空处理，其余块照常写入")
        intervals = [(doc.metadata.offset[0] if doc.metadata.offset else [0, 0]) for doc in documents]
        content_intervals = []
        begin = 0
        for doc in documents:
            end = begin + length_function(doc.page_content)
            content_intervals.append([begin,end])
            begin = end
        start_idx = find_index(slice_offset_start, intervals, content_intervals)
        end_idx = find_index(slice_offset_end, intervals, content_intervals)
        for idx, doc in enumerate(documents):
            if start_idx <= idx <= end_idx:
                new_position.append(doc.metadata.position[0] if doc.metadata.position else [])
                new_page_size.append(doc.metadata.page_size[0] if doc.metadata.page_size else [])
                new_page_number.append(doc.metadata.page_number[0] if doc.metadata.page_number else 0)
                _flag = True
    except Exception as e:
        logger.exception(f'query_position_by_offset{e}')

    return _flag, new_position, new_page_size, new_page_number
        

def naive_merge(
        documents: list[ParsedText],
        max_length=500,
        length_function: Callable[[str], int] = len,
        split_regex=None,
        overlap=50
):
    if split_regex is None:
        # split_regex = ['(?<=[。？！?!])', '(?<=[，,])']
        split_regex = []

    # 如果解析结果存在Document.page_content长度大于上限的Document，则进行非强制切分
    chunks = []
    chunk_sizes = []

    if documents:
        new_document = copy.copy(documents[0])
        metadata = new_document.metadata
        for other_document in documents[1:]:
            new_document.page_content += other_document.page_content
            other_metadata = other_document.metadata
            metadata.position += other_metadata.position
            metadata.page_number += other_metadata.page_number
            metadata.page_size += other_metadata.page_size
            metadata.offset += other_metadata.offset
        page_content = new_document.page_content

        content_slices = recursive_split(page_content, documents, split_regex, max_length, overlap, force=False)

        # slice_offset_start = metadata.offset[0][0]
        start_idx = 0 #仅为find，模糊位置
        for slice_index, content_slice in enumerate(content_slices):
            new_metadata = metadata.model_dump()
            chunk_sizes.append(length_function(content_slice))

            # 处理切分chunk的position
            # 不需要进行切分，而是共用position
            # 为了防止后面合并chunk的时候出现多个重复position
            # 这里会将除了第一个子块外的chunk的position设置为0用来标记
            if slice_index != 0:
                new_metadata['position'] = [[[0, 0]] * 4]

            # 设置新的offset
            slice_offset_start = page_content.find(content_slice, start_idx)

            slice_offset_end = slice_offset_start + len(content_slice)
            new_metadata['offset'] = [[slice_offset_start, slice_offset_end]]
            # slice_offset_start = slice_offset_end
            if start_idx + len(content_slice) - overlap >= 0:
                start_idx = start_idx + len(content_slice) - overlap
            # [设置新的postion、page_number、page_size]
            _flag, new_position, new_page_size, new_page_number = query_position_by_content(slice_offset_start, slice_offset_end, documents, length_function)
            if _flag:
                new_metadata['position'] = new_position
                new_metadata['page_number'] = new_page_number
                new_metadata['page_size'] = new_page_size
            chunks.append(ParsedText(
                page_content=content_slice,
                metadata=ParsedTextMetadata(**new_metadata)
            ))
            slice_offset_start = slice_offset_end
    return chunks


def tokenize_table(tables, metadata):
    for table in tables:
        img = table.metadata.get('image', None)
        rows = table.page_content
        poss = table.metadata.get('position', None)
        if not rows:
            continue

        d = copy.deepcopy(metadata)
        tokenize(d, rows)
        if img:
            d["image"] = img
        if poss:
            add_positions(d, poss)
        table.metadata.update(d)

    return tables


def remove_contents_table(sections: list[Document], english=True):
    i = 0
    while i < len(sections):
        text = sections[i].page_content
        if not re.match(r"(contents|目录|目次|table of contents|致谢|acknowledge)$",
                        re.sub(r"([ \u3000])+", "", text, re.IGNORECASE)):
            i += 1
            continue
        sections.pop(i)
        if i >= len(sections):
            break
        prefix = text[:3] if not english else " ".join(text.split(" ")[:2])
        while not prefix:
            sections.pop(i)
            if i >= len(sections):
                break
            prefix = text[:3] if not english else " ".join(text.split(" ")[:2])
        sections.pop(i)
        if i >= len(sections) or not prefix:
            break
        for j in range(i, min(i + 128, len(sections))):
            if not re.match(prefix, sections[j].page_content):
                continue
            for _ in range(i, j):
                sections.pop(i)
            break


def is_english(documents: list[Document]) -> bool:
    if len(documents) > 50000:
        documents = random.choices(documents, k=50000)
    eng = 0
    texts = list(map(lambda document: document.page_content.strip(), documents))
    if not texts:
        return False
    for text in texts:
        if text and len(re.findall('[a-zA-Z]', text)) / len(text) > 0.5:
            eng += 1
    if eng / len(texts) > 0.8:
        return True
    return False


def group_documents(documents: list[ParsedText]) -> dict[str, list[ParsedText]]:
    """
    可以把所有documents按照source（file_path）进行分组。

    Args:
        documents: Langchain Document对象列表

    Returns:
        一个key-value对应的类型为str-tuple的字典，key对应文件路径字符串，value是一个ParsedText对象列表
    """
    documents_group_by_source = {}
    for document in documents:
        source = document.metadata.file_path
        documents_group_by_source.setdefault(source, []).append(document)

    return documents_group_by_source


def not_bullet(line):
    patt = [
        r"0", r"[0-9]+ +[0-9~个只-]", r"[0-9]+\.{2,}"
    ]
    return any([re.match(r, line) for r in patt])


def bullets_category(sections: list[ParsedText]) -> bool:
    for i, pro in enumerate(BULLET_PATTERN):
        for sec in sections:
            sec = sec.page_content
            for p in pro:
                if re.match(p, sec) and not not_bullet(sec):
                    return True

    return False

def split_slice_by_overlap(sentences, sub_sentences, overlap):
    """句子，根据依据分好的子句，进行overlap，得到slice"""
    slices = []
    max_idx = len(sentences)
    for idx, (sentence, sub_sentence) in enumerate(zip(sentences, sub_sentences)):
        overlap_preceding = ''
        overlap_following = ''
        if idx - 1 > 0:
            for item in reversed(sub_sentences[idx-1]):
                if len(overlap_preceding+item) > int(overlap/2):
                    break
                overlap_preceding = item + overlap_preceding
        if idx + 1 < max_idx:
            for item in sub_sentences[idx+1]:
                if len(overlap_following+item) > int(overlap/2):
                    break
                overlap_following = overlap_following + item
        slices.append(overlap_preceding+sentence+overlap_following)
    return slices


def recursive_split(text: str, documents, regex_separators: list[str], max_length: int, chunk_overlap = int, force=True) -> list:
    # TODO 适配token的切分
    # [按字符列表、再按最大长度]
    if regex_separators:
        for splitter in regex_separators:
            # [考虑转义字符]
            if splitter == '(?<=?)':
                splitter = r'(?<=\?)'
            elif splitter == '(?=?)':
                splitter = r'(?=\?)'
            elif splitter == '(?=.)':
                splitter = r'(?=\.)'
            elif splitter == '(?<=.)':
                splitter = r'(?<=\.)'
            elif splitter == '(?<=\\n\\n)':
                splitter = r'(?<=\n\n)'
            elif splitter == '(?=\\n\\n)':
                splitter = r'(?=\n\n)'
            if '\n\n' in splitter or '\\n\\n' in splitter:
                nested_list = [re.split(splitter, doc.page_content) for doc in documents]
                sentences = list(chain(*nested_list))
            else:
                sentences = re.split(splitter, text)
            sentences = [x for x in sentences if x]
            if chunk_overlap > 0:
                sub_sentences = [re.split('(?<=[，。])', x) for x in sentences]
                sentences = split_slice_by_overlap(sentences, sub_sentences, chunk_overlap)
            
            if len(sentences) > 1:
                if not sentences[-1]:
                    sentences = sentences[:-1]
                return sentences
    if chunk_overlap > max_length:
        chunk_overlap = 0
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_length,  # 每块最大长度
        chunk_overlap=chunk_overlap,  # 块之间的重叠长度
        keep_separator="end",  # 保留且放句尾
        # separators=['。', '？', '！', '，'],  # 不使用分隔符，直接按字符切分
        separators=['。', '？', '！', '，', '.', '?', '!', ','],  # 不使用分隔符，直接按字符切分
    )

    # [执行切分]
    texts = text_splitter.split_text(text)
    return texts


def extract_preceding_context(current_idx, documents, max_idx=7, max_len=150):
    """获取表格的上文
    """
    preceding_context = ""
    for gap in range(1, max_idx):
        if current_idx - gap < 0:
            break
        if documents[current_idx-gap].metadata.type != 'text':
            break
        if len(preceding_context) > max_len:
            break
        preceding_context += documents[current_idx-gap].page_content + '\n'
    return preceding_context


def merge_table_documents(documents, model_info, span_len=4):
    """合并跨页表格"""
    for idx, document in enumerate(documents):
        if document.metadata.type != 'table':
            continue
        if documents[idx].metadata.table_multipage_flag == True:
            continue
        cur_page_content = document.page_content
        for span in range(1, span_len):
            if idx + span >= len(documents) or documents[idx+span].metadata.type !='table':
                break
            merge_flag = is_mutli_page_table(cur_page_content, documents[idx+span].page_content, model_info)
            if not merge_flag:
                break
            documents[idx].metadata.table_multipage_flag = True
            documents[idx+span].metadata.table_multipage_flag = True
            cur_page_content = merge_multi_page_table([cur_page_content, documents[idx+span].page_content])
            documents[idx].metadata.table_html_content = cur_page_content

    return documents
