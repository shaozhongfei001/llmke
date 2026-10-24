import SystemContainer from "../../SystemContainer";
import { Tabs, TabsProps } from "antd";
import { useEffect, useState } from "react";
import "./style.less";
import Members from "./components/members";
import Resigned from "./components/resigned";
import DepartmentsTab from "./components/departments";
import { useAppPassport } from "@root/src/core/helps";
import useSystemApi from "@root/src/apis/system";

const Departments = () => {
  const api = useSystemApi();
  const [activeKey, setActiveKey] = useState("1");
  const { getToken, getUserInfo }: any = useAppPassport();
  const [userType, setUserType] = useState<any>({});
  const items: TabsProps["items"] = [
    {
      key: "1",
      label: "成员"
    },
    {
      key: "2",
      label: "部门"
    },
    {
      key: "3",
      label: "已离职人员"
    }
  ];

  const getUserTypeFn = async () => {
    const userInfo = getUserInfo();
    try {
      const res: any = await api.getUserType({
        userId: userInfo.id,
        userName: userInfo.userName
      });
      if (res.success) {
        setUserType(res.data);
      }
    } catch (error) {
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };
  useEffect(() => {
    getUserTypeFn();
  }, []);
  return (
    <SystemContainer title="用户部门管理" description="">
      <>
        <div className="flex departmentTabs">
          <div
            className="h-[57px] w-[20px]"
            style={{ borderBottom: "1px solid #f1f1f1" }}
          ></div>
          <Tabs
            defaultActiveKey="1"
            items={items}
            accessKey={activeKey}
            className="flex-1"
            onChange={(key: string) => {
              setActiveKey(key);
            }}
          />
        </div>
        <div className="h-[calc(100%-60px)] w-full">
          {activeKey === "1" && <Members userType={userType} />}
          {activeKey === "2" && <DepartmentsTab userType={userType} />}
          {activeKey === "3" && <Resigned userType={userType} />}
        </div>
      </>
    </SystemContainer>
  );
};

export default Departments;
