import "@/assets/styles/knowledgebase.less";
import { PlusCircleOutlined } from "@ant-design/icons";
import { useParams } from "react-router-dom";
import { Button, Radio, RadioChangeEvent } from "antd";
import { useEffect, useState, useMemo } from "react";
import { getGroups, getUsers, getGroupList, getUserList } from "./service";
import AddConfigForm from "./AddConfigForm";
import GroupTable from "./GroupTable";
import UserTable from "./UserTable";

const typeOptions = [
  { value: "1", label: "用户组" },
  { value: "2", label: "用户" }
];

const editGroupRow = [
  {
    key: 999999,
    groupName: "编辑列",
    userCount: 0,
    edit: true
  }
];

const editUserRow = [
  {
    key: 888888,
    userName: "编辑列",
    edit: true
  }
];

const PermisssonConfig = () => {
  const { id: knowledgeBaseId }: any = useParams();
  const [type, setType] = useState(typeOptions[0].value);
  const [showModal, setShowModal] = useState(false);
  const [groupLoading, setGroupLoading] = useState(false);
  const [userLoading, setUserLoading] = useState(false);
  const [users, setUsers] = useState<Array<any>>([]);
  const [groups, setGroups] = useState<Array<any>>([]);
  const [userList, setUserList] = useState([]);
  const [groupList, setGroupList] = useState([]);

  const isGroup = useMemo(() => {
    return type === typeOptions[0].value;
  }, [type]);

  const setCreateRow = () => {
    const isExit = isGroup
      ? groups.find((g: any) => g.edit === true)
      : users.find((u: any) => u.edit === true);
    if (!isExit) {
      if (isGroup) {
        setGroups([...editGroupRow, ...groups]);
      } else {
        setUsers([...editUserRow, ...users]);
      }
    }
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
    }
  };

  const fetchUsers = async () => {
    setUserLoading(true);
    try {
      const res = await getUsers(knowledgeBaseId);
      setUserLoading(false);
      setUsers(res?.length ? res : []);
    } catch (e) {
      setUserLoading(false);
    }
  };

  const fetchGroupList = async () => {
    try {
      const res = await getGroupList({ pageNo: 1, pageSize: 9999 });
      if (res?.records?.length) {
        return res.records.map((item: any) => ({
          value: item.id,
          label: item.name
        }));
      } else {
        return [];
      }
    } catch (e) {
      return [];
    }
  };

  const fetchUserList = async () => {
    try {
      const res = await getUserList({ pageNo: 1, pageSize: 9999 });
      if (res?.records?.length) {
        return res.records.map((item: any) => ({
          value: item.id,
          label: item.userName
        }));
      } else {
        return [];
      }
    } catch (e) {
      return [];
    }
  };

  const typeOnChange = ({ target: { value } }: any) => {
    setType(value);
  };

  const setNewGroup = (groups: any) => {
    setGroups(groups);
  };

  const setNewUsers = (users: any) => {
    setUsers(users);
  };

  const initOptions = async () => {
    fetchGroups();
    fetchUsers();
    const userList = await fetchUserList();
    const groupList = await fetchGroupList();
    setUserList(userList);
    setGroupList(groupList);
  };

  useEffect(() => {
    initOptions();
  }, []);

  return (
    <div className="min-h-[calc(100vh-160px)] w-full relative flex">
      {/* <div>{JSON.stringify(users)}</div> */}

      <div
        className="w-[207px] h-[calc(100%-180px)] px-[12px] pb-[12px]"
        style={{ borderRight: "1px solid #E8E8E8" }}
      >
        {typeOptions.map((item) => (
          <div
            key={item.value}
            onClick={() => typeOnChange({ target: { value: item.value } })}
            className={`mr-[10px] w-[183px] h-[50px] px-[20px] flex items-center cursor-pointer text-[14px] rounded-[4px] ${item.value === type ? "text-primary-color bg-[#F1F5FF]" : "text-text-color1"}`}
          >
            {item.label}
          </div>
        ))}
      </div>

      <div className="h-[calc(100%-110px)] overflow-y-auto px-5 flex-1">
        <Button
          style={{
            background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
            color: "#fff"
          }}
          className="mb-[10px] border-none"
          icon={<PlusCircleOutlined />}
          onClick={setCreateRow}
        >
          新建
        </Button>
        <GroupTable
          className={`${type === typeOptions[0].value ? "" : "hidden"}`}
          targetId={knowledgeBaseId}
          groups={groups}
          loading={groupLoading}
          groupList={groupList}
          setGroups={setNewGroup}
          fetchGroups={fetchGroups}
        />
        <UserTable
          className={`${type === typeOptions[1].value ? "" : "hidden"}`}
          targetId={knowledgeBaseId}
          loading={userLoading}
          users={users}
          userList={userList}
          setUsers={setNewUsers}
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

export default PermisssonConfig;
