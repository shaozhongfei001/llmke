import {
  Flex,
  Input,
  Table,
  DatePicker,
  Select,
  Button,
  Cascader,
  Modal,
  Form,
  message,
  Tooltip,
  Pagination,
  ConfigProvider,
  Drawer,
  Tag,
  Descriptions,
  Divider
} from "antd";
import "./styles.less";
import { useEffect, useState } from "react";
import axios$ from "@root/src/apis";
import {
  CaretDownOutlined,
  CaretRightOutlined,
  CaretUpOutlined,
  CloseOutlined,
  CopyOutlined,
  ExportOutlined,
  SearchOutlined
} from "@ant-design/icons";
import feedbackExport from "@root/src/assets/img/feedbackExport.png";
import { formatTime, getUrlPrefix, useAppPassport } from "@root/src/core/helps";
import { DrawerStyles } from "antd/es/drawer/DrawerPanel";
import TextArea from "antd/es/input/TextArea";
import { Divide } from "lucide-react";
import { modelRegex } from "@root/src/components/CommonEditor/constant";
const { RangePicker } = DatePicker;
const initialPage = {
  pageNo: 1,
  pageSize: 10
};
const FeedbackList = () => {
  const { getToken } = useAppPassport();
  const [recordList, setRecordList] = useState([]);
  const [recordTotal, setRecordTotal] = useState(0);
  const [fieldMapper, setFieldMapper] = useState([
    {
      que_name: "回答不佳",
      items: ["有事实性错误", "回答逻辑混乱", "内容不完整", "问题理解有误"]
    },
    {
      que_name: "格式问题",
      items: ["格式错误", "乱码错误", "内容重复"]
    },
    {
      que_name: "理解问题有误",
      items: ["敏感/有害回复", "存在价值观问题"]
    },
    {
      que_name: "其他",
      items: ["其他问题"]
    }
  ]);
  const [cascaderOptions, setCascaderOptions] = useState<any>([]);
  const [searchInput, setSearchInput] = useState("");
  const [dateRange, setDateRange] = useState(["", ""]);
  const [cascaderSelection, setCascaderSelections] = useState([]);
  const [showExportModal, setShowExportModal] = useState(false);
  const [openDrawer, setOpenDrawer] = useState(false);
  const [showAnswer, setShowAnswer] = useState(true);
  const [showOther, setShowOther] = useState(true);
  const [record, setRecord]: any = useState({});
  const modalStyles = {
    header: {
      padding: "20px 24px",
      borderBottom: "1px solid #F0F0F0",
      margin: 0
    },
    body: { padding: "16px 24px 20px 24px", borderBottom: "1px solid #F0F0F0" },
    mask: {},
    footer: { padding: "16px 24px", margin: 0 },
    content: { padding: 0, borderRadius: "4px", width: "563px" }
  };
  const drawerStyles: DrawerStyles = {
    mask: {
      backdropFilter: "blur(10px)"
    },
    content: {
      boxShadow: "-10px 0 10px #666"
    },
    header: { display: "none" },
    body: { padding: 0 },
    footer: {}
  };
  const getMappedValue = (str: string, type: string) => {
    if (!str) return "暂无";
    const fieldValues = str.split(";");
    // console.log("fieldValues", fieldValues);

    const aaa = fieldValues.map((item: string) => {
      // console.log("item", item);

      // handle history data
      if (item.startsWith("bad_performance-")) {
        const values = fieldMapper[0]?.items; // 回答不佳
        if (values) {
          const index = item.replace("bad_performance-", "");
          return `${values[parseInt(index) - 1]}`;
        }
        return item;
      } else if (item.startsWith("malform-")) {
        const values = fieldMapper[1]?.items; // 格式问题
        if (values) {
          const index = item.replace("malform-", "");
          return `${values[parseInt(index) - 1]}`;
        }
        return item;
      } else if (item.startsWith("harmful_response-")) {
        const values = fieldMapper[2]?.items; // 有害信息
        if (values) {
          const index = item.replace("harmful_response-", "");
          return `${values[parseInt(index) - 1]}`;
        }
        return item;
      } else if (item.startsWith("others-")) {
        const values = fieldMapper[3]?.items; // 其他
        if (values) {
          const index = item.replace("others-", "");
          return `${values[parseInt(index) - 1]}`;
        }
        return item;
      }

      // reformat output, add first level type str
      let result_str = "";
      switch (type) {
        case "misunderstand":
          result_str = item;
          break;
        case "bad_performance":
          result_str = `${fieldMapper[0].que_name}(${item})`;
          break;
        case "malformed":
          result_str = `${fieldMapper[1].que_name}(${item})`;
          break;
        case "harmful_response":
          result_str = `${fieldMapper[2].que_name}(${item})`;
          break;
        case "others":
          result_str = `${fieldMapper[3].que_name}(${item})`;
          break;
        default:
          result_str = item;
          break;
      }

      return result_str;
    });

    return aaa.join(";");
  };

  const [tableLoading, setTableLoading] = useState(false);
  const [page, setPage] = useState(initialPage);
  const fetchRecordList = (fuzzy?: any, keyList?: any, dataRange?: any) => {
    // get record list

    const params: any = {
      pageNo: page.pageNo || 1,
      pageSize: page.pageSize || 10
    };
    if (fuzzy || searchInput) {
      params["fuzzy"] = fuzzy ? fuzzy : searchInput;
    }
    if ((keyList && keyList.length > 0) || cascaderSelection.length > 0) {
      params["keyList"] =
        keyList && keyList.length > 0 ? keyList : cascaderSelection;
    }
    if (dateRange[0] != "") {
      params["startTime"] = dateRange[0];
      params["endTime"] = dateRange[1];
    }
    setTableLoading(true);
    axios$
      .post(`${getUrlPrefix()}/qa/feedback/list`, params)
      .then((result: any) => {
        // console.log("result", result);
        setRecordList(
          result.data.records.map((item: any, index: number) => {
            return {
              ...item,
              key: `${item.answerId}_${index}`,
              id: item.answerId,
              username: item.userName,
              question: item.qestion,
              answer: item.anwser,
              misunderstand: getMappedValue(item.queError, "misunderstand"), // deprecated
              bad_performance: getMappedValue(item.ansPoor, "bad_performance"),
              malformed: getMappedValue(item.formatError, "malformed"),
              harmful_response: getMappedValue(
                item.harmfulInfo,
                "harmful_response"
              ),
              others: getMappedValue(item.othres, "others"),
              supplementary: item.supplementExplain,
              expectation: item.idealAnswer,
              department: item.deptName,
              real_name: item.userRealname,
              contact: item.userPhone,
              feedbackTime: item.feedbackTime
            };
          })
        );

        setRecordTotal(result.data?.total || 0);
      })
      .finally(() => {
        setTableLoading(false);
      });
  };

  useEffect(() => {
    // get field map
    axios$.get(`${getUrlPrefix()}/qa/feedback/que/list`).then((result: any) => {
      // console.log('result1', result)
      setFieldMapper(result.data);
    });
  }, []);

  useEffect(() => {
    // console.log('fieldMapper', fieldMapper)
    // get value map first
    if (fieldMapper && fieldMapper.length > 0) {
      setCascaderOptions(
        fieldMapper.map((item: any) => {
          return {
            value: item.que_name,
            label: item.que_name,
            children: item.items.map((i: any) => {
              return {
                value: i,
                label: i
              };
            })
          };
        })
      );
    }
  }, [fieldMapper]);

  const renderTitle = (text: string) => {
    return (
      <span
        style={{
          maxHeight: "500px",
          maxWidth: "70vw",
          overflow: "auto",
          textOverflow: "ellipsis",
          whiteSpace: "pre-wrap",
          display: "block",
          width: "100%",
          color: "#333",
          padding: 5
        }}
      >
        {text}
      </span>
    );
  };
  const [showContentCopy, setShowContentCopy] = useState({
    type: -1,
    index: -1
  });
  const columns = [
    {
      title: "序号",
      render: (_: any, data: any, index: any) => {
        // console.log('test', _, data, index)
        return <label>{index + 1}</label>;
      },
      width: 80
    },

    {
      title: "用户问题",
      dataIndex: "question",
      key: "question",
      ellipsis: true,
      render: (text: string, item: any) => {
        return (
          <Tooltip color="#fff" title={renderTitle(text)}>
            <label
              style={{
                overflow: "hidden",
                whiteSpace: "nowrap",
                textOverflow: "ellipsis"
              }}
            >
              {text}
            </label>
          </Tooltip>
        );
      }
    },
    {
      title: "联系电话",
      dataIndex: "userPhone",
      key: "userPhone",
      width: 200
    },
    {
      title: "部门",
      dataIndex: "deptName",
      key: "deptName",
      width: 200
    },
    {
      title: "反馈时间",
      dataIndex: "feedbackTime",
      key: "feedbackTime",
      width: 200,
      render: (val: string) => {
        return <>{formatTime(val)}</>;
      }
    }
  ];

  const handleFilterSelect = (event: any) => {
    // console.log('event', event)
    const mapper = [
      {
        key: "que_error",
        value: "理解问题有误"
      },
      {
        key: "ans_poor",
        value: "回答不佳"
      },
      {
        key: "format_error",
        value: "格式问题"
      },
      {
        key: "harmful_info",
        value: "有害信息"
      },
      {
        key: "othres",
        value: "其他"
      }
    ];

    if (event && event[0]) {
      const result = event.map((item: any) => {
        // console.log('item', item)
        const selectAll = fieldMapper.find(
          (j: any) => j.que_name == item[0]
        ) || { items: [] };

        return {
          column: mapper.find((i: any) => i.value == item[0])?.key || "",
          columnValue: item[1] || selectAll.items.join(";")
        };
      });

      // console.log('result', result, fieldMapper);
      const final_result: any = [];
      result.forEach((j: any) => {
        if (final_result.every((value: any) => value.column != j.column)) {
          final_result.push(j);
        } else {
          const match_one = final_result.find(
            (value: any) => value.column == j.column
          );
          match_one.columnValue = match_one.columnValue + ";" + j.columnValue;
        }
      });

      console.log("final_result", final_result);
      setCascaderSelections(final_result);
    } else {
      setCascaderSelections([]);
    }
  };

  const handleDatePicker = (event: any, b: any) => {
    setDateRange(b);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      setPage((pre) => {
        return { ...pre, pageNo: 1 };
      });
    }
  };

  const handleExportCSV = async () => {
    const params: any = {
      pageNo: 1,
      pageSize: 9999
    };
    if (cascaderSelection.length > 0) {
      params["keyList"] = cascaderSelection;
    }
    if (dateRange[0] != "") {
      params["startTime"] = dateRange[0];
      params["endTime"] = dateRange[1];
    }

    fetch(`${getUrlPrefix()}/qa/feedback/exportCsv`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: getToken() || ""
      },
      body: JSON.stringify(params)
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
        a.download = `点踩反馈问题收集_${new Date().getTime()}.xlsx`;
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

    resetExportModal();
  };

  const resetExportModal = () => {
    setShowExportModal(false);
    // reset all params
    setCascaderSelections([]);
    setDateRange(["", ""]);
  };

  const assembleProblemStr = (record: any) => {
    let resultStr = "";

    if (record.misunderstand && record.misunderstand != "暂无") {
      resultStr += `${record.misunderstand};`;
    }
    if (record.bad_performance && record.bad_performance != "暂无") {
      resultStr += `${record.bad_performance};`;
    }
    if (record.malformed && record.malformed != "暂无") {
      resultStr += `${record.malformed};`;
    }
    if (record.harmful_response && record.harmful_response != "暂无") {
      resultStr += `${record.harmful_response};`;
    }
    if (record.others && record.others != "暂无") {
      resultStr += `${record.others};`;
    }

    return resultStr?.split(";")?.filter((item: string) => item != "") || [];
  };

  const handleCopy = (text: string) => {
    const textField = document.createElement("textarea");
    textField.innerText = text;
    document.body.appendChild(textField);
    textField.select();
    document.execCommand("copy");
    textField.remove();
    message.success("复制成功");
  };

  const onPageSizeChange = (pageNo: number, pageSize: number) => {
    setPage({
      pageNo,
      pageSize
    });
  };
  useEffect(() => {
    setPage((pre) => {
      return { ...pre, pageNo: 1 };
    });
  }, [dateRange, cascaderSelection]);
  useEffect(() => {
    fetchRecordList();
  }, [page]);
  return (
    <>
      <div className="flex items-center justify-between pb-[20px]">
        <div className="flex items-center">
          <div className="text-[16px] text-text-color1 font-bold">用户反馈</div>
        </div>
      </div>
      <div className="px-[20px] pt-[20px] h-[calc(100%-76px)] overflow-auto bg-white rounded-[8px]">
        <Flex justify="space-between">
          <div
            style={{
              fontFamily: "Microsoft YaHei",
              fontSize: "16px",
              fontWeight: 700,
              color: "#2a2a2a"
            }}
          >
            点踩反馈问题收集
          </div>
          <Flex gap={16}>
            <Cascader
              multiple
              options={cascaderOptions}
              onChange={handleFilterSelect}
              placeholder="问题类型"
              style={{ width: "250px" }}
              maxTagCount={1}
            />
            <RangePicker
              style={{ width: "250px" }}
              onChange={handleDatePicker}
            />
            <Input
              placeholder="请输入内容"
              suffix={
                <SearchOutlined
                  onClick={() => {
                    setPage((pre) => {
                      return { ...pre, pageNo: 1 };
                    });
                  }}
                />
              }
              style={{ width: "150px" }}
              value={searchInput}
              onChange={(e) => setSearchInput(e?.target?.value || "")}
              onPressEnter={handleKeyDown}
            />
            <Button
              type="default"
              className="text-text-color1"
              icon={<img src={feedbackExport} />}
              iconPosition="start"
              onClick={() => setShowExportModal(true)}
            >
              导出
            </Button>
          </Flex>
        </Flex>
        <div
          style={{ height: "calc(100% - 117px)" }}
          className="mt-[20px] overflow-y-auto rowHoverTable nlp-setting-list-table"
        >
          <Table
            dataSource={recordList}
            columns={columns}
            pagination={false}
            onRow={(record) => {
              return {
                onClick: (event) => {
                  console.log("record", record);
                  setRecord(record);
                  setOpenDrawer(true);
                } // 点击行
              };
            }}
          ></Table>
        </div>
        <div className="h-[64px] flex justify-end items-center">
          {/* <div className="statistics-wrap">
          <InfoCircleFilled style={{ color: "#014DDF", marginRight: "4px" }} />
          共<label>{listCount}</label>条记录
        </div> */}
          <Pagination
            disabled={tableLoading}
            total={recordTotal}
            pageSize={page.pageSize}
            current={page.pageNo}
            showSizeChanger={false}
            // showQuickJumper
            onChange={onPageSizeChange}
          ></Pagination>
        </div>
        <ConfigProvider
          modal={{
            styles: modalStyles
          }}
        >
          <Modal
            title="导出"
            open={showExportModal}
            onCancel={() => resetExportModal()}
            footer={
              <div className="flex justify-end">
                <Button
                  className="mr-[16px] w-[76px] border-[#EBEBEB]"
                  onClick={resetExportModal}
                >
                  取消
                </Button>
                <Button
                  type="primary"
                  className="w-[76px] border-none bg-[linear-gradient(90deg,#0359FF,#BD9CFF)]"
                  onClick={handleExportCSV}
                >
                  确认
                </Button>
              </div>
            }
          >
            <Form layout="vertical">
              <Form.Item label="时间" labelCol={{ span: 4 }}>
                <RangePicker
                  style={{ width: "100%" }}
                  onChange={handleDatePicker}
                />
              </Form.Item>
              <Form.Item label="问题类型" labelCol={{ span: 4 }}>
                <Cascader
                  multiple
                  options={cascaderOptions}
                  onChange={handleFilterSelect}
                  placeholder="请选择"
                  maxTagCount={3}
                />
              </Form.Item>
            </Form>
          </Modal>
        </ConfigProvider>
        <Drawer
          closable
          destroyOnClose
          placement="right"
          open={openDrawer}
          width={840}
          styles={drawerStyles}
          onClose={() => setOpenDrawer(false)}
          forceRender
          getContainer={false}
          mask={false}
          afterOpenChange={(open) => {
            if (!open) {
              return;
            }
          }}
        >
          <div className="flex flex-col h-full">
            <div
              className="feed_drawer_header px-[20px] py-[16px] font-bold text-text-color1 text-[16px] flex justify-between"
              style={{ borderBottom: "1px solid #EEEEEE" }}
            >
              <div>用户反馈问题详细信息</div>
              <CloseOutlined onClick={() => setOpenDrawer(false)} />
            </div>
            <div className="feed_drawer_content px-[20px] py-[20px]">
              <div className="question text-[16px] font-bold text-text-color1">
                {record.question}
              </div>
              <div className="mt-[12px]">
                {assembleProblemStr(record).map((item: any) => {
                  return (
                    <Tag
                      bordered={false}
                      color="processing"
                      className="mr-[4px] mt-[4px]"
                    >
                      {item}
                    </Tag>
                  );
                })}
              </div>
              <div
                className="flex mt-[20px] justify-between mb-[12px] items-center cursor-pointer"
                onClick={() => setShowAnswer((pre) => !pre)}
              >
                <div className="question text-[16px] font-bold text-text-color1">
                  大模型回答
                </div>
                {showAnswer ? <CaretDownOutlined /> : <CaretUpOutlined />}
              </div>
              {showAnswer && (
                <TextArea
                  style={{
                    height: 114,
                    resize: "none"
                  }}
                  value={
                    record.answer
                      ? record.answer.replaceAll(modelRegex, "")
                      : ""
                  }
                  readOnly
                />
              )}
              <div
                className="flex mt-[20px] justify-between mb-[12px] items-center cursor-pointer"
                onClick={() => setShowOther((pre) => !pre)}
              >
                <div className="question text-[16px] font-bold text-text-color1">
                  其他信息
                </div>
                {showOther ? <CaretDownOutlined /> : <CaretUpOutlined />}
              </div>
              {showOther && (
                <Descriptions
                  bordered
                  contentStyle={{
                    width: 690
                  }}
                  className="mt-[12px] rounded-none"
                  size="small"
                  items={[
                    {
                      key: "idealAnswer",
                      label: "理想回答",
                      children: record.idealAnswer || ""
                    },
                    {
                      key: "supplementExplain",
                      label: "补充说明",
                      children: record.supplementExplain || ""
                    },
                    {
                      key: "configName",
                      label: "助手名称",
                      children: record.configName || ""
                    },
                    {
                      key: "userName",
                      label: "用户名称",
                      children: record.userName || ""
                    },
                    {
                      key: "department",
                      label: "所在部门",
                      children: record.department || ""
                    },
                    {
                      key: "userPhone",
                      label: "联系方式",
                      children: record.userPhone || ""
                    }
                  ]}
                  column={1}
                />
              )}
              <div className="mt-[20px] question text-[16px] font-bold text-text-color1">
                上文信息
              </div>
              <div className="mt-[12px]">
                {(record.historyDTOList || []).map(
                  (item: any, index: number) => {
                    return (
                      <div
                        key={index}
                        className="rounded-[4px] bg-[#FAFAFA] border-[1px] border-solid border-[#EEEEEE] px-[20px] py-[20px] mb-[12px]"
                      >
                        <div className="flex">
                          <div className="text-[16px] text-primary-color font-bold h-full mr-[8px]">
                            Q:
                          </div>
                          <div className="text-[16px] text-text-color1 font-bold">
                            {item.queryContent}
                          </div>
                        </div>
                        <Divider className="border-[#E8E8E8] my-[16px]" />
                        <div className="flex">
                          <div className="text-[16px] text-text-color1 font-bold h-full mr-[8px]">
                            A:
                          </div>
                          <div className="text-[14px] text-text-color1 leading-[22px]">
                            {item.answerContent}
                          </div>
                        </div>
                      </div>
                    );
                  }
                )}
              </div>
            </div>
          </div>
        </Drawer>
      </div>
    </>
  );
};

export default FeedbackList;
