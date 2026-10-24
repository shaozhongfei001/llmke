from enum import Enum
from urllib.parse import urlparse

from log import logger, request_id
from .data_access_object import DataAccessObject
from .nacos_utils import DocParseConfig


class TASK_STATUS(Enum):
    PENDING: str = '0'
    STARTED: str = '1'
    COMPLETED: str = '2'
    FAILED: str = '-1'


# class ProcessReporter:
#     def __init__(self):
#         pass
#
#     def create_table(self):
#         pass
#
#     def new_task(self, **task_info):
#         pass
#
#     def update_process(self, task_id= request_id, **task_info):
#         pass
#
#     def delete_task(self, task_id):
#         pass
#
#     def __enter__(self):
#         return self
#
#     def close(self):
#         pass
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self.close()


class ProcessReporter:
    def __init__(self):
        doc_parse_config = DocParseConfig()
        java_common_config = doc_parse_config.configs['java-common']
        doc_parse_config = doc_parse_config.config

        self.mysql_config: dict = doc_parse_config['mysql']
        self.mysql_config.update(java_common_config['mysql'])

        url = self.mysql_config.get('url').replace('jdbc:mysql://', 'https://')
        url = url.replace('${server.host-ip}', java_common_config['server']['host-ip'])
        parsed_url = urlparse(url)

        host = parsed_url.hostname
        port = parsed_url.port
        database = parsed_url.path.lstrip('/')
        username = self.mysql_config['username']
        password = self.mysql_config['password']

        self.table_name = self.mysql_config['table_name']

        self.dao = DataAccessObject(
            host=host,
            user=username,
            password=password,
            database=database,
            port=port
        )

    def create_table(self):
        schema = self.mysql_config['schema']
        self.dao.create_table(
            table_name=self.table_name,
            column_schema=''.join(schema['column_schema']),
            table_schema=schema['table_schema'],
        )
        # [新增三大表-financial]
        table_names = ["consolidated_balance", "consolidated_income", "consolidated_cash_flow"]
        for table_name in table_names:
            schema = self.mysql_config[table_name]['schema']
            self.dao.create_table(
                table_name=table_name,
                column_schema=''.join(schema['column_schema']),
                table_schema=schema['table_schema'],
            )

    def new_task(self, **task_info):
        self.dao.insert(self.table_name, **task_info)

    def update_process(self, task_id: str, **task_info):
        self.dao.update(
            table=self.table_name,
            columns=task_info.keys(),
            values=task_info.values(),
            where_clause='task_id=%s',
            where_params=(task_id,)
        )

    def delete_task(self, task_id: str):
        self.dao.delete(self.table_name, 'task_id=%s', (task_id,))

    def indictae_execute_update(self, params_dic):
        where_list = ['knowledge_base_name', 'file_id', 'company_short_name', 'year', 'period_type', 'date_type',
                      'indicator_raw']
        where_clause = ''
        success = True
        msg = ''
        where_params = []
        # set_dic = {}
        column_values = {
            'columns': [],
            'values': []
        }
        for key in params_dic.keys():
            if key in where_list:
                if where_clause != '':
                    where_clause += 'AND '
                where_clause += f'{key} = %s '
                where_params.append(params_dic[key])
            else:
                if key != 'table_name':
                    column_values['values'].append(params_dic[key])
                    if key == 'user_id':
                        key = 'modified_by'
                    if key == 'modify_value':
                        key = 'indicator_value'
                    column_values['columns'].append(key)

        table_name = params_dic['table_name']
        where_params = tuple(where_params)
        try:
            rows_counts = self.dao.update(table=table_name, where_clause=where_clause, where_params=where_params,
                                          **column_values)
            if rows_counts == 0:
                msg = '运行成功，但未找到可修改条目'
            elif rows_counts > 1:
                msg = '运行成功，但修改条目数不止一条'
            elif rows_counts == 1:
                msg = '运行成功，条目已修改'
        except:
            success = False
            msg = '运行失败'
        return success, msg

    def indicate_execute_query(self, queries: list[str], table_names: list[str], request_id: str, params: tuple = None):
        try:
            success = True
            error_msg = ""
            results = []
            for query, table_name in zip(queries, table_names):
                query_result = self.dao.execute_query(query=query, params=params)
                for result in query_result:
                    result["table_name"] = table_name
                    results.append(result)
        except:
            success = False
            error_msg = "内部服务出错，任务查询失败。"
            results = []
        return success, error_msg, request_id, results

    def indicate_ref(self, table_names, ref_ids, fixed_value, adopt_index, modified_by):
        self.dao.connection.autocommit = False  # 手动提交事务
        cursor = self.dao.connection.cursor(dictionary=True)

        try:
            if adopt_index:
                for idx, (table_name, id) in enumerate(zip(table_names, ref_ids)):
                    sql = f"UPDATE {table_name} SET adopt = %s, modified_by = %s WHERE id = %s"
                    params = (1 if adopt_index == idx else 0, modified_by, id)
                    cursor.execute(sql, params)
            else:
                for table_name, id in zip(table_names, ref_ids):
                    sql = f"""
                        UPDATE {table_name}
                        SET adopt = %s, 
                            fixed_value = %s, 
                            modified_by = %s 
                        WHERE id = %s
                    """
                    params = (2, fixed_value, modified_by, id)
                    cursor.execute(sql, params)
            self.dao.connection.commit()
            logger.info("事务提交成功！")
            success, msg = True, '修改成功'
        except Exception as e:
            logger.info("发生错误，事务回滚:", str(e))
            self.dao.connection.rollback()
            success, msg = False, '发生错误，事务已回滚'

        return success, msg

    def indictae_execute_update(self, params_dic):
        where_list = ['knowledge_base_name', 'file_id', 'company_short_name', 'year', 'period_type', 'date_type']
        where_clause = ''
        success = True
        msg = ''
        where_params = []
        # set_dic = {}
        column_values = {
            'columns': [],
            'values': []
        }
        for key in params_dic.keys():
            if key in where_list:
                if where_clause != '':
                    where_clause += 'AND '
                where_clause += f'{key} = %s'
                where_params.append(params_dic[key])
            else:
                if key != 'table_name':
                    column_values['columns'].append(key)
                    column_values['values'].append(params_dic[key])

        table_name = 'table_name'
        where_params = tuple(where_params)
        try:
            rows_counts = self.dao.update(table=table_name, where_clause=where_clause, where_params=where_params,
                                          **column_values)
            if rows_counts == 0:
                msg = '运行成功，但未找到可修改条目'
            elif rows_counts > 1:
                msg = '运行成功，但修改条目数不止一条'
            elif rows_counts == 1:
                msg = '运行成功，条目已修改'
        except:
            success = False
            msg = '运行失败'
        return success, msg

    def indicate_execute_query(self, queries: list[str], table_names: list[str], request_id: str, params: tuple = None):
        try:
            success = True
            error_msg = ""
            results = []
            for query, table_name in zip(queries, table_names):
                query_result = self.dao.execute_query(query=query, params=params)
                for result in query_result:
                    result["table_name"] = table_name
                    results.append(result)
        except Exception as e:
            success = False
            error_msg = "内部服务出错，任务查询失败。"
            results = []
        return success, error_msg, request_id, results

    def indicate_ref(self, table_names, ref_ids, fixed_value, adopt_index, modified_by):
        self.dao.connection.autocommit = False  # 手动提交事务
        cursor = self.dao.connection.cursor(dictionary=True)

        try:
            if adopt_index:
                for idx, (table_name, id) in enumerate(zip(table_names, ref_ids)):
                    sql = f"UPDATE {table_name} SET adopt = %s, modified_by = %s WHERE id = %s"
                    params = (1 if adopt_index == idx else 0, modified_by, id)
                    cursor.execute(sql, params)
            else:
                for table_name, id in zip(table_names, ref_ids):
                    sql = f"""
                        UPDATE {table_name}
                        SET adopt = %s, 
                            fixed_value = %s, 
                            modified_by = %s 
                        WHERE id = %s
                    """
                    params = (2, fixed_value, modified_by, id)
                    cursor.execute(sql, params)
            self.dao.connection.commit()
            logger.info("事务提交成功！")
            success, msg = True, '修改成功'
        except Exception as e:
            logger.info("发生错误，事务回滚:", str(e))
            self.dao.connection.rollback()
            success, msg = False, '发生错误，事务已回滚'

        return success, msg

    def __enter__(self):
        return self

    def close(self):
        self.dao.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# class ProcessReporter:
#     def __init__(self):
#         doc_parse_config = DocParseConfig()
#         java_common_config = doc_parse_config.configs['java-common']
#         doc_parse_config = doc_parse_config.config
#
#         self.mysql_config: dict = doc_parse_config['mysql']
#         self.mysql_config.update(java_common_config['mysql'])
#
#         url = self.mysql_config.get('url').replace('jdbc:mysql://', 'https://')
#         url = url.replace('${server.host-ip}', java_common_config['server']['host-ip'])
#         parsed_url = urlparse(url)
#
#         host = parsed_url.hostname
#         port = parsed_url.port
#         database = parsed_url.path.lstrip('/')
#         username = self.mysql_config['username']
#         password = self.mysql_config['password']
#
#         self.table_name = self.mysql_config['table_name']
#
#         self.dao = DataAccessObject(
#             host=host,
#             user=username,
#             password=password,
#             database=database,
#             port=port
#         )
#
#     def create_table(self):
#         schema = self.mysql_config['schema']
#         self.dao.create_table(
#             table_name=self.table_name,
#             column_schema=''.join(schema['column_schema']),
#             table_schema=schema['table_schema'],
#         )
#         # [新增三大表-financial]
#         table_names = ["consolidated_balance", "consolidated_income", "consolidated_cash_flow"]
#         for table_name in table_names:
#             schema = self.mysql_config[table_name]['schema']
#             self.dao.create_table(
#                 table_name=table_name,
#                 column_schema=''.join(schema['column_schema']),
#                 table_schema=schema['table_schema'],
#             )
#
#     def new_task(self, **task_info):
#         self.dao.insert(self.table_name, **task_info)
#
#     def update_process(self, task_id: str, **task_info):
#         self.dao.update(
#             table=self.table_name,
#             columns=task_info.keys(),
#             values=task_info.values(),
#             where_clause='task_id=%s',
#             where_params=(task_id,)
#         )
#
#     def delete_task(self, task_id: str):
#         self.dao.delete(self.table_name, 'task_id=%s', (task_id,))
#
#     def indictae_execute_update(self, params_dic):
#         where_list = ['knowledge_base_name', 'file_id', 'company_short_name', 'year', 'period_type', 'date_type', 'indicator_raw']
#         where_clause = ''
#         success = True
#         msg = ''
#         where_params = []
#         # set_dic = {}
#         column_values = {
#             'columns': [],
#             'values': []
#         }
#         for key in params_dic.keys():
#             if key in where_list:
#                 if where_clause != '':
#                     where_clause += 'AND '
#                 where_clause += f'{key} = %s '
#                 where_params.append(params_dic[key])
#             else:
#                 if key != 'table_name':
#                     column_values['values'].append(params_dic[key])
#                     if key == 'user_id':
#                         key = 'modified_by'
#                     if key == 'modify_value':
#                         key = 'indicator_value'
#                     column_values['columns'].append(key)
#
#
#         table_name = params_dic['table_name']
#         where_params = tuple(where_params)
#         try:
#             rows_counts = self.dao.update(table=table_name, where_clause=where_clause, where_params=where_params,
#                                           **column_values)
#             if rows_counts == 0:
#                 msg = '运行成功，但未找到可修改条目'
#             elif rows_counts > 1:
#                 msg = '运行成功，但修改条目数不止一条'
#             elif rows_counts == 1:
#                 msg = '运行成功，条目已修改'
#         except:
#             success = False
#             msg = '运行失败'
#         return success, msg
#
#     def indicate_execute_query(self, queries: list[str], table_names:list[str], request_id:str, params: tuple = None):
#         try:
#             success = True
#             error_msg = ""
#             results = []
#             for query, table_name in zip(queries, table_names):
#                 query_result = self.dao.execute_query(query=query, params=params)
#                 for result in query_result:
#                     result["table_name"] = table_name
#                     results.append(result)
#         except:
#             success = False
#             error_msg = "内部服务出错，任务查询失败。"
#             results = []
#         return success, error_msg, request_id, results
#
#     def indicate_ref(self, table_names, ref_ids, fixed_value, adopt_index, modified_by):
#         self.dao.connection.autocommit = False  # 手动提交事务
#         cursor = self.dao.connection.cursor(dictionary=True)
#
#         try:
#             if adopt_index:
#                 for idx, (table_name, id)in enumerate(zip(table_names, ref_ids)):
#                     sql = f"UPDATE {table_name} SET adopt = %s, modified_by = %s WHERE id = %s"
#                     params = (1 if adopt_index==idx else 0,  modified_by, id)
#                     cursor.execute(sql, params)
#             else:
#                 for table_name, id in zip(table_names, ref_ids):
#                     sql = f"""
#                         UPDATE {table_name}
#                         SET adopt = %s,
#                             fixed_value = %s,
#                             modified_by = %s
#                         WHERE id = %s
#                     """
#                     params = (2, fixed_value, modified_by, id)
#                     cursor.execute(sql, params)
#             self.dao.connection.commit()
#             logger.info("事务提交成功！")
#             success, msg = True, '修改成功'
#         except Exception as e:
#             logger.info("发生错误，事务回滚:", str(e))
#             self.dao.connection.rollback()
#             success, msg = False, '发生错误，事务已回滚'
#
#         return success, msg
#
#     def indictae_execute_update(self, params_dic):
#         where_list = ['knowledge_base_name', 'file_id', 'company_short_name', 'year', 'period_type', 'date_type']
#         where_clause = ''
#         success = True
#         msg = ''
#         where_params = []
#         # set_dic = {}
#         column_values = {
#             'columns': [],
#             'values': []
#         }
#         for key in params_dic.keys():
#             if key in where_list:
#                 if where_clause != '':
#                     where_clause += 'AND '
#                 where_clause += f'{key} = %s'
#                 where_params.append(params_dic[key])
#             else:
#                 if key != 'table_name':
#                     column_values['columns'].append(key)
#                     column_values['values'].append(params_dic[key])
#
#         table_name = 'table_name'
#         where_params = tuple(where_params)
#         try:
#             rows_counts = self.dao.update(table=table_name, where_clause=where_clause, where_params=where_params,
#                                           **column_values)
#             if rows_counts == 0:
#                 msg = '运行成功，但未找到可修改条目'
#             elif rows_counts > 1:
#                 msg = '运行成功，但修改条目数不止一条'
#             elif rows_counts == 1:
#                 msg = '运行成功，条目已修改'
#         except:
#             success = False
#             msg = '运行失败'
#         return success, msg
#
#     def indicate_execute_query(self, queries: list[str], table_names:list[str], request_id:str, params: tuple = None):
#         try:
#             success = True
#             error_msg = ""
#             results = []
#             for query, table_name in zip(queries, table_names):
#                 query_result = self.dao.execute_query(query=query, params=params)
#                 for result in query_result:
#                     result["table_name"] = table_name
#                     results.append(result)
#         except Exception as e:
#             success = False
#             error_msg = "内部服务出错，任务查询失败。"
#             results = []
#         return success, error_msg, request_id, results
#
#     def indicate_ref(self, table_names, ref_ids, fixed_value, adopt_index, modified_by):
#         self.dao.connection.autocommit = False  # 手动提交事务
#         cursor = self.dao.connection.cursor(dictionary=True)
#
#         try:
#             if adopt_index:
#                 for idx, (table_name, id)in enumerate(zip(table_names, ref_ids)):
#                     sql = f"UPDATE {table_name} SET adopt = %s, modified_by = %s WHERE id = %s"
#                     params = (1 if adopt_index==idx else 0,  modified_by, id)
#                     cursor.execute(sql, params)
#             else:
#                 for table_name, id in zip(table_names, ref_ids):
#                     sql = f"""
#                         UPDATE {table_name}
#                         SET adopt = %s,
#                             fixed_value = %s,
#                             modified_by = %s
#                         WHERE id = %s
#                     """
#                     params = (2, fixed_value, modified_by, id)
#                     cursor.execute(sql, params)
#             self.dao.connection.commit()
#             logger.info("事务提交成功！")
#             success, msg = True, '修改成功'
#         except Exception as e:
#             logger.info("发生错误，事务回滚:", str(e))
#             self.dao.connection.rollback()
#             success, msg = False, '发生错误，事务已回滚'
#
#         return success, msg
#
#     def __enter__(self):
#         return self
#
#     def close(self):
#         self.dao.close()
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self.close()


with ProcessReporter() as process_reporter:
    process_reporter.create_table()
logger.info('文档解析及金融抽取mysql表创建成功')
