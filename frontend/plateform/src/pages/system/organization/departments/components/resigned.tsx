import { EllipsisOutlined, SearchOutlined } from "@ant-design/icons";
import useSystemApi from "@root/src/apis/system";
import { popoverVariants } from "@root/src/components/CommonEditor/ui/popover";
import CustomTooltip from "@root/src/components/CustomTooltip";
import {
  BTN_NAME,
  getEditPermission,
  PERMISSION_WARNING_MSG,
  USER_STATUS
} from "@root/src/const/permission";
import {
  Button,
  DatePicker,
  Dropdown,
  Input,
  MenuProps,
  message,
  Pagination,
  Popconfirm,
  Table
} from "antd";
import { useEffect, useRef, useState } from "react";
import { uid } from "uid";
const { RangePicker } = DatePicker;

const Resigned = ({ userType }: { userType: USER_STATUS }) => {
  const api = useSystemApi();
  const [tableLoading, setTableLoading] = useState(false);
  const [pageNo, setPageNo] = useState(1);
  const [total, setTotal] = useState(0);
  const [dateRange, setDateRange] = useState(["", ""]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [resignedList, setResignedList] = useState([
    {
      id: uid(),
      name: "德西",
      status: 0,
      email: "349636973@qq.com",
      department: "市场部",
      role: "管理员"
    }
  ]);
  const columns = [
    {
      title: "姓名",
      dataIndex: "userRealname",
      key: "userRealname",
      minWidth: 100
    },
    {
      title: "离职前所属部门",
      dataIndex: "deptName",
      key: "deptName",
      minWidth: 100
    },
    {
      title: "离职天数",
      dataIndex: "resignedDays",
      key: "resignedDays",
      minWidth: 100
    },
    {
      title: "离职日期",
      dataIndex: "resignDate",
      key: "resignDate",
      minWidth: 100
    },
    {
      title: "操作",
      dataIndex: "action",
      key: "action",
      width: 100,
      render: (_: any, record: any) => {
        return (
          <>
            {getBtn(
              getEditPermission(userType, BTN_NAME.ADD),
              <Button
                type="link"
                disabled={getEditPermission(userType, BTN_NAME.ADD)}
              >
                删除
              </Button>,
              "删除",
              "column",
              record
            )}
          </>
        );
      }
    }
  ];

  const searchResignedUserListFn = async () => {
    try {
      setTableLoading(true);
      const res: any = await api.searchResignedUserList({
        pageSize: 5,
        pageNo,
        startTime: dateRange[0],
        endTime: dateRange[1],
        userRealname: searchInput
      });
      setTableLoading(false);
      if (res.success) {
        setResignedList(res.data.records);
        setTotal(res.data.total);
      }
    } catch (error) {
      setTableLoading(false);
      console.log("error", error);
    }
  };

  const clearResignedUsersFn = async () => {
    try {
      setTableLoading(true);
      const res: any = await api.clearResignedUsers({});
      setTableLoading(false);
      if (res.success) {
        if (pageNo !== 1) {
          setPageNo(1);
        } else {
          searchResignedUserListFn();
        }
      }
    } catch (error) {
      setTableLoading(false);
      console.log("error", error);
    }
  };

  const handleDatePicker = (event: any, b: any) => {
    setDateRange(b);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      if (pageNo !== 1) {
        setPageNo(1);
      } else {
        searchResignedUserListFn();
      }
    }
  };

  const deleteUsersByIdsFn = async (params: any[]) => {
    try {
      const res: any = await api.deleteUsersByIds({
        userIds: params.join(",")
      });
      if (res.success) {
        message.success("删除成功！");
        if (pageNo !== 1) {
          setPageNo(1);
        } else {
          searchResignedUserListFn();
        }
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  useEffect(() => {
    searchResignedUserListFn();
  }, [pageNo, dateRange]);
  const [tableHeight, setTableHeight] = useState(500);
  const tableBoxRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    console.log("userType", userType);

    if (tableBoxRef.current) {
      const tableBoxHeight = tableBoxRef.current.offsetHeight;
      setTableHeight(tableBoxHeight);
    }
  }, []);
  const getBtn = (
    disabled: boolean,
    btn: any,
    popoverText?: string,
    from?: string,
    record?: any
  ) => {
    console.log("record", record);

    return disabled ? (
      <CustomTooltip
        content={
          getEditPermission(userType, BTN_NAME.ADD)
            ? PERMISSION_WARNING_MSG
            : ""
        }
        type="warning"
        position="top"
      >
        {btn}
      </CustomTooltip>
    ) : (
      <Popconfirm
        placement="right"
        style={{ width: "224px", borderRadius: "8px" }}
        title={
          <>
            <div className="flex items-center">
              <div className="text-[14px] text-[#000000] font-bold">
                {popoverText || "删除"}
              </div>
            </div>
            <div className="flex items-center">
              <div className="text-[14px] text-[#000000] mt-[8px]">
                <span>{popoverText || "删除"}后无法恢复，是否继续</span>
                <br />
                <span>{popoverText || "删除"}？</span>
              </div>
            </div>
          </>
        }
        onConfirm={(e) => {
          e?.stopPropagation();
          if (record) {
            deleteUsersByIdsFn([record.id]);
            return;
          }
          if (popoverText === "清空") {
            clearResignedUsersFn();
            return;
          }
          deleteUsersByIdsFn(selectedRowKeys);
        }}
        onCancel={(e) => {
          e?.stopPropagation();
        }}
        okText="确认"
        cancelText="取消"
      >
        <Button
          style={{
            border: "1px solid #EBEBEB",
            color: "#555555",
            marginRight: "16px"
          }}
          disabled={
            popoverText === "清空" || from === "column"
              ? getEditPermission(userType, BTN_NAME.ADD)
              : getEditPermission(userType, BTN_NAME.ADD) ||
                !selectedRowKeys.length
          }
        >
          {popoverText}
        </Button>
      </Popconfirm>
    );
  };
  return (
    <div className="p-[16px] h-full">
      <div className="flex justify-between">
        <div>
          {getBtn(
            getEditPermission(userType, BTN_NAME.ADD),
            <Button
              style={{
                border: "1px solid #EBEBEB",
                color: "#555555",
                marginRight: "16px"
              }}
              disabled={
                getEditPermission(userType, BTN_NAME.ADD) ||
                !selectedRowKeys.length
              }
            >
              删除
            </Button>,
            "删除"
          )}
          {getBtn(
            getEditPermission(userType, BTN_NAME.ADD),
            <Button
              style={{
                border: "1px solid #EBEBEB",
                color: "#555555",
                marginRight: "16px"
              }}
              disabled={
                getEditPermission(userType, BTN_NAME.ADD) ||
                !selectedRowKeys.length
              }
            >
              清空
            </Button>,
            "清空"
          )}
        </div>
        <div className="flex">
          <RangePicker
            style={{ width: "250px", marginRight: "16px" }}
            onChange={handleDatePicker}
          />
          <Input
            placeholder="请输入成员姓名"
            suffix={
              <SearchOutlined
                onClick={() => {
                  if (pageNo !== 1) {
                    setPageNo(1);
                  } else {
                    searchResignedUserListFn();
                  }
                }}
              />
            }
            style={{ width: "250px" }}
            value={searchInput}
            onChange={(e) => setSearchInput(e?.target?.value || "")}
            onPressEnter={handleKeyDown}
          />
        </div>
      </div>

      <div ref={tableBoxRef} className="h-[calc(100%-50px)]">
        <Table
          columns={columns}
          dataSource={resignedList}
          className="mt-[20px]"
          rowKey="id"
          pagination={false}
          loading={tableLoading}
          scroll={{
            x: "max-content",
            y: tableHeight > 415 ? undefined : tableHeight - 130
          }}
          rowSelection={{
            type: "checkbox",
            onChange: (selectedRowKeys: any, selectedRows: any[]) => {
              setSelectedRowKeys(selectedRowKeys);
            }
          }}
        />
        <Pagination
          align="end"
          className="mt-[10px]"
          current={pageNo}
          total={total}
          pageSize={5}
          size="small"
          hideOnSinglePage
          onChange={(page: number, pageSize: number) => {
            setPageNo(page);
          }}
        />
      </div>
    </div>
  );
};

export default Resigned;
