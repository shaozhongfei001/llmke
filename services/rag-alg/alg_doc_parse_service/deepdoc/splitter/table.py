from tqdm import tqdm

from deepdoc.output_object import ParsedTable, ParsedTableMetadata
from log import set_request_id, request_id
from server.nacos_utils import DocParseConfig
from server.utils import create_uuid, run_in_thread_pool
from .base import BaseSplitter
from .table_utils.table_index import index_table, detect_multiple_tables, summarize_table_full, extract_pipeline


class TableSplitter(BaseSplitter):
    def chunk(self, documents: list[ParsedTable]) -> list[ParsedTable]:
        chunks = []

        @set_request_id(request_id.get())
        def worker(_document, model_info):
            # 判断一个ParsedTable里是否存在多个独立的表格.
            # 例：excel表格内一个sheet可能存在多个独立的表格，需要进一步分离。
            result = [index_table(table, True, model_info) for table in detect_multiple_tables(_document)]
            return result, _document.metadata

        for index_table_results, document_metadata in tqdm(
                run_in_thread_pool(
                    worker,
                    [{'_document': document, 'model_info': self.model_info} for document in documents],
                    stable_order=True,
                    max_workers=DocParseConfig().config.get('table_split_max_worker', 4)
                ),
                total=len(documents),
                desc='表格切分'
        ):
            for table_summary, table_chunks, _ in index_table_results:
                table_id = create_uuid()
                if table_summary and isinstance(table_summary, str):
                    table_metadata = document_metadata.model_dump()
                    table_metadata.update({
                        'pk': table_id,
                        'type': 'table_summary'
                    })
                    chunks.append(ParsedTable(
                        page_content=table_summary,
                        metadata=ParsedTableMetadata(**table_metadata)
                    ))
                for table_string, table_pos in table_chunks:
                    table_metadata = document_metadata.model_dump()
                    table_metadata.update({
                        "offset": table_pos,
                        'pk': create_uuid(),
                        'table_summary_id': table_id
                    })
                    chunks.append(ParsedTable(
                        page_content=table_string,
                        metadata=ParsedTableMetadata(**table_metadata)
                    ))

        return chunks

class FinancialTableSplitter(BaseSplitter):
    def chunk(self, documents: list[ParsedTable]) -> list[ParsedTable]:
        chunks = []

        @set_request_id(request_id.get())
        def worker(_document, user_id, knowledge_base_id, url_table_indicator, model_info):
            # 判断一个ParsedTable里是否存在多个独立的表格.
            # 例：excel表格内一个sheet可能存在多个独立的表格，需要进一步分离。
            result = [index_table(table, False, model_info) for table in detect_multiple_tables(_document)]
            # [全表摘要及三大表抽取]
            if not _document.metadata.table_html_content and not _document.metadata.table_multipage_flag:
                _document.metadata.table_html_content = _document.page_content
            extract_pipeline(_document, user_id, knowledge_base_id, url_table_indicator, model_info)
            full_table_summary = summarize_table_full(_document, model_info)
            
            return result, _document.metadata, full_table_summary

        nacos_config = DocParseConfig().config
        for index_table_results, document_metadata, full_table_summary in tqdm(
                run_in_thread_pool(
                    worker,
                    [{'_document': document, 'user_id': self.user_id, 'knowledge_base_id': self.knowledge_base_id, 
                      'url_table_indicator': nacos_config.get("url_table_indicator"), 
                      'model_info': self.model_info} for document in documents],
                    stable_order=True,
                    max_workers=nacos_config.get('table_split_max_worker', 4)
                ),
                total=len(documents),
                desc='表格切分'
        ):
            # 初始化table_id，确保在所有情况下都能使用
            table_id = create_uuid()
            
            if full_table_summary:
                table_metadata = document_metadata.model_dump()
                table_metadata.update({
                        'pk': table_id,
                        'type': 'table_summary'
                    })
                chunks.append(ParsedTable(
                        page_content=full_table_summary,
                        metadata=ParsedTableMetadata(**table_metadata)
                    ))
            for table_summary, table_chunks, _ in index_table_results:
                
                for table_string, table_pos in table_chunks:
                    table_metadata = document_metadata.model_dump()
                    table_metadata.update({
                        "offset": table_pos,
                        'pk': create_uuid(),
                        'table_summary_id': table_id
                    })
                    chunks.append(ParsedTable(
                        page_content=table_string,
                        metadata=ParsedTableMetadata(**table_metadata)
                    ))

        return chunks
