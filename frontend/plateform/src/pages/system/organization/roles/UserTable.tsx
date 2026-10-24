import React, { useState, useEffect } from 'react';
import { Table, Empty, Button, Popconfirm, message, Avatar } from 'antd';
import { DeleteOutlined, UserOutlined } from '@ant-design/icons';
import { getAvatarProps } from '@/pages/system/organization/config/gradients';

interface UserTableProps {
  loading: boolean;
  dataSource: any[];
  onRemoveUser: (userId: string) => void;
}

const UserTable: React.FC<UserTableProps> = ({
  loading,
  dataSource,
  onRemoveUser
}) => {
  const [tableHeight, setTableHeight] = useState<string | undefined>(undefined);

  useEffect(() => {
    // 当数据变化时重新计算高度
    setTableHeight(dataSource.length > 0 ? 'calc(100vh - 520px)' : undefined);
  }, [dataSource]);

  const columns = [
    {
      title: '姓名',
      dataIndex: 'userRealname',
      key: 'userRealname',
      width: 200,
      render: (text: string) => (
        <div className="flex items-center gap-x-2">
          <Avatar {...getAvatarProps('MEMBER')} icon={<UserOutlined />} />
          <span>{text || '匿名'}</span>
        </div>
      ),
    },
    {
      title: '邮箱',
      dataIndex: 'userEmail',
      key: 'userEmail',
      width: 200,
      render: (text: string) => text || '-'
    },
    {
      title: '部门',
      dataIndex: 'deptName',
      key: 'deptName',
      width: 200,
      render: (text: string) => text || '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: any) => (
        <div className='flex justify-center items-center gap-x-1'>
          <Popconfirm
            title="确定要移除该用户吗？"
            onConfirm={() => onRemoveUser(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button 
              type="link" 
              danger
              icon={<DeleteOutlined />}
            >
              移除
            </Button>
          </Popconfirm>
        </div>
      ),
    },
  ];

  return (
    <Table
      loading={loading}
      columns={columns}
      dataSource={dataSource}
      rowKey="id"
      pagination={{
        size: "small",
        pageSize: 6,
        showSizeChanger: false,
        showQuickJumper: true,
        showTotal: (total) => `共 ${total} 条`
      }}
      scroll={{ 
        y: tableHeight,
        x: '100%'
      }}
      locale={{
        emptyText: (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无已分配用户"
          />
        )
      }}
    />
  );
};

export default UserTable; 