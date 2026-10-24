import "@/assets/styles/knowledgebase.less";
import { CaretDownOutlined, CaretRightOutlined } from "@ant-design/icons";
import {
  Empty,
  message,
  Popconfirm,
  Switch,
  Table,
  TableColumnsType,
  Select,
  Button
} from "antd";
import { useState, useMemo } from "react";

import {
  deleteGroupPermission,
  getGroupUserList,
  updateGroupPermission,
  setGroupPermission
} from "./service";

interface DataType {
  key: React.Key;
  groupName: string;
  userCount: number;
  edit?: boolean;
}

interface ExpandedDataType {
  name: string;
}

interface ExpandTableI {
  className: string;
  loading: boolean;
  [key: string]: any;
}

const GroupTable = (props: ExpandTableI) => {
  const {
    className,
    groups,
    setGroups,
    loading,
    fetchGroups,
    groupList,
    targetId
  } = props;
  const [loadingIndex, setLoadingIndex] = useState(-1);
  const [switchLoading, setSwitchLoading] = useState(-1);
  const [groupId, setGroupId] = useState("");
  const [permission, setPermission] = useState(false);

  const groupListOptions = useMemo(() => {
    return (groupList || []).filter(
      (item: any) =>
        !groups.map((g: any) => g.groupId).includes(Number(item.value))
    );
  }, [groups, groupList]);

  const onExpand = async (expanded: boolean, record: any) => {
    if (!expanded) return;
    if (!record.child) {
      setLoadingIndex(record.id);
      try {
        const res = await getGroupUserList({
          pageNo: 1,
          pageSize: 9999,
          groupId: record.groupId
        });
        setLoadingIndex(-1);
        if (res?.records) {
          record.child = res.records;
        }
      } catch (e) {
        setLoadingIndex(-1);
        console.log("e------>", e);
      }
    }
  };

  const expandedRowRender = (record: any, index: number) => {
    const columns: TableColumnsType<ExpandedDataType> = [
      { title: "用户名", dataIndex: "userName", key: "userName" },
      { title: "邮件地址", dataIndex: "userEmail", key: "userEmail" },
      { title: "手机号", dataIndex: "userPhone", key: "userPhone" }
    ];

    return (
      <div>
        {record?.child?.length === 0 ? (
          <Empty />
        ) : (
          <div className="expand-table-wrap">
            <Table
              columns={columns}
              dataSource={record.child}
              pagination={false}
              loading={record.id === loadingIndex}
              rowKey={(record: any) => record.id}
            />
          </div>
        )}
      </div>
    );
  };

  const deleteGroupPermissionById = async (id: string) => {
    try {
      const res = await deleteGroupPermission(id);
      if (res) {
        message.success("删除成功");
        fetchGroups();
      } else {
        message.error("删除失败");
      }
    } catch (e) {
      console.log("e", e);
    }
  };

  const columns: TableColumnsType<DataType> = [
    {
      title: "用户组",
      dataIndex: "groupName",
      key: "groupName",
      render: (_, record) => {
        return record.edit ? (
          getEditRowRender("groupName")
        ) : (
          <>
            {record.groupName}
            <span>（{record.userCount || 0}人）</span>
          </>
        );
      }
    },
    {
      title: "编辑权限",
      key: "permission",
      width: 120,
      render: (_, record, index) => {
        return record.edit ? (
          getEditRowRender("permission")
        ) : (
          <Switch
            checked={_.permission === 2}
            loading={switchLoading === index}
            onChange={async (checked: boolean) => {
              try {
                setSwitchLoading(index);
                const res = await updateGroupPermission({
                  groupId: _.groupId,
                  permission: checked ? 2 : 1,
                  bizType: 2,
                  targetId
                });
                setSwitchLoading(-1);
                if (res) {
                  message.success("修改权限成功!");
                  _.permission = checked ? 2 : 1;
                  setGroups([...groups]);
                }
              } catch (e) {
                setSwitchLoading(-1);
                console.log("e---------->", e);
              }
            }}
          />
        );
      }
    },
    {
      title: "操作",
      key: "action",
      width: 100,
      render: (_, record: any) =>
        record.edit ? (
          getEditRowRender("action")
        ) : (
          <Popconfirm
            title="删除权限"
            description="确认删除该用户组权限吗？"
            okText="确认"
            cancelText="取消"
            onConfirm={() => deleteGroupPermissionById(record.id)}
          >
            <Button type="link">删除</Button>
          </Popconfirm>
        )
    }
  ];

  const permissionOnChange = (checked: boolean) => {
    setPermission(checked);
  };

  const groupIdOnChange = (value: string) => {
    setGroupId(value);
  };

  const cancleCreate = () => {
    setGroups(groups.slice(1, groups.length));
  };

  const addGroup = async () => {
    const res = await setGroupPermission({
      groupIds: [groupId],
      permission: permission === true ? 2 : 1,
      bizType: 2,
      targetId
    });
    if (res) {
      message.success("添加权限成功!");
      fetchGroups();
    }
  };

  const getEditRowRender = (key: string) => {
    switch (key) {
      case "groupName":
        return (
          <Select
            style={{ width: "250px" }}
            showSearch
            placeholder="请选择"
            optionFilterProp="label"
            // mode="multiple"
            options={groupListOptions}
            onChange={groupIdOnChange}
          />
        );
      case "permission":
        return <Switch onChange={permissionOnChange} />;
      case "action":
        return (
          <div className="create-action-cell">
            <Button type="link" onClick={cancleCreate}>
              取消
            </Button>
            <Button type="link" disabled={!groupId} onClick={addGroup}>
              保存
            </Button>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <Table
      className={`${className}`}
      columns={columns}
      expandable={{
        expandedRowRender,
        onExpand,
        expandIcon: ({ expanded, onExpand, record }: any) =>
          record.edit ? null : expanded ? (
            <CaretDownOutlined onClick={(e) => onExpand(record, e)} />
          ) : (
            <CaretRightOutlined onClick={(e) => onExpand(record, e)} />
          )
      }}
      dataSource={groups}
      pagination={false}
      loading={loading}
      rowKey={(record: any) => record.id || record.key}
    />
  );
};

export default GroupTable;
