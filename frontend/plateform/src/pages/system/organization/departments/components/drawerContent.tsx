import Icon, {
  ApartmentOutlined,
  CaretDownOutlined,
  CloseCircleFilled,
  CopyOutlined,
  DownloadOutlined,
  InfoCircleFilled,
  SearchOutlined
} from "@ant-design/icons";
import "./style.css";
import {
  Button,
  Upload,
  Form,
  Input,
  Select,
  TreeSelect,
  UploadProps,
  Table,
  Progress,
  Radio,
  Checkbox,
  RadioChangeEvent,
  Tree,
  message
} from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import xiazaiexcel from "@/assets/img/xiazaiexcel 1.png";
import excel from "@/assets/img/excel.png";
import { FILEIMG, getUrlPrefix, useAppPassport } from "@root/src/core/helps";
import IconHeader from "@root/src/pages/Components/IconHeader";
import useSystemApi from "@root/src/apis/system";
import { ELEMENT_TYPE, USER_STATUS } from "@root/src/const/permission";
import DepartmentSelect from "./components/departmentSelect";
import ResourceTable from "./components/EditTable";
const { Dragger } = Upload;
const DEFALT_RESOURCE = [
  {
    id: 1,
    resource: "知识库",
    description: "转让该成员创建的所有知识库"
  },
  {
    id: 2,
    resource: "问答助手",
    description: "转让该成员创建的所有问答助手"
  },
  {
    id: 3,
    resource: "模型",
    description: "转让该成员创建的所有模型"
  }
  // {
  //   id: 4,
  //   resource: "知识库文件",
  //   description: "转让该成员创建的所有知识库文件"
  // }
];

const DEFALT_RESOURCE_OPTIONS = [
  { label: "知识库", value: 1 },
  { label: "问答助手", value: 2 },
  { label: "模型", value: 3 }
  // { label: "知识库文件", value: 4 }
];

export const ChangeDepartment = ({
  drawConfig,
  handleEvent,
  deptTreeData,
  btnLoading
}: {
  drawConfig: { type: string; data: any };
  handleEvent: (type: string, data?: any, cb?: (arg?: any) => void) => void;
  deptTreeData: any[];
  btnLoading: boolean;
}) => {
  const [searchInput, setSearchInput] = useState("");
  const [selected, setSelected] = useState<any>("1");

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

    return filterTree(deptTreeData || [], searchInput);
  }, [deptTreeData, searchInput]);

  useEffect(() => {
    setSelected(drawConfig.data.deptId || "");
  }, [drawConfig]);

  return (
    <div className="w-full h-full pt-[12px]">
      <div className="h-[calc(100%-80px)]">
        <DepartmentSelect
          searchInput={searchInput}
          onSearchChange={(e: any) => setSearchInput(e?.target?.value || "")}
          treeData={filteredDept}
          checkedKey={selected}
          onTreeCheck={(checkedKeys: any, e: any) => {
            if (e.checked) {
              setSelected(e.node.id);
            } else {
              setSelected(null);
            }
          }}
        />
      </div>
      <div className="h-[20px] w-[5px]"></div>
      <div
        className="flex justify-end h-[38px] pt-[16px]"
        style={{ borderTop: "1px solid #EBEBEB" }}
      >
        <Button
          style={{
            border: "1px solid #EBEBEB",
            color: "#555555",
            marginRight: "16px"
          }}
          onClick={() => {
            handleEvent("closeDrawer");
          }}
        >
          取消
        </Button>
        <Button
          style={{
            border: "none",
            color: "#fff",
            background:
              "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
          }}
          loading={btnLoading}
          onClick={() => {
            handleEvent("save:changeDepartment", { deptId: selected });
          }}
        >
          确认
        </Button>
      </div>
    </div>
  );
};

export const BatchExport = ({
  drawConfig,
  deptTreeData,
  handleEvent,
  btnLoading
}: {
  drawConfig: { type: string; data: any };
  deptTreeData: any[];
  handleEvent: (type: string, data?: any, cb?: (arg?: any) => void) => void;
  btnLoading: boolean;
}) => {
  const [value, setValue] = useState(1);
  const [showModal, setShowModal] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [selected, setSelected] = useState<any>("1");
  const onChange = (e: RadioChangeEvent) => {
    if (e.target.value === 2) {
      setShowModal(true);
    }
    setValue(e.target.value);
  };

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

    return filterTree(deptTreeData || [], searchInput);
  }, [deptTreeData, searchInput]);

  return (
    <div className="w-full h-full pt-[12px] overflow-y-auto">
      <div className="h-[calc(100%-60px)] overflow-y-auto">
        <div>编辑管理范围</div>
        <Radio.Group
          onChange={onChange}
          value={value}
          className="mt-[12px]"
          options={[
            {
              value: 1,
              label: "全部"
            },
            {
              value: 2,
              label: "部分成员"
            }
          ]}
        />
        {value === 2 && (
          <div className="h-[calc(100%-120px)] mt-[10px]">
            <DepartmentSelect
              searchInput={searchInput}
              onSearchChange={(e: any) =>
                setSearchInput(e?.target?.value || "")
              }
              mode="multiple"
              treeData={filteredDept}
              checkedKey={selected}
              onTreeCheck={(checkedKeys: any, e: any) => {
                setSelected(checkedKeys.checked);
              }}
            />
          </div>
        )}
      </div>
      <div
        className="flex justify-end h-[38px] pt-[16px]"
        style={{ borderTop: "1px solid #EBEBEB" }}
      >
        <Button
          style={{
            border: "1px solid #EBEBEB",
            color: "#555555",
            marginRight: "16px"
          }}
          onClick={() => {
            handleEvent("closeDrawer");
          }}
        >
          取消
        </Button>
        <Button
          style={{
            border: "none",
            color: "#fff",
            background:
              "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
          }}
          onClick={() => {
            handleEvent(
              "save:batchExport",
              value === 1 ? null : selected.join(",")
            );
          }}
        >
          确认
        </Button>
      </div>
    </div>
  );
};

export const Resignation = ({
  drawConfig,
  type,
  handleEvent,
  btnLoading
}: {
  drawConfig: { type: string; data: any; extraData?: any };
  type?: string;
  handleEvent: (type: string, data?: any, cb?: (arg?: any) => void) => void;
  btnLoading: boolean;
}) => {
  const api = useSystemApi();
  const { getUserInfo } = useAppPassport();
  const [value, setValue] = useState(2);
  const [checkValue, setCheckValue] = useState([]);
  const [form] = Form.useForm();
  const [data, setData]: any = useState(DEFALT_RESOURCE);
  const [options, setOptions]: any = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    searchUserListFn();
  }, []);

  useEffect(() => {
    if (options.length) {
      const userInfo: any = getUserInfo();
      setData((pre: any) => {
        const res = pre.map((item: any) => {
          return { ...item, userId: userInfo.id };
        });
        return res;
      });
    }
  }, [options]);

  useEffect(() => {
    const userInfo: any = getUserInfo();
    const updatedData = checkValue.map((v) => {
      const existingItem = data.find((item: any) => {
        return item.id === DEFALT_RESOURCE.find((r) => r.id === v)?.id;
      });
      return existingItem || DEFALT_RESOURCE.find((r) => r.id === v);
    });
    setData(
      updatedData.map((item: any) => {
        return { ...item, userId: item.userId || userInfo.id };
      })
    );
  }, [checkValue, getUserInfo]);

  useEffect(() => {
    if (Array.isArray(data)) {
    } else {
      if (value === 2) {
        setData(DEFALT_RESOURCE);
      }
    }
  }, [value]);

  const searchUserListFn = async (newValue?: any) => {
    try {
      setLoading(true);
      const res: any = await api.searchUserList({
        pageSize: 9999,
        pageNo: 1,
        idOrName: newValue
      });
      setLoading(false);
      if (res.success) {
        setOptions(res.data.records);
      }
    } catch (error) {
      setLoading(false);
      console.log("error", error);
    }
  };
  const handleSearch = (newValue: string) => {
    return;
    searchUserListFn(newValue);
  };

  const checkOptions = useMemo(() => {
    const transferTypes = Array.isArray(drawConfig?.data)
      ? [1, 2, 3]
      : drawConfig?.extraData?.transferType;
    if (transferTypes) {
      setCheckValue(transferTypes);
      return DEFALT_RESOURCE_OPTIONS.filter((item: any) => {
        return transferTypes.includes(item.value);
      });
    } else {
      return [];
    }
  }, [drawConfig]);

  const getTransferParams = () => {
    let flag = true;
    const users = Array.isArray(drawConfig.data)
      ? drawConfig.data
      : [drawConfig.data];

    const r = users.map((item: any) => {
      return {
        transferType: value,
        transferProperties: data.map((v: any) => {
          if (item.id === v.userId) {
            flag = false;
            return;
          }
          return {
            userId: item.id,
            targetUserId: v.userId,
            type: v.id
          };
        })
      };
    });

    if (!flag) {
      message.warning("接收方不能为自己，请重新填写");
      return false;
    }
    return r;
  };

  return (
    <div className="w-full h-full pt-[12px]">
      <div className="h-[calc(100%-60px)] overflow-y-auto">
        {Array.isArray(drawConfig.data) ? (
          <div className="flex">
            {drawConfig.data.map((item: any) => {
              return (
                <div className="h-[28px] rounded-full bg-[#E8E8E8] flex items-center mr-[16px]">
                  <IconHeader
                    text={item.userRealname || ""}
                    rounded="rounded-full"
                    size={28}
                    len={2}
                    fontSize="text-[10px]"
                    mr="mr-[4px]"
                  />
                  <div className="text-[12px] font-[500] text-text-color1 mr-[6px]">
                    {item.userRealname}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex">
            <IconHeader
              text={drawConfig.data.userRealname || ""}
              rounded="rounded-full"
              size={50}
              len={2}
              type={ELEMENT_TYPE.USER}
            />
            <div>
              <div className="text-[20px] font-[500] text-text-color1">
                {drawConfig.data.userRealname}
              </div>
              <div className="text-text-color2 mt-[2px]">
                用户ID：{drawConfig.data.id}
              </div>
            </div>
          </div>
        )}
        {type !== "transfer" && (
          <>
            <div className="mt-[30px] text-[16px] text-text-color1 font-[500]">
              将成员拥有的资源
            </div>
            <Radio.Group
              className="mt-[20px]"
              onChange={(v) => {
                setValue(v.target.value);
              }}
              value={value}
              options={[
                {
                  value: 2,
                  label: "转移给其他用户"
                },
                {
                  value: 1,
                  label: "删除"
                }
              ]}
            />
          </>
        )}

        {value === 2 ? (
          <>
            {checkOptions.length ? (
              <>
                <div className="mt-[30px] text-[16px] text-text-color1 font-[500]">
                  选择要转移的资源
                </div>
                <Checkbox.Group
                  className="mt-[20px]"
                  options={checkOptions}
                  value={checkValue}
                  onChange={(checkedValues: any) => {
                    setCheckValue(checkedValues);
                  }}
                />
                <div className="mt-[20px] text-[16px] text-text-color1 font-[500]">
                  设置资源接收人
                </div>
                <div className="mt-[20px]">
                  <ResourceTable
                    data={data}
                    setData={setData}
                    form={form}
                    options={options}
                    handleSearch={handleSearch}
                    loading={loading}
                  />
                </div>
              </>
            ) : (
              <div className="mt-[10px]">暂无资源</div>
            )}
          </>
        ) : (
          <>
            <div className="h-[60px] bg-[#FAFAFA] rounded-[4px] flex items-center justify-center mt-[20px]">
              <InfoCircleFilled className="text-[#FAAD14] text-[20px] mr-[8px]" />
              <div className="text-[14px] text-text-color1">
                系统将：删除该成员创建的所有文档
              </div>
            </div>
          </>
        )}
      </div>
      <div
        className="flex justify-end h-[38px] pt-[16px]"
        style={{ borderTop: "1px solid #EBEBEB" }}
      >
        <Button
          style={{
            border: "1px solid #EBEBEB",
            color: "#555555",
            marginRight: "16px"
          }}
          onClick={() => {
            handleEvent("closeDrawer");
          }}
        >
          取消
        </Button>
        <Button
          style={{
            border: "none",
            color: "#fff",
            background:
              "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
          }}
          onClick={() => {
            const p = getTransferParams();
            if (type === "transfer") {
              p && handleEvent("save:transferPropertyFn", p);
            } else {
              if (!p) return;
              handleEvent("save:resignation", drawConfig.data, () => {
                if (value === 2 && data?.length) {
                  handleEvent("save:transferPropertyFn", p);
                } else {
                  handleEvent("closeDrawerAndFresh");
                }
              });
            }
          }}
          loading={btnLoading}
        >
          确认
        </Button>
      </div>
    </div>
  );
};
let percentInterval: any = null;

export const BatchImport = ({
  drawConfig,
  handleEvent,
  btnLoading,
  type
}: {
  drawConfig: { type: string; data: any };
  handleEvent: (type: string, data?: any, cb?: (arg?: any) => void) => void;
  btnLoading: boolean;
  type?: string;
}) => {
  const { getToken } = useAppPassport();
  const [saveLoading, setSaveLoading] = useState(false);
  const [percent, setPercent] = useState(0);
  const [errorList, setErrorList]: any = useState([]);

  useEffect(() => {
    if (saveLoading) {
      percentInterval = setInterval(() => {
        setPercent((prevPercent) => {
          if (prevPercent >= 90) {
            clearInterval(percentInterval);
            setSaveLoading(false);
            return 100;
          }
          return prevPercent + 10;
        });
      }, 500);
    }
  }, [saveLoading]);
  const columns = [
    {
      title: "用户登录名",
      dataIndex: "userName",
      key: "userName"
    },
    {
      title: "姓名",
      dataIndex: "userRealname",
      key: "userRealname"
    },
    {
      title: "密码",
      dataIndex: "userPassword",
      key: "userPassword"
    },
    {
      title: "手机号码",
      dataIndex: "userPhone",
      key: "userPhone"
    },
    {
      title: "邮箱",
      dataIndex: "userEmail",
      key: "userEmail"
    },
    {
      title: "部门",
      dataIndex: "deptPath",
      key: "deptPath"
    },
    {
      title: "角色",
      dataIndex: "roleName",
      key: "roleName"
    },
    {
      title: "失败原因",
      dataIndex: "errorMsg",
      key: "errorMsg"
    }
  ];
  const columns2 = [
    {
      title: "部门名称",
      dataIndex: "name",
      key: "name"
    },
    {
      title: "部门人数",
      dataIndex: "userCount",
      key: "userCount"
    },
    {
      title: "上级部门名称",
      dataIndex: "parentDeptName",
      key: "parentDeptName"
    },
    {
      title: "失败原因",
      dataIndex: "errorMsg",
      key: "errorMsg"
    }
  ];
  const [fileList, setFileList]: any = useState([]);
  const [showError, setShowError]: any = useState(false);
  const props: UploadProps = {
    name: "file",
    multiple: false,
    onChange(info) {
      const { status } = info.file;
      setFileList([info.file]);
      if (status !== "uploading") {
        console.log(info.file, info.fileList);
      }
      if (status === "done") {
      } else if (status === "error") {
      }
    },
    accept: ".xlsx",
    onDrop(e) {
      console.log("Dropped files", e.dataTransfer.files);
    },
    beforeUpload: () => {
      return false;
    }
  };

  const handleDownload = (
    filePath: string,
    fileType: string,
    name?: string
  ) => {
    if (filePath) {
      fetch(filePath, {
        method: "GET",
        headers: {
          Authorization: getToken() || ""
        }
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Network response was not ok");
          }
          return response.blob(); // 获取Blob对象
        })
        .then((blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.style.display = "none";
          a.href = url;
          a.download = `${name || "用户信息模板"}.${fileType}`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url); // 释放URL对象
          document.body.removeChild(a);
        })
        .catch((error) => {
          console.error(
            "There has been a problem with your fetch operation:",
            error
          );
        });
    }
  };

  return (
    <div className="w-full h-full">
      <div className="h-[calc(100%-18px)] overflow-y-auto">
        {showError ? (
          <>
            <div className="h-[77px] rounded-[4px] bg-[#F8F9FA] flex justify-center items-center">
              <CloseCircleFilled className="text-[#FF4D4F] text-[20px] mr-[16px]" />
              <div className="text-[16px]">
                导入失败 {errorList.length} {type === "dept" ? "个部门" : "人"}
              </div>
            </div>
            <div className="mt-[20px] flex justify-between">
              <div>
                以下为导入失败的成员列表，可
                <span
                  className="text-primary-color cursor-pointer"
                  onClick={() =>
                    handleDownload(
                      type === "dept"
                        ? `${getUrlPrefix()}/auth/departmentInfo/exportError`
                        : `${getUrlPrefix()}/auth/user/exportError`,
                      "xlsx",
                      "错误报告"
                    )
                  }
                >
                  下载错误报告
                </span>
                ，修改后重新导入
              </div>
              <Button
                style={{
                  border: "none",
                  color: "#fff",
                  background:
                    "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
                }}
                onClick={() => {
                  setShowError(false);
                  handleEvent("reImport");
                  setFileList([]);
                }}
              >
                重新导入
              </Button>
            </div>
            <Table
              className="mt-[20px]"
              columns={type === "dept" ? columns2 : columns}
              dataSource={errorList}
              pagination={{ pageSize: 5, hideOnSinglePage: true }}
            />
          </>
        ) : (
          <>
            <div className="h-[140px] rounded-[4px] p-[20px] bg-[#F8F9FA]">
              <div className="text-[16px] font-[500] text-text-color1 flex">
                <div className="w-[24px] h-[24px] bg-[#2B69FF] text-white rounded-full flex justify-center items-center mr-[16px]">
                  1
                </div>
                下载导入模板
              </div>
              <div className="mt-[12px] text-[14px] text-text-color2">
                根据提示信息完善表格内容
              </div>
              <Button
                className="mt-[12px] text-text-color2"
                icon={<DownloadOutlined />}
                style={{
                  border: "1px solid #EBEBEB"
                }}
                onClick={() => {
                  handleDownload(
                    type === "dept"
                      ? `${getUrlPrefix()}/auth/departmentInfo/downloadTemplate?fileType=xlsx`
                      : `${getUrlPrefix()}/auth/user/downloadTemplate?fileType=xlsx`,
                    "xlsx",
                    type === "dept" ? "部门信息模板" : ""
                  );
                }}
              >
                下载空的模板表格
              </Button>
            </div>
            <div className="h-[362px] rounded-[4px] p-[20px] bg-[#F8F9FA] mt-[20px]">
              <div className="text-[16px] font-[500] text-text-color1 flex">
                <div className="w-[24px] h-[24px] bg-[#2B69FF] text-white rounded-full flex justify-center items-center mr-[16px]">
                  2
                </div>
                上传完善后的模板
              </div>
              <div className="mt-[12px] text-[14px] text-text-color2">
                更新信息的模板中，如有空的数据列，则相应字段信息会被清空，请谨慎填写
              </div>
              <div className="h-[245px] mt-[20px]">
                <Dragger
                  {...props}
                  style={{ border: "1px solid #EBEBEB", background: "#FFFFFF" }}
                  showUploadList={false}
                >
                  {saveLoading ? (
                    <div className="w-full h-full flex justify-center items-center">
                      <div className="flex items-center">
                        <img src={excel} height={72} />
                        <div className="flex flex-col items-start">
                          <div>
                            {fileList?.[0]?.name || "sgga"}（
                            {fileList?.[0]?.size}）
                          </div>
                          <Progress
                            percent={percent}
                            size="small"
                            className="w-[321px]"
                          />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="w-full h-full">
                      <div className="my-[12px] w-full flex justify-center">
                        <img
                          src={fileList.length ? excel : xiazaiexcel}
                          height={72}
                        />
                      </div>
                      {fileList.length ? (
                        <>
                          <div>
                            {fileList[0].name}（{fileList[0].size / 1024}KB）
                          </div>
                          <Button
                            style={{
                              marginTop: "20px",
                              border: "1px solid #EBEBEB",
                              color: "#555555"
                            }}
                          >
                            重新导入
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            style={{
                              border: "none",
                              color: "#fff",
                              background:
                                "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
                            }}
                          >
                            上传文件
                          </Button>
                          <div className="text-[#BBBBBB] mt-[16px]">
                            下载模板并完善信息后，可直接将文件拖拽到此处进行上传，
                            支持格式:XLSX
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </Dragger>
              </div>
            </div>
          </>
        )}
      </div>
      <div
        className="flex justify-end h-[38px] pt-[16px]"
        style={{ borderTop: "1px solid #EBEBEB" }}
      >
        {!showError && (
          <>
            {" "}
            <Button
              style={{
                border: "1px solid #EBEBEB",
                color: "#555555",
                marginRight: "16px"
              }}
              onClick={() => {
                handleEvent("closeDrawer");
              }}
            >
              取消
            </Button>
            <Button
              style={{
                border: "none",
                color: "#fff",
                background:
                  "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
              }}
              onClick={() => {
                setSaveLoading(true);
                handleEvent("save:importUser", fileList, (errorList: any[]) => {
                  setSaveLoading(false);
                  setPercent(0);
                  clearInterval(percentInterval);
                  if (errorList?.length) {
                    setErrorList(errorList);
                    setShowError(true);
                  }
                });
              }}
              loading={btnLoading}
            >
              确认
            </Button>
          </>
        )}
      </div>
    </div>
  );
};

export const AddOrEditDepartment = ({
  drawConfig,
  deptTreeData,
  handleEvent,
  btnLoading
}: {
  drawConfig: { type: string; data: any };
  deptTreeData?: any;
  handleEvent: (type: string, data?: any) => void;
  btnLoading: boolean;
}) => {
  const [form] = Form.useForm();

  useEffect(() => {
    if (drawConfig.type === "edit") {
      form.setFieldValue("name", drawConfig.data.name);
      form.setFieldValue("parentId", drawConfig.data.parentId);
    } else {
      form.resetFields();
      form.setFieldValue("parentId", drawConfig.data.id);
    }
  }, [drawConfig]);
  return (
    <div className="w-full h-full">
      <div className="h-[calc(100%-60px)] overflow-y-auto">
        <Form form={form} layout="vertical" className="mt-[8px]">
          <Form.Item
            label="部门名称"
            name="name"
            rules={[
              { required: true, message: "请输入部门名称" },
              { max: 100, message: "最大字数限制100" }
            ]}
          >
            <Input placeholder="请输入部门名称" className="w-full" />
          </Form.Item>
          <Form.Item label="上级部门" name="parentId">
            <TreeSelect
              style={{ width: "100%" }}
              dropdownStyle={{ maxHeight: 400, overflow: "auto" }}
              placeholder="请输入上级部门"
              treeData={deptTreeData}
              fieldNames={{ label: "name", value: "id" }}
              treeDefaultExpandAll
              disabled={
                drawConfig.data.id === deptTreeData?.[0]?.id &&
                drawConfig.type !== "add"
              }
            />
          </Form.Item>
        </Form>
      </div>

      <div
        className="flex justify-end h-[38px] pt-[16px]"
        style={{ borderTop: "1px solid #EBEBEB" }}
      >
        <Button
          style={{
            border: "1px solid #EBEBEB",
            color: "#555555",
            marginRight: "16px"
          }}
          onClick={() => {
            handleEvent("closeDrawer");
          }}
        >
          取消
        </Button>
        <Button
          style={{
            border: "none",
            color: "#fff",
            background:
              "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
          }}
          onClick={() => {
            form.validateFields().then((values) => {
              drawConfig.type === "add"
                ? handleEvent("save:addDepartment", values)
                : handleEvent("save:editDepartment", values);
            });
          }}
          loading={btnLoading}
        >
          确认
        </Button>
      </div>
    </div>
  );
};

export const AddOrEditMembers = ({
  drawConfig,
  deptTreeData,
  handleEvent,
  btnLoading
}: {
  btnLoading: boolean;
  drawConfig: { type: string; data: any };
  deptTreeData: any;
  handleEvent: (type: string, data?: any, cb?: () => void) => void;
}) => {
  const api = useSystemApi();
  const [form] = Form.useForm();
  const [isEdit, setIsEdit] = useState(true);
  const [roleList, setRoleList] = useState([]);
  const [createdData, setCreatedData]: any = useState(null);

  useEffect(() => {
    if (drawConfig.type === "viewMembers") {
      setIsEdit(false);
      form.setFieldsValue(drawConfig.data);
      const roleIds = (drawConfig.data.roles || []).map((item: any) => item.id);
      form.setFieldValue("roleIds", roleIds);
    } else {
      setIsEdit(true);
      form.resetFields();
    }
  }, [drawConfig]);

  const getRoleListFn = async () => {
    try {
      const res: any = await api.getRoleList({ pageNo: 1, pageSize: 9999 });
      if (res.success) {
        setRoleList(res.data.records);
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  const handleCopy = () => {
    if (!createdData) return;
    const textField = document.createElement("textarea");
    textField.innerText = createdData.userPassword;
    document.body.appendChild(textField);
    textField.select();
    document.execCommand("copy");
    textField.remove();
    message.success("复制成功");
  };

  useEffect(() => {
    getRoleListFn();
  }, []);

  return (
    <div className="w-full h-full">
      <div className="h-[calc(100%-60px)] overflow-y-auto">
        <Form
          form={form}
          layout="vertical"
          className="mt-[8px] h-[calc(100%-58px)]"
        >
          <Form.Item
            label={
              isEdit ? "用户名" : <div className="text-text-color3">用户名</div>
            }
            name="userName"
            rules={
              isEdit
                ? [
                    { required: true, message: "请输入用户名" },
                    { max: 100, message: "最大字数限制100" }
                  ]
                : []
            }
          >
            {isEdit ? (
              <Input
                placeholder="请输入用户名"
                className="w-full"
                disabled={!isEdit || drawConfig.type === "viewMembers"}
              />
            ) : (
              <div className="text-text-color1">
                {drawConfig.type === "addMembers"
                  ? createdData.userName
                  : drawConfig.data?.userName}
              </div>
            )}
          </Form.Item>
          <Form.Item
            label={
              isEdit ? "姓名" : <div className="text-text-color3">姓名</div>
            }
            name="userRealname"
            rules={
              isEdit
                ? [
                    { required: true, message: "请输入姓名" },
                    { max: 100, message: "最大字数限制100" }
                  ]
                : []
            }
          >
            {isEdit ? (
              <Input
                placeholder="请输入姓名"
                className="w-full"
                disabled={!isEdit}
              />
            ) : (
              <div className="text-text-color1">
                {drawConfig.type === "addMembers"
                  ? createdData.userRealname
                  : drawConfig.data?.userRealname}
              </div>
            )}
          </Form.Item>
          <Form.Item
            label={
              isEdit ? "手机号" : <div className="text-text-color3">手机号</div>
            }
            name="userPhone"
            rules={
              isEdit
                ? [
                    { required: true, message: "请输入手机号" },
                    {
                      pattern: /^(?:(?:\+|00)86)?1[3-9]\d{9}$/, // 中国大陆手机号正则
                      message: "请输入有效的手机号码！"
                    }
                  ]
                : []
            }
          >
            {isEdit ? (
              <Input
                placeholder="请输入手机号"
                className="w-full"
                addonBefore="+86"
                disabled={!isEdit}
              />
            ) : (
              <div className="text-text-color1">
                +86{" "}
                {drawConfig.type === "addMembers"
                  ? createdData.userPhone
                  : drawConfig.data?.userPhone}
              </div>
            )}
          </Form.Item>
          <Form.Item
            label={
              isEdit ? (
                "联系邮箱"
              ) : (
                <div className="text-text-color3">联系邮箱</div>
              )
            }
            name="userEmail"
            rules={
              isEdit
                ? [
                    { required: true, message: "请输入联系邮箱" },
                    { type: "email" }
                  ]
                : []
            }
          >
            {isEdit ? (
              <Input
                placeholder="请输入联系邮箱"
                className="w-full"
                variant={isEdit ? "outlined" : "borderless"}
                disabled={!isEdit}
              />
            ) : (
              <div className="text-text-color1">
                {drawConfig.type === "addMembers"
                  ? createdData.userEmail
                  : drawConfig.data?.userEmail}
              </div>
            )}
          </Form.Item>
          {drawConfig.type === "addMembers" && !isEdit && (
            <Form.Item
              label={
                isEdit ? "密码" : <div className="text-text-color3">密码</div>
              }
              name="userPassword"
              rules={
                isEdit
                  ? [
                      { required: true, message: "请输入密码" },
                      {
                        pattern: new RegExp(/^(?=.*[a-z])(?=.*[A-Z]).{8,}$/),
                        message: `密码至少包含一个大写字母、一个小写字母、8位字符`
                      }
                    ]
                  : []
              }
            >
              {isEdit ? (
                <Input
                  placeholder="请输入密码"
                  className="w-full"
                  variant={isEdit ? "outlined" : "borderless"}
                  disabled={!isEdit}
                />
              ) : (
                <>
                  <div className="text-[#EF4444] mb-[4px]">
                    请妥善保存您的密码，离开此页面后将无法找回。
                  </div>
                  <div className="flex mr-[8px] items-center">
                    <div className="text-text-color1 mr-[8px]">********</div>
                    <CopyOutlined onClick={handleCopy} />
                  </div>
                </>
              )}
            </Form.Item>
          )}
          <Form.Item
            label={
              isEdit ? "部门" : <div className="text-text-color3">部门</div>
            }
            name="deptId"
            rules={isEdit ? [{ required: true, message: "请输入部门" }] : []}
          >
            <TreeSelect
              style={{ width: "100%" }}
              dropdownStyle={{ maxHeight: 400, overflow: "auto" }}
              placeholder="请输入部门"
              treeData={deptTreeData}
              fieldNames={{ label: "name", value: "id" }}
              treeDefaultExpandAll
              disabled={!isEdit}
            />
          </Form.Item>
          <Form.Item
            label="角色"
            name="roleIds"
            rules={isEdit ? [{ required: true, message: "请输入角色" }] : []}
          >
            <Select
              mode="multiple"
              allowClear
              style={{ width: "100%" }}
              placeholder="请输入角色"
              options={roleList}
              disabled={!isEdit}
              fieldNames={{ label: "name", value: "id" }}
            />
          </Form.Item>
        </Form>
      </div>
      <div
        className="flex justify-end h-[38px] pt-[16px] mt-[10px]"
        style={{ borderTop: "1px solid #EBEBEB" }}
      >
        {!isEdit ? (
          <>
            {drawConfig.type === "addMembers" ? (
              <Button
                style={{
                  border: "1px solid #EBEBEB",
                  color: "#555555",
                  marginRight: "16px"
                }}
                onClick={() => {
                  handleEvent("closeDrawer");
                }}
              >
                返回
              </Button>
            ) : (
              <Button
                style={{
                  border: "none",
                  color: "#fff",
                  background:
                    "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
                }}
                onClick={() => setIsEdit(true)}
              >
                编辑成员
              </Button>
            )}
          </>
        ) : (
          <>
            <Button
              style={{
                border: "1px solid #EBEBEB",
                color: "#555555",
                marginRight: "16px"
              }}
              onClick={() => {
                drawConfig.type === "addMembers"
                  ? handleEvent("closeDrawer")
                  : setIsEdit(false);
              }}
            >
              取消
            </Button>
            <Button
              style={{
                border: "none",
                color: "#fff",
                background:
                  "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
              }}
              loading={btnLoading}
              onClick={() => {
                form.validateFields().then((values) => {
                  drawConfig.type === "addMembers"
                    ? handleEvent("save:addMembers", values, (data?: any) => {
                        if (data) {
                          setIsEdit(false);
                          setCreatedData(data);
                          form.setFieldsValue(data);
                        }
                      })
                    : handleEvent("save:viewMembers", values, () => {
                        setIsEdit(false);
                      });
                });
              }}
            >
              确认
            </Button>
          </>
        )}
      </div>
    </div>
  );
};
