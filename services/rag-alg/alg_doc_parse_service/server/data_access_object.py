from mysql import connector


class DataAccessObject:
    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306):
        """初始化 DAO，建立数据库连接"""
        self.connection = connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        self.cursor = self.connection.cursor(dictionary=True)

    def __enter__(self):
        return self

    def close(self):
        self.cursor.close()
        self.connection.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def execute_query(self, query: str, params: tuple = None) -> list[dict]:
        """执行查询，返回查询结果"""
        self.cursor.execute(query, params)
        result = self.cursor.fetchall()
        return result

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """执行插入、更新、删除等操作"""
        self.cursor.execute(query, params)
        self.connection.commit()  # 提交事务
        return self.cursor.rowcount  # 返回受影响的行数

    def create_table(self, table_name: str, column_schema: str, table_schema: str) -> None:
        query = f'CREATE TABLE IF NOT EXISTS {table_name} ({column_schema}) {table_schema}'
        self.execute_update(query)

    def insert(self, table: str, **column_values) -> int:
        """插入数据"""
        placeholders = ', '.join(['%s'] * len(column_values))
        columns_str = ', '.join(column_values.keys())
        query = f'INSERT INTO {table} ({columns_str}) VALUES ({placeholders})'
        return self.execute_update(query, tuple(column_values.values()))

    def update(self, table: str, where_clause: str, where_params: tuple, **column_values) -> int:
        """更新数据"""
        set_clause = ', '.join([f'{col} = %s' for col in column_values['columns']])
        query = f'UPDATE {table} SET {set_clause} WHERE {where_clause}'
        return self.execute_update(query, tuple(column_values['values']) + where_params)

    def delete(self, table: str, where_clause: str, where_params: tuple) -> int:
        """删除数据"""
        query = f"DELETE FROM {table} WHERE {where_clause}"
        return self.execute_update(query, where_params)

    def fetch_all(self, table: str, columns: list[str] = None) -> list[dict]:
        """获取所有数据"""
        if columns is None:
            columns = ['*']
        columns_str = ', '.join(columns)
        query = f"SELECT {columns_str} FROM {table}"
        return self.execute_query(query)

    def fetch_one(self, table: str, columns: list[str] = None, where_clause: str = '',
                  where_params: tuple = ()) -> dict:
        """获取单条数据"""
        if columns is None:
            columns = ['*']
        columns_str = ', '.join(columns)
        query = f'SELECT {columns_str} FROM {table} WHERE {where_clause} LIMIT 1'
        result = self.execute_query(query, where_params)
        return result[0] if result else None
