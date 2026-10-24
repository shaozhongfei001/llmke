import { ChangeEventHandler, useEffect, useMemo, useState } from "react";
import axios$ from "@/apis";
import {
  Button,
  ConfigProvider,
  Drawer,
  Flex,
  Input,
  Modal,
  Pagination,
  Table,
  Tabs,
  Tag,
  Tooltip,
  message
} from "antd";
import {
  CloseOutlined,
  PlusCircleOutlined,
  SearchOutlined
} from "@ant-design/icons";
import "./style.less";
import { useNavigate } from "react-router-dom";
import ISettingDetail from "./SettingDetail";
import PermisssonConfig, {
  TypeDrawConfig
} from "@/pages/Components/PermissionConfig";
import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";
import { getUrlPrefix } from "@root/src/core/helps";
import { PublishPannel } from "./PublishPannel";
import { useSelector } from "react-redux";

const SettingPage = () => {
  const [configCount, setConfigCount] = useState(0);
  const [configShareCount, setConfigShareCount] = useState(0);
  // const [modelList, setModelList] = useState([]);
  const [configData, setConfigData] = useState([]);
  const [configShareData, setConfigShareData] = useState([]);
  const [fuzzy, setFuzzy] = useState([]);
  const navigator = useNavigate();
  const [curMenuKey, setCurMenuKey] = useState("1");
  useEffect(() => {
    fetchConfigShareList();
    fetchConfigList();
    //fetchModelList();
  }, []);

  const fetchConfigList = (page?: any, pageSize?: any) => {
    axios$
      .get(
        `${getUrlPrefix()}/qa/search/config/searchList?pageNo=${
          page || 1
        }&pageSize=${pageSize || 10}&fuzzy=${fuzzy}`
      )
      .then((res: any) => {
        setConfigCount(res.data.total);
        setConfigData(res.data.records);
      });
  };

  const fetchConfigShareList = (page?: any, pageSize?: any) => {
    axios$
      .get(
        `${getUrlPrefix()}/qa/search/config/share/list?pageNo=${
          page || 1
        }&pageSize=${pageSize || 10}&fuzzy=${fuzzy}`
      )
      .then((res: any) => {
        setConfigShareCount(res.data.total);
        setConfigShareData(res.data.records);
      });
  };

  const handleColumnToUpdate = (record: any) => {
    navigator(`config/${record.key}`);
  };

  const handleTriggerCreate = () => {
    navigator("config");
  };

  const handleDeleteConfig = (payload: any) => {
    if (payload.key) {
      axios$
        .delete(
          `${getUrlPrefix()}/qa/search/config/deleteById?configId=${
            payload.key
          }`
        )
        .then((res: any) => {
          curMenuKey === "1" ? fetchConfigList() : fetchConfigShareList();
          payload._fn();
          message.success("配置删除成功", 2);
        })
        .catch((e) => {
          console.log("Error when deleting record", e);
          payload._fn();
        });
    }
  };

  const handlePageChange = (page: any, pageSize: any) => {
    curMenuKey === "1"
      ? fetchConfigList(page, pageSize)
      : fetchConfigShareList(page, pageSize);
  };

  const OVERLAP_DEEAULT_STYLE = {
    setting: {
      container: "hidden"
    }
  };

  return (
    <div style={{ height: "100%" }}>
      <DetailWrapper
        data={configData}
        shareData={configShareData}
        count={configCount}
        shareCount={configShareCount}
        onDelete={handleDeleteConfig}
        onTriggerCreate={handleTriggerCreate}
        onToUpdate={handleColumnToUpdate}
        onPageChange={handlePageChange}
        fetchConfigList={fetchConfigList}
        fetchConfigShareList={fetchConfigShareList}
        setFuzzy={setFuzzy}
        curMenuKey={curMenuKey}
        setCurMenuKey={setCurMenuKey}
      ></DetailWrapper>
    </div>
  );
};

const DetailWrapper = (props: any) => {
  const {
    fetchConfigList,
    setFuzzy,
    data,
    curMenuKey,
    setCurMenuKey,
    shareData,
    configShareCount,
    fetchConfigShareList
  } = props;
  const [openDraw, setOpenDraw] = useState(false);
  const [drawConfig, setDrawConfig] = useState<TypeDrawConfig>({
    type: "create"
  });
  const navigator = useNavigate();
  const [curColumnData, setCurColData] = useState<any>({});
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const globalMenu: any = useSelector((state: any) => state.global.globalMenu);

  const getPermission = (p: number) => {
    return p === 2 || p === 3;
  };

  const databasePermission = useMemo(() => {
    if (!globalMenu) return;
    //这里目前只处理写作模版的权限
    const docMenu = globalMenu.find((i: any) => i.url === "/chats/database");
    if (!docMenu) return false;
    return docMenu.permission;
  }, [globalMenu]);

  const dealData = (data: any) => {
    return data.map((item: any, index: any) => {
      let configJson: any = {};
      try {
        configJson = JSON.parse(item.configJson);
      } catch (e) {
        console.log("config list json format error:", e);
      }
      // const model_mask_name =
      //   props.models.find((item: any) => item.value == configJson.model_name)
      //     ?.label || configJson?.model_name;
      const { enabledFaq, enabled_faq, rerank } = configJson;
      const _enabled_faq =
        enabled_faq !== undefined ? !!enabled_faq : !!enabledFaq;
      const _rerank = !!rerank;
      return {
        ...item,
        ...configJson,
        id: item.id,
        rerank: _rerank,
        enabled_faq: _enabled_faq,
        key: item.id,
        config_name: item.name,
        description: item.des,
        model_name: configJson.model_name,
        temperature: configJson.temperature,
        max_tokens: configJson.max_tokens,
        knowledge_base_name: configJson.knowledge_base_name,
        knowledge_base_name_source: configJson.knowledge_base_name_source,
        top_k: configJson.top_k,
        score_threshold: configJson.score_threshold,
        sensitiveWordIds: item.sensitiveWordIds,
        defaultAnswer: item.defaultAnswer,
        enabledFaq: item.enabledFaq,
        isDefault: item.isDefault,
        permission: item.permission
      };
    });
  };

  const columns = [
    {
      title: "助手名称",
      dataIndex: "config_name",
      key: "config_name",
      render: (_: any, record: any) => {
        return curMenuKey === "1" ? (
          _
        ) : (
          <Button
            type="link"
            size="small"
            onClick={() => {
              // setDrawConfig({
              //   type: "view",
              //   data: record
              // });
              // setOpenDraw(true);
              navigator(`config/view/${record.id}`);
            }}
          >
            {_}
          </Button>
        );
      }
    },
    {
      title: "模型名称",
      dataIndex: "model_name",
      key: "model_name",
      editable: true
    },
    {
      title: () => {
        return (
          <>
            温度
            {/* <Tooltip title={EXPLANATION_TEMPERATURE}>
              <QuestionCircleOutlined
                style={{ color: "#1d71f5", marginLeft: "5px" }}
              />
            </Tooltip> */}
          </>
        );
      },
      dataIndex: "temperature",
      key: "temperature",
      editable: true
    },
    {
      title: () => {
        return (
          <>
            多样性
            {/* <Tooltip title={EXPLANATION_TOP_P}>
              <QuestionCircleOutlined
                style={{ color: "#1d71f5", marginLeft: "5px" }}
              />
            </Tooltip> */}
          </>
        );
      },
      dataIndex: "top_p",
      key: "top_p",
      editable: true
    },
    {
      title: () => {
        return (
          <>
            最大令牌数
            {/* <Tooltip title={EXPLANATION_MAXTOKENS}>
              <QuestionCircleOutlined
                style={{ color: "#1d71f5", marginLeft: "5px" }}
              />
            </Tooltip> */}
          </>
        );
      },
      dataIndex: "max_tokens",
      key: "max_tokens"
    },
    // {
    //     title: "最大可信文本块(top_k)",
    //     dataIndex: "top_k",
    //     key: "top_k",
    //     width: "7%",
    // },
    {
      title: () => {
        return (
          <>
            知识库名称
            {/* <Tooltip title={EXPLANATION_KB_NAME}>
              <QuestionCircleOutlined
                style={{ color: "#1d71f5", marginLeft: "5px" }}
              />
            </Tooltip> */}
          </>
        );
      },
      dataIndex: "knowledge_base_name_source",
      key: "knowledge_base_name_source",
      editable: true,
      render: (_: any, data: any) => {
        let original_kb_list = [];
        const _str =
          data.knowledge_base_name_source || data.knowledge_base_name;
        if (_str) {
          if (typeof _str === "string") {
            original_kb_list = _str.split(";").filter((item: string) => item);
          } else {
            original_kb_list = _str.filter((item: string) => item);
          }
        }

        let kb_list = original_kb_list;
        if (kb_list && kb_list.length > 3) {
          kb_list = kb_list.slice(0, 3);
          kb_list.push("...");
        }
        const react_nodes = () => {
          return (
            <Flex
              style={{ maxWidth: "500px", flexWrap: "wrap", color: "#000" }}
            >
              {original_kb_list.map((item: any, index: any) => {
                return (
                  item && (
                    <span
                      key={index}
                      title={item}
                      className="my-[4px] mx-[4px]"
                    >
                      {item}
                    </span>
                  )
                );
              })}
            </Flex>
          );
        };
        if (typeof data.knowledge_base_name_source == "string" && kb_list) {
          return (
            <Flex
              style={{
                maxWidth: "500px",
                overflow: "hidden",
                flexWrap: "wrap"
              }}
            >
              {kb_list.map((item: any, index: any) => {
                if (item == "...") {
                  return (
                    <Tooltip title={react_nodes} color="#fff" key={index}>
                      <span title={item} key={index} className="mx-[4px]">
                        {item}
                      </span>
                    </Tooltip>
                  );
                }
                return item ? (
                  <span key={index} title={item} className="mx-[4px]">
                    {item}
                  </span>
                ) : (
                  <label
                    key={index}
                    style={{ fontSize: "12px" }}
                    className="mx-[4px]"
                  >
                    无知识库
                  </label>
                );
              })}
            </Flex>
          );
        } else {
          return <Tag>{JSON.stringify(data.knowledge_base_name_source)}</Tag>;
        }
      }
    },
    ...(databasePermission
      ? [
          {
            title: () => {
              return <>数据库名称</>;
            },
            dataIndex: "database_name",
            key: "database_name",
            editable: true,
            render: (a: any, data: any) => {
              if (!Array.isArray(a)) return "";
              const _ = (a || []).map((item: any) => {
                return item.label;
              });

              if (_?.length) {
                if (_.length > 3) {
                  return (
                    <>
                      {_.slice(0, 3).join(" ")}
                      <Tooltip
                        title={
                          <div>
                            {_.map((item: any) => {
                              return <div className="text-[#222]">{item}</div>;
                            })}
                          </div>
                        }
                        color="#fff"
                      >
                        ...
                      </Tooltip>
                    </>
                  );
                } else {
                  return _.join(" ");
                }
              } else {
                return "";
              }
            }
          }
        ]
      : []),
    {
      title: "操作",
      dataIndex: "operation",
      render: (_: any, record: any) => (
        <div className="table-btn-group-wrap">
          <Button
            type="link"
            size={"small"}
            onClick={() => {
              setDrawConfig({
                type: "publish",
                data: record
              });
              setOpenDraw(true);
            }}
            disabled={getBtnDisabled(FILE_BTN.DELETE, record.permission)}
          >
            发布
          </Button>
          <Button
            type="link"
            size={"small"}
            onClick={() => {
              setDrawConfig({
                type: "permission",
                data: record
              });
              setOpenDraw(true);
            }}
            disabled={getBtnDisabled(FILE_BTN.AUTHORIZE, record.permission)}
          >
            授权
          </Button>
          <Button
            type="link"
            size={"small"}
            onClick={() => {
              // setDrawConfig({
              //   type: "edit",
              //   data: record
              // });
              // setOpenDraw(true);
              if (curMenuKey == 2) {
                navigator(`config/share/${record.id}`);
              } else {
                navigator(`config/${record.id}`);
              }
            }}
            disabled={getBtnDisabled(FILE_BTN.EDIT, record.permission)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size={"small"}
            onClick={() => handleConfirmColumnDelete(record)}
            disabled={getBtnDisabled(FILE_BTN.DELETE, record.permission)}
          >
            删除
          </Button>
          {/* <div
        className="setting-column-operations-rename-btn"
        onClick={() => handleConfig(record)}
      >
        配置权限
      </div> */}
        </div>
      ),
      width: 150
    }
  ];

  const EditableCell: React.FC<React.PropsWithChildren<any>> = ({
    editing,
    dataIndex,
    title,
    inputType,
    record,
    index,
    children,

    ...restProps
  }) => {
    let displayNode = <>{children}</>;
    if ("config_name" == dataIndex) {
      displayNode = (
        <>
          <a
            onClick={(event: any) => {
              props.onToUpdate && props.onToUpdate(record);
            }}
          >
            {record.config_name}
          </a>
        </>
      );
    }

    return <td {...restProps}>{displayNode}</td>;
  };

  const mergedColumns: any = columns.map((col) => {
    if (!col.editable) {
      return col;
    }
    return {
      ...col,
      onCell: (record: any) => ({
        record,
        key: col.dataIndex,
        dataIndex: col.dataIndex,
        title: col.title
      })
    };
  });

  const handleConfirmColumnDelete = (record: any) => {
    setCurColData(record);
  };

  useEffect(() => {
    if (curColumnData.key) {
      console.log("curColumnData", curColumnData);
      setShowDeleteModal(true);
    }
  }, [curColumnData]);

  const handleColumnDelete = () => {
    props.onDelete &&
      props.onDelete({
        key: curColumnData.key,
        _fn: () => {
          setShowDeleteModal(false);
        }
      });
  };

  const onTriggerCreate = () => {
    // setDrawConfig({
    //   type: "create"
    // });
    // setOpenDraw(true);
    navigator("/chats/setting/config");
  };

  const onTriggerPageChange = (page: any, pageSize: any) => {
    props.onPageChange && props.onPageChange(page, pageSize);
  };

  const fuzzyNameOrIdOnChange: ChangeEventHandler<HTMLInputElement> = (e) => {
    const inputElement = e.target as HTMLInputElement;
    setFuzzy(inputElement.value.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      curMenuKey === "1" ? fetchConfigList() : fetchConfigShareList();
    }
  };

  return (
    <>
      <div className="huihuaAssistant h-full">
        <div className="flex items-center justify-between pb-[20px]">
          <div className="flex items-center">
            <div className="text-[16px] text-text-color1 font-bold">
              会话助手配置
            </div>
          </div>
        </div>
        <div className="h-[calc(100%-76px)] bg-white rounded-[8px]">
          <Tabs
            items={[
              { label: "我创建的", key: "1" },
              { label: "共享", key: "2" }
            ]}
            activeKey={curMenuKey}
            onChange={(key) => {
              setCurMenuKey(key);
            }}
          />
          <div className="flex justify-between mt-[16px]  px-[20px]">
            {curMenuKey === "1" ? (
              <Button
                type="primary"
                icon={<PlusCircleOutlined />}
                className="w-[83px] border-none"
                style={{ background: "linear-gradient(90deg,#075BFF,#AC96FF)" }}
                onClick={onTriggerCreate}
              >
                新建
              </Button>
            ) : (
              <div></div>
            )}
            <Input
              style={{ width: "240px" }}
              placeholder="请输入内容"
              suffix={
                <SearchOutlined
                  style={{ color: "#999", fontSize: 12 }}
                  onClick={() => {
                    curMenuKey === "1"
                      ? fetchConfigList()
                      : fetchConfigShareList();
                  }}
                />
              }
              onChange={fuzzyNameOrIdOnChange}
              onKeyDown={handleKeyDown}
            />
          </div>
          <div className="h-[calc(100%-183px)] mt-[16px] overflow-auto  px-[20px] nlp-setting-list-table">
            {curMenuKey === "1" ? (
              <Table
                dataSource={dealData(props.data)}
                columns={mergedColumns}
                components={{
                  body: {
                    cell: EditableCell
                  }
                }}
                pagination={false}
              ></Table>
            ) : (
              <Table
                dataSource={dealData(shareData)}
                columns={mergedColumns}
                components={{
                  body: {
                    cell: EditableCell
                  }
                }}
                pagination={false}
              ></Table>
            )}
          </div>
          <div className="flex justify-end w-full h-[64px] items-center  px-[20px]">
            {curMenuKey === "1" ? (
              <Pagination
                defaultCurrent={1}
                total={props.count}
                onChange={onTriggerPageChange}
                showSizeChanger={false}
              ></Pagination>
            ) : (
              <Pagination
                defaultCurrent={1}
                total={configShareCount}
                onChange={onTriggerPageChange}
                showSizeChanger={false}
              ></Pagination>
            )}
          </div>
        </div>
      </div>
      <Modal
        className="delete-modal"
        open={showDeleteModal}
        closable={false}
        title="确认删除这个助手？"
        onOk={handleColumnDelete}
        onCancel={() => {
          setCurColData({});
          setShowDeleteModal(false);
        }}
      ></Modal>
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
              <div className="text-[16px] font-bold">{`${
                drawConfig.type === "permission"
                  ? "权限配置"
                  : drawConfig.type === "create"
                  ? "新建会话助手"
                  : drawConfig.type === "view"
                  ? "会话助手详情"
                  : drawConfig.type === "publish"
                  ? "发布助手"
                  : "编辑会话助手"
              }`}</div>
              <CloseOutlined
                className="cursor-pointer"
                onClick={() => setOpenDraw(false)}
              />
            </div>
          }
          width={
            drawConfig.type === "permission"
              ? 557
              : drawConfig.type === "publish"
              ? 850
              : 784
          }
          onClose={() => setOpenDraw(false)}
          open={openDraw}
          closable={false}
          destroyOnClose
        >
          {drawConfig.type === "permission" ? (
            <div className="h-[calc(100vh-100px)] relative px-[20px] pt-[10px] pb-[20px]">
              <PermisssonConfig
                drawConfig={drawConfig}
                subTitle="助手公开范围"
                bizType={2}
                type="assistantRight"
              />
            </div>
          ) : drawConfig.type === "publish" ? (
            <PublishPannel drawConfig={drawConfig} />
          ) : (
            <ISettingDetail
              drawConfig={drawConfig}
              setOpenDraw={setOpenDraw}
              fetchConfigList={fetchConfigList}
              fetchConfigShareList={fetchConfigShareList}
              configData={data}
              openDraw={openDraw}
              curMenuKey={curMenuKey}
            />
          )}
        </Drawer>
      </ConfigProvider>
    </>
  );
};

export default SettingPage;
