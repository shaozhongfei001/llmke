import {
  CaretDownOutlined,
  CaretRightOutlined,
  CloseOutlined,
  EllipsisOutlined,
  MinusCircleTwoTone,
  PlusCircleTwoTone,
  SearchOutlined
} from "@ant-design/icons";
import useSystemApi from "@root/src/apis/system";
import {
  Button,
  ConfigProvider,
  Drawer,
  Dropdown,
  Input,
  MenuProps,
  message,
  Popover,
  Table,
  TableProps
} from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { uid } from "uid";
import { AddOrEditDepartment, BatchExport, BatchImport } from "./drawerContent";
import axios$ from "@root/src/apis";
import { getUrlPrefix, useAppPassport } from "@root/src/core/helps";
import DeleteConfirm from "@root/src/components/DeletModal";
import LinkItemsBtn from "./components/listItemsBtn";
import {
  BTN_NAME,
  getEditPermission,
  PERMISSION_WARNING_MSG,
  USER_STATUS
} from "@root/src/const/permission";
import CustomTooltip from "@root/src/components/CustomTooltip";
const DRAWER_WIDTH = 557;
type TCallback = (res?: any) => void;

const DepartmentManage = ({ userType }: { userType: USER_STATUS }) => {
  const { getToken } = useAppPassport();
  const api = useSystemApi();
  const [drawWidth, setDrawWidth] = useState<number | string>(DRAWER_WIDTH);
  const [treeLoading, setTreeLoading] = useState(false);
  const [saveBtnLoading, setSaveBtnLoading] = useState(false);
  const [openDraw, setOpenDraw] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys]: any = useState([]);
  const [tempData, setTempData]: any = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [drawConfig, setDrawConfig] = useState<{ type: string; data: any }>({
    type: "add",
    data: null
  });
  const [deptTreeData, setDeptTreeData]: any = useState([
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
      title: "部门名称",
      dataIndex: "name",
      key: "name",
      minWidth: 120
    },
    {
      title: "部门人数",
      dataIndex: "userCount",
      key: "userCount",
      minWidth: 120
    },
    {
      title: "上级部门",
      dataIndex: "parentDeptName",
      key: "parentDeptName",
      minWidth: 120
    },
    {
      title: "操作",
      dataIndex: "action",
      key: "action",
      width: 260,
      render: (_: any, record: any) => {
        return (
          <>
            <CustomTooltip
              content={
                getEditPermission(userType, BTN_NAME.ADD)
                  ? PERMISSION_WARNING_MSG
                  : ""
              }
              type="warning"
            >
              <Button
                type="link"
                onClick={() => rightEvent("add", record)}
                disabled={getEditPermission(userType, BTN_NAME.ADD)}
              >
                添加子部门
              </Button>
            </CustomTooltip>
            <CustomTooltip
              content={
                getEditPermission(userType, BTN_NAME.ADD)
                  ? PERMISSION_WARNING_MSG
                  : ""
              }
              type="warning"
            >
              <Button
                type="link"
                onClick={() => rightEvent("edit", record)}
                disabled={getEditPermission(userType, BTN_NAME.ADD)}
              >
                编辑部门
              </Button>
            </CustomTooltip>
            <Dropdown menu={{ items: getRightItems(record) }}>
              <a onClick={(e) => e.preventDefault()}>
                <EllipsisOutlined />
              </a>
            </Dropdown>
          </>
        );
      }
    }
  ];

  const getRightItems = (record: any) => {
    return [
      // {
      //   key: "1",
      //   label: (
      //     <a href="javascript:void(0);" className="!text-primary-color">
      //       上移
      //     </a>
      //   )
      // },
      // {
      //   key: "2",
      //   label: (
      //     <a href="javascript:void(0);" className="!text-primary-color">
      //       下移
      //     </a>
      //   )
      // },
      {
        key: "3",
        label: (
          <LinkItemsBtn
            item={{ name: "删除", key: "delete" }}
            handleEvent={() => rightEvent("delete", record)}
            disabled={getEditPermission(userType, BTN_NAME.ADD)}
            tip={
              getEditPermission(userType, BTN_NAME.ADD)
                ? PERMISSION_WARNING_MSG
                : ""
            }
          />
        )
      }
    ];
  };

  const uploadFilesOrUrls = (
    formData: FormData,
    sucFn?: TCallback,
    failFn?: TCallback,
    finFn?: TCallback
  ) => {
    const _url = `${getUrlPrefix()}/auth/departmentInfo/import`;

    setSaveBtnLoading(true);
    axios$
      .post(_url, formData, {
        headers: {
          Authorization: getToken() || ""
        }
      })
      .then((res: any) => {
        if (res) {
          const { success, data } = res;
          getDepartmentInfo();
          if (res.data.length) {
            failFn && failFn(res.data);
          } else {
            sucFn && sucFn(data);
          }
        } else {
          failFn && failFn();
        }
      })
      .finally(() => {
        if (finFn) {
          finFn();
        } else {
          setSaveBtnLoading(false);
        }
      })
      .catch((e) => {
        console.log(e);
      });
  };

  const handleTriggerUpload = (fList: any[], cb?: (arg?: any) => void) => {
    if (!fList.length) return;
    const _formData = new FormData();
    _formData.append("file", fList[0]);
    uploadFilesOrUrls(
      _formData,
      () => {
        setOpenDraw(false);
        setDrawWidth(DRAWER_WIDTH);
        cb && cb([]);
      },
      (data) => {
        setDrawWidth("100%");
        cb && cb(data);
      }
    );
  };

  const getDepartmentInfo = async () => {
    setTreeLoading(true);
    try {
      const res: any = await api.getTreeDeptById({}, {});
      setTreeLoading(false);
      if (res.success) {
        setDeptTreeData(res.data);
      }
    } catch (error) {
      setTreeLoading(false);
      console.log("error", error);
    }
  };
  const rowSelection: TableProps<any>["rowSelection"] = {
    onChange: (selectedRowKeys: React.Key[], selectedRows: any[]) => {
      setSelectedRowKeys(selectedRowKeys);
    },
    selectedRowKeys
  };

  const deleteDepartmentFn = async (params: any) => {
    try {
      setSaveBtnLoading(true);
      const api_delete = params.ids
        ? api.deleteBatchDepartment
        : api.deleteDepartment;
      const res: any = await api_delete(params);
      setSaveBtnLoading(false);
      if (res.success) {
        setShowDeleteModal(false);
        getDepartmentInfo();
      }
    } catch (error) {
      setSaveBtnLoading(false);
      console.log("error", error);
    }
  };

  const createDepartmentFn = async (item: any) => {
    try {
      setSaveBtnLoading(true);
      const res: any = await api.createDepartment({
        name: item.name,
        parentId: item.parentId
      });
      setSaveBtnLoading(false);
      if (res.success) {
        setOpenDraw(false);
        getDepartmentInfo();
      }
    } catch (error) {
      setSaveBtnLoading(false);
      console.log("error", error);
    }
  };

  const editDepartmentFn = async (item: any) => {
    try {
      setSaveBtnLoading(true);
      const res: any = await api.editDepartment({
        name: item.name,
        parentId: item.parentId,
        id: drawConfig.data.id
      });
      setSaveBtnLoading(false);
      if (res.success) {
        setOpenDraw(false);
        getDepartmentInfo();
      }
    } catch (error) {
      setSaveBtnLoading(false);
      console.log("error", error);
    }
  };

  const departmentExportFn = async (params: any) => {
    const queryParams = new URLSearchParams(params);
    setSaveBtnLoading(true);
    fetch(
      `${getUrlPrefix()}/auth/departmentInfo/export?${queryParams.toString()}`,
      {
        method: "GET",
        headers: {
          Authorization: getToken() || ""
        }
      }
    )
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.blob(); // 获取Blob对象
      })
      .then((blob) => {
        setSaveBtnLoading(false);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        a.download = "用户信息模板";
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url); // 释放URL对象
        document.body.removeChild(a);
        setSaveBtnLoading(false);
      })
      .catch((error) => {
        setSaveBtnLoading(false);
        console.error(
          "There has been a problem with your fetch operation:",
          error
        );
      });
  };

  const handleEvent = (type: string, data?: any, cb?: (arg?: any) => void) => {
    switch (type) {
      case "save:batchExport":
        departmentExportFn(data ? { pids: data } : {});
        break;
      case "save:importUser":
        handleTriggerUpload(data, cb);
        break;
      case "save:editDepartment":
        editDepartmentFn(data);
        break;
      case "save:addDepartment":
        createDepartmentFn(data);
        break;
      case "batchExport":
        setDrawConfig({ type, data });
        setOpenDraw(true);
        break;
      case "reImport":
        setDrawWidth(DRAWER_WIDTH);
        break;
      case "closeDrawer":
        setOpenDraw(false);
        break;
      case "batchImport":
        setDrawConfig({ type, data });
        setOpenDraw(true);
        break;
    }
  };

  const rightEvent = (type: string, data?: any) => {
    console.log("====================================");
    console.log("t->", type, "d->", data);
    console.log("====================================");
    switch (type) {
      case "add":
        setDrawConfig({ type: "add", data });
        setOpenDraw(true);
        break;
      case "edit":
        setDrawConfig({ type, data });
        setOpenDraw(true);
        break;
      case "delete":
        setTempData(data);
        setShowDeleteModal(true);
        break;
      case "prev":
        break;
      case "next":
        break;
    }
  };

  useEffect(() => {
    getDepartmentInfo();
  }, []);

  useEffect(() => {
    setDrawWidth(DRAWER_WIDTH);
  }, [openDraw]);
  const [tableHeight, setTableHeight] = useState(500);
  const tableBoxRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (tableBoxRef.current) {
      const tableBoxHeight = tableBoxRef.current.offsetHeight;
      setTableHeight(tableBoxHeight);
    }
  }, []);

  const filteredDept = useMemo(() => {
    if (!deptTreeData) return deptTreeData;

    const filterTree = (nodes: any[], search: string): any[] => {
      return nodes
        .map((node) => {
          const match = node.name.toLowerCase().includes(search.toLowerCase());
          if (node.children) {
            const filteredChildren = filterTree(node.children, search);
            if (filteredChildren.length > 0 || match) {
              return { ...node, children: filteredChildren };
            }
          }
          return match ? { ...node, children: [] } : null;
        })
        .filter((node) => node !== null);
    };

    return filterTree(deptTreeData[0]?.children || [], searchInput);
  }, [deptTreeData, searchInput]);
  return (
    <div className="p-[16px] h-full">
      <div className="flex justify-between">
        <div className="flex">
          <CustomTooltip
            content={
              getEditPermission(userType, BTN_NAME.ADD)
                ? PERMISSION_WARNING_MSG
                : ""
            }
            type="warning"
          >
            <Button
              style={{
                marginRight: "16px",
                border: getEditPermission(userType, BTN_NAME.ADD)
                  ? "1px solid rgb(235, 235, 235)"
                  : "none",
                color: getEditPermission(userType, BTN_NAME.ADD)
                  ? "rgb(85, 85, 85)"
                  : "#fff",
                background: getEditPermission(userType, BTN_NAME.ADD)
                  ? "rgba(0,0,0,.04)"
                  : "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
              }}
              onClick={() =>
                rightEvent("add", { type: "add", id: deptTreeData[0]?.id })
              }
              disabled={getEditPermission(userType, BTN_NAME.ADD)}
            >
              新建部门
            </Button>
          </CustomTooltip>
          <CustomTooltip
            content={
              getEditPermission(userType, BTN_NAME.ADD)
                ? PERMISSION_WARNING_MSG
                : ""
            }
            type="warning"
          >
            <Button
              style={{
                border: "1px solid #EBEBEB",
                color: "#555555",
                marginRight: "16px"
              }}
              onClick={() => handleEvent("batchImport")}
              disabled={getEditPermission(userType, BTN_NAME.ADD)}
            >
              批量导入
            </Button>
          </CustomTooltip>{" "}
          <CustomTooltip
            content={
              getEditPermission(userType, BTN_NAME.ADD)
                ? PERMISSION_WARNING_MSG
                : ""
            }
            type="warning"
          >
            <Button
              style={{
                border: "1px solid #EBEBEB",
                color: "#555555",
                marginRight: "16px"
              }}
              onClick={() => handleEvent("batchExport")}
              disabled={getEditPermission(userType, BTN_NAME.ADD)}
            >
              批量导出
            </Button>
          </CustomTooltip>
          <CustomTooltip
            content={
              getEditPermission(userType, BTN_NAME.ADD)
                ? PERMISSION_WARNING_MSG
                : ""
            }
            type="warning"
          >
            <Button
              style={{
                border: "1px solid #E33737",
                color: "#E33737",
                marginRight: "16px"
              }}
              onClick={() => {
                rightEvent("delete", { ids: selectedRowKeys.join(",") });
              }}
              disabled={
                getEditPermission(userType, BTN_NAME.ADD) ||
                !selectedRowKeys.length
              }
            >
              批量删除
            </Button>
          </CustomTooltip>
        </div>
        <Input
          placeholder="搜索部门名"
          suffix={<SearchOutlined />}
          value={searchInput}
          onChange={(e) => setSearchInput(e?.target?.value || "")}
          className="mb-[10px] mr-[16px] w-[200px]"
        />
      </div>
      <div ref={tableBoxRef} className="h-[calc(100%-30px)] w-full">
        <Table
          columns={columns}
          dataSource={filteredDept}
          className="mt-[20px]"
          rowKey="id"
          loading={treeLoading}
          rowSelection={{ ...rowSelection }}
          pagination={{ pageSize: 5, size: "small" }}
          scroll={{
            x: "max-content",
            y: tableHeight - 160
          }}
          expandable={{
            expandIcon: ({ expanded, onExpand, record }: any) => {
              return record?.children?.length ? (
                expanded ? (
                  <CaretDownOutlined
                    onClick={(e) => onExpand(record, e)}
                    className="mr-[10px] text-[#888888]"
                  />
                ) : (
                  <CaretRightOutlined
                    onClick={(e) => onExpand(record, e)}
                    className="mr-[10px] text-[#888888]"
                  />
                )
              ) : null;
            }
          }}
        />
      </div>
      <ConfigProvider
        drawer={{
          styles: {
            body: { padding: 0 },
            header: { padding: "20px 20px 16px 20px" }
          }
        }}
      >
        <Drawer
          title={
            <div className="flex justify-between items-center">
              <div className="text-[16px] font-bold">
                {drawConfig.type === "add"
                  ? "新建部门"
                  : drawConfig.type === "edit"
                  ? "编辑部门"
                  : drawConfig.type === "batchImport"
                  ? "批量导入"
                  : drawConfig.type === "batchExport"
                  ? "批量导出"
                  : ""}
              </div>
              <CloseOutlined
                className="cursor-pointer"
                onClick={() => setOpenDraw(false)}
              />
            </div>
          }
          closable={false}
          width={drawWidth}
          onClose={() => setOpenDraw(false)}
          open={openDraw}
          destroyOnClose
        >
          <div className="h-[calc(100vh-62px)] relative px-[20px] pt-[10px] pb-[20px]">
            {(drawConfig.type === "add" || drawConfig.type === "edit") && (
              <AddOrEditDepartment
                drawConfig={drawConfig}
                deptTreeData={deptTreeData}
                handleEvent={handleEvent}
                btnLoading={saveBtnLoading}
              />
            )}
            {drawConfig.type === "batchImport" && (
              <BatchImport
                drawConfig={drawConfig}
                handleEvent={handleEvent}
                btnLoading={saveBtnLoading}
                type={"dept"}
              />
            )}
            {drawConfig.type === "batchExport" && (
              <BatchExport
                drawConfig={drawConfig}
                deptTreeData={deptTreeData}
                handleEvent={handleEvent}
                btnLoading={saveBtnLoading}
              />
            )}
          </div>
        </Drawer>
      </ConfigProvider>
      <DeleteConfirm
        isShowDeleteModal={showDeleteModal}
        loading={saveBtnLoading}
        confirmModal={() => {
          deleteDepartmentFn(tempData);
        }}
        closeModal={() => {
          setShowDeleteModal(false);
        }}
      />
    </div>
  );
};

export default DepartmentManage;
