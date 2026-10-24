/* eslint-disable no-irregular-whitespace */
import "@/assets/styles/knowledgebase.less";
import return_svg from "@/assets/knowledgebase/return.svg";
import questionMark_svg from "@/assets/knowledgebase/questionMark.svg";
import image66_svg from "@/assets/knowledgebase/image66.svg";
import image67_svg from "@/assets/knowledgebase/image67.svg";
import {
  ExclamationCircleFilled,
  PlusOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useNavigate, useParams } from "react-router-dom";
import {
  Button,
  Col,
  Empty,
  Form,
  Input,
  InputNumber,
  message,
  Popconfirm,
  Popover,
  Radio,
  Row,
  Select,
  Slider,
  Switch,
  Table,
  TableColumnsType,
  Tabs,
  Tooltip,
} from "antd";
import { useEffect, useState } from "react";
import {
  deleteGroupPermission,
  deleteUserPermission,
  getGroups,
  getGroupUserList,
  getUsers,
  updateConf,
  updateGroupPermission,
  updateUserPermission,
} from "./service";
import AddConfigForm from "./AddConfigForm";
import { setgroups } from "process";
const { useForm } = Form;

const Configuration = () => {
  const [tabKey, setTabKey] = useState("1");
  const tabChange = (key: string) => {
    setTabKey(key);
  };

  return (
    <div className="configuration-wrap ">
      <ConfigurationHeader />
      <div className="h-[calc(100%-60px)] bg-white rounded-[4px] px-[30px] py-[30px]">
        <PermissonConfig />
      </div>
    </div>
  );
};
export default Configuration;

interface DataType {
  key: React.Key;
  groupName: string;
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
  const { className, groups, setGroups, loading, fetchGroups } = props;
  const { id: knowledgeBaseId }: any = useParams();
  const [loadingIndex, setLoadingIndex] = useState(-1);
  const [switchLoading, setSwitchLoading] = useState(-1);

  const onExpand = async (expanded: boolean, record: any) => {
    if (!expanded) return;
    if (!record.child) {
      setLoadingIndex(record.id);
      try {
        const res = await getGroupUserList({
          pageNo: 1,
          pageSize: 9999,
          groupId: record.groupId,
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
      { title: "手机号", dataIndex: "userPhone", key: "userPhone" },
    ];

    return (
      <div>
        {record?.child?.length === 0 ? (
          <Empty />
        ) : (
          <Table
            columns={columns}
            dataSource={record.child}
            pagination={false}
            loading={record.id === loadingIndex}
            rowKey={(record: any) => record.id}
          />
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
      }
    } catch (e) {
      console.log("e", e);
    }
  };

  const columns: TableColumnsType<DataType> = [
    { title: "用户组", dataIndex: "groupName", key: "groupName" },
    {
      title: "是否可编辑",
      key: "permission",
      render: (_, record, index) => {
        return (
          <Switch
            checked={_.permission === 2}
            loading={switchLoading === index}
            onChange={async (checked: boolean) => {
              try {
                setSwitchLoading(index);
                const res = await updateGroupPermission({
                  groupId: _.groupId,
                  permission: checked ? 2 : 1,
                  bizType: 1,
                  targetId: knowledgeBaseId,
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
      },
    },
    {
      title: "操作",
      key: "action",
      width: "20%",
      render: (_, record: any) => (
        <Popconfirm
          title="删除权限"
          description="确认删除该用户组权限吗？"
          okText="确认"
          cancelText="取消"
          onConfirm={() => deleteGroupPermissionById(record.id)}
        >
          <Button type="link">删除</Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <Table
      className={`${className}`}
      columns={columns}
      expandable={{ expandedRowRender, onExpand }}
      dataSource={groups}
      pagination={false}
      loading={loading}
      rowKey={(record: any) => record.id}
    />
  );
};

const UserTable = (props: ExpandTableI) => {
  const { className, loading, users, fetchUsers, setUsers } = props;
  const { id: knowledgeBaseId }: any = useParams();
  const [switchLoading, setSwitchLoading] = useState(-1);

  const deleteUserPermissionById = async (id: string) => {
    try {
      const res = await deleteUserPermission(id);
      if (res) {
        message.success("删除成功");
        fetchUsers();
      }
    } catch (e) {
      console.log("e", e);
    }
  };

  const columns: TableColumnsType<DataType> = [
    { title: "用户", dataIndex: "userName", key: "userName" },
    {
      title: "是否可编辑",
      key: "permission",
      render: (_, record: any, index) => {
        return (
          <Switch
            checked={record.permission === 2}
            loading={index === switchLoading}
            onChange={async (checked: boolean) => {
              try {
                setSwitchLoading(index);
                const res = await updateUserPermission({
                  userId: _.userId,
                  permission: checked ? 2 : 1,
                  bizType: 1,
                  targetId: knowledgeBaseId,
                });
                setSwitchLoading(-1);
                if (res) {
                  record.permission = checked ? 2 : 1;
                  setUsers([...users]);
                  message.success("修改权限成功!");
                }
              } catch (e) {
                setSwitchLoading(-1);
                console.log("e---------->", e);
              }
            }}
          />
        );
      },
    },
    {
      title: "操作",
      key: "action",
      width: "20%",
      render: (_, record: any) => (
        <Popconfirm
          title="删除权限"
          description="确认删除该用户权限吗？"
          okText="确认"
          cancelText="取消"
          onConfirm={() => deleteUserPermissionById(record.id)}
        >
          <Button type="link">删除</Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <Table
      className={`${className}`}
      columns={columns}
      dataSource={users}
      pagination={false}
      loading={loading}
      rowKey={(record: any) => record.id}
    />
  );
};

const PermissonConfig = () => {
  const { id: knowledgeBaseId }: any = useParams();
  const [type, setType] = useState("1");
  const [showModal, setShowModal] = useState(false);
  const [groupLoading, setGroupLoading] = useState(false);
  const [userLoading, setUserLoading] = useState(false);
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);

  const onCreateClick = () => {
    setShowModal(true);
  };

  const fetchGroups = async () => {
    setGroupLoading(true);
    try {
      const res = await getGroups(knowledgeBaseId);
      setGroupLoading(false);
      if (res?.length) {
        setGroups(res);
      } else {
        setGroups([]);
      }
    } catch (e) {
      setGroupLoading(false);
      console.log("e--->", e);
    }
  };

  const fetchUsers = async () => {
    setUserLoading(true);
    try {
      const res = await getUsers(knowledgeBaseId);
      setUserLoading(false);
      if (res?.length) {
        setUsers(res);
      } else {
        setGroups([]);
      }
    } catch (e) {
      setUserLoading(false);
      console.log("e--->", e);
    }
  };

  const initList = async () => {
    fetchGroups();
    fetchUsers();
  };

  useEffect(() => {
    initList();
  }, []);

  return (
    <div className="h-[calc(100%-73px)] relative">
      <div className="flex justify-between">
        <div className={`search-bar`}>
          <Select
            style={{ width: "240px", marginRight: "16px" }}
            defaultValue="1"
            value={type}
            options={[
              { value: "1", label: "用户组" },
              { value: "2", label: "用户" },
            ]}
            onChange={(v: string) => setType(v)}
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            style={{ width: "120px" }}
            onClick={onCreateClick}
          >
            添加
          </Button>
        </div>
      </div>
      <div className="mt-[20px] h-[calc(100%-110px)] overflow-y-auto">
        <GroupTable
          className={`${type === "1" ? "" : "hidden"}`}
          groups={groups}
          loading={groupLoading}
          setGroups={setGroups}
          fetchGroups={fetchGroups}
        />
        <UserTable
          className={`${type === "2" ? "" : "hidden"}`}
          loading={userLoading}
          users={users}
          setUsers={setUsers}
          fetchUsers={fetchUsers}
        />
      </div>
      <AddConfigForm
        isShowCreateModal={showModal}
        closeModal={(v) => setShowModal(v)}
        type={type}
        cb={() => {
          if (type === "1") {
            fetchGroups();
          } else {
            fetchUsers();
          }
        }}
      />
    </div>
  );
};

const ConfigurationHeader = () => {
  const navigator = useNavigate();
  return (
    <div className="flex mb-[23px] mt-[2px] items-center pl-[30px]">
      <div
        className="flex items-center cursor-pointer"
        onClick={() => navigator(-1)}
      >
        <img
          src={return_svg}
          className="w-[14px] h-[14px] mr-[10px] mt-[2px]"
        />
        <div className="text-[#333333] text-[16px] font-medium">配置</div>
      </div>
      <span className="breadcrumb-tab cursor-default">
        <ExclamationCircleFilled color="rgba(250, 128, 21, 1)" />
        <span className="tip-text">
          在这里更新您的知识库详细信息，尤其是解析方法。
        </span>
      </span>
    </div>
  );
};
