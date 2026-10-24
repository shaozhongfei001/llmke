import React, { useState, useMemo, useEffect, useCallback } from "react";
import { Button, Tooltip, Empty, Input } from "antd";
import { CloseOutlined, CheckOutlined } from "@ant-design/icons";
import { FilePdfIcon, FxIcon } from "@/components/Icon";

export enum InfoConfirmTypes {
  // 关闭
  CLOSE = "close",
  // 多值冲突
  MULTI_VALUED_CONFLICT = "multiValuedConflict",
  // 多选溯源
  CHOOSE_SOURCE_FILE = "chooseSourceFile",
  // 展示文件
  SHOW_SOURCE_FILE = "showSourceFile"
}

interface InfoDetailProps {
  item: any;
  confirmInfoByType: (type: InfoConfirmTypes, row: any, data: any) => void;
  isLoading: boolean;
}

// mock begin
const isMock = false;
const isRandom = false;
const randomNum = 3;

const getRandomInt = (min: number, max: number) => {
  min = Math.ceil(min);
  max = Math.floor(max);
  return Math.floor(Math.random() * (max - min + 1)) + min;
};

const titleKey = "title";
const cases = [
  {
    [titleKey]: "",
    value: "2,821,543,685.04", //页面展示的值
    state: 1, //状态，标记颜色！
    errorMsg: "",
    source: [
      {
        tableName: "consolidated_balance",
        id: 11,
        name: "货币资金",
        value: "2,821,543,685.04",
        match: [
          {
            fileId: 12,
            fileName: "xxxxx年报",
            fileUrl: "http://10.15.12.13:9009/xxxxx年报.pdf",
            pageId: 5,
            position: "[417, 729, 534, 729, 534, 762, 417, 762]"
          }
        ]
      },
      {
        tableName: "consolidated_balance1",
        id: 111,
        name: "货币资金1",
        value: "2,121,543,685.04",
        match: [
          {
            fileId: 11,
            fileName: "xxxxx年报111",
            fileUrl: "http://10.15.12.13:9009/xx1111xxx年报.pdf",
            pageId: 5,
            position: "[417, 729, 534, 729, 534, 762, 417, 762]"
          }
        ]
      }
    ]
  },
  {
    [titleKey]: "货币资金",
    value: "2,821,543,685.04",
    state: 2,
    errorMsg: "无溯源",
    source: [
      {
        tableName: "consolidated_balance",
        id: 11,
        name: "货币资金",
        value: "2,821,543,685.04",
        match: [
          {
            fileId: 12,
            fileName: "xxxxx年报",
            fileUrl: "http://10.15.12.13:9009/xxxxx年报.pdf",
            pageId: 5,
            position: "[417, 729, 534, 729, 534, 762, 417, 762]"
          }
        ]
      },
      {
        tableName: "consolidated_balance2",
        id: 112,
        name: "货币资金2",
        value: "22,821,543,685.04",
        match: [
          {
            fileId: 11,
            fileName: "xxxxx年报111",
            fileUrl: "http://10.15.12.13:9009/xx1111xxx年报.pdf",
            pageId: 5,
            position: "[417, 729, 534, 729, 534, 762, 417, 762]"
          }
        ]
      }
    ]
  },
  {
    [titleKey]: "应收票据期初值",
    value: "2,821,543,685.04",
    state: 4,
    errorMsg: "检测到多个来源值，且值不一样",
    source: [
      {
        tableName: "consolidated_balance3",
        id: 113,
        name: "货币资金3",
        value: "433,685.04",
        match: [
          {
            fileId: 123,
            fileName: "xxxxx年报3",
            fileUrl: "http://10.15.12.13:9009/xxxxx年3报.pdf",
            pageId: 5,
            position: "[417, 729, 534, 729, 534, 762, 417, 762]"
          }
        ]
      },
      {
        tableName: "consolidated_balance33",
        id: 1233,
        name: "货币资金33",
        value: "33,685.04",
        match: [
          {
            fileId: 1233,
            fileName: "xxxxx年报33",
            fileUrl: "http://10.15.12.13:9009/xxxxx年33报.pdf",
            pageId: 53,
            position: "[417, 729, 534, 729, 534, 762, 417, 762]"
          }
        ]
      }
    ]
  },
  {
    [titleKey]: "资产总计期末值",
    value: "2,821,543,685.04",
    state: 5,
    errorMsg: "勾稽校验失败4",
    // source: [
    //   {
    //     tableName: "consolidated_balance4",
    //     id: 114,
    //     name: "000总资产4",
    //     value: "2,821,543,685.04",
    //     match: [
    //       {
    //         fileId: 12,
    //         fileName: "000xxxxx年报44",
    //         fileUrl: "http://10.15.12.13:9009/xxxxx年报44.pdf",
    //         pageId: 5,
    //         position: "[417, 729, 534, 729, 534, 762, 417, 762]"
    //       }
    //     ]
    //   }
    // ],
    // diff: "000总资产-(流动资产+非流动资产) = 0.15亿",
    // calculators: ["$2002-eop-N5/[（$2007-bop-N5 + $2007-eop-N5）/2]"],
    // formulas: ["000近5年期末2002/[(近5年期末)]"],
    refers: [
      {
        diff: "1差异：总资产-（流动资产+非流动资产）= 0.15亿",
        tableName: "consolidated_balance44",
        id: 1244,
        indicatorId: 204,
        name: "111流动资产44",
        value: "44,685.04",
        formulas: ["111近5年期末2002/[(近5年期末)]"],
        match: [
          {
            fileId: 12,
            fileName: "111xxxxx年报44",
            fileUrl: "http://10.15.12.13:9009/xxxxx年报44.pdf",
            pageId: 5,
            position: "[417, 729, 534, 729, 534, 762, 417, 762]"
          }
        ]
      },
      {
        // diff: "2流动资产 =货币资金 + 交易性金融资产 + 应收票据 + 应收账款 + 预付款项 + 其他应收款 + 存货 + 一年内到期的非流动资产 + 其他流动资产= 0.02亿",
        tableName: "consolidated_balance444",
        id: 13444,
        indicatorId: 21444,
        name: "111非流动资产444",
        value: "444,685.04",
        // formulas: ["222近5年期末2002/[(近5年期末)]"],
        match: [
          {
            fileId: 13444,
            fileName: "111xxxxx年报4444",
            fileUrl: "http://10.15.12.13:9009/xxxxx年报444.pdf",
            pageId: 5444,
            position: "[417, 729, 534, 729, 534, 762, 417, 762]"
          }
        ],
        subRefers: [
          {
            tableName: "consolidated_balance44",
            id: 1244555,
            indicatorId: 204555,
            name: "222sub流动资产44",
            value: "44,685.04555",
            match: [
              {
                fileId: 12,
                fileName: "222subxxxxx年报44",
                fileUrl: "http://10.15.12.13:9009/xxxxx年报sub44.pdf",
                pageId: 5,
                position: "[417, 729, 534, 729, 534, 762, 417, 762]"
              }
            ]
          },
          {
            tableName: "consolidated_balance444",
            id: 13444666,
            indicatorId: 21446664,
            name: "222sub非流动资产444",
            value: "444,685.04",
            match: [
              {
                fileId: 13444,
                fileName: "222subxxxxx年报4444",
                fileUrl: "http://10.15.12.13:9009/xxxxx年报sub444.pdf",
                pageId: 5444,
                position: "[417, 729, 534, 729, 534, 762, 417, 762]"
              }
            ]
          }
        ]
      },
      {
        diff: "3流动资产 =货币资金 + 交易性金融资产 + 应收票据 + 应收账款 + 预付款项 + 其他应收款 + 存货 + 一年内到期的非流动资产 + 其他流动资产= 0.02亿",
        tableName: "consolidated_balance444",
        id: 1344554,
        indicatorId: 21444,
        name: "111非流动资产444555",
        value: "444,685.04",
        formulas: ["333近5年期末2002/[(近5年期末)]"],
        match: [
          {
            fileId: 13444,
            fileName: "111xxxxx年报4444",
            fileUrl: "http://10.15.12.13:9009/xxxxx年报444.pdf",
            pageId: 5444,
            position: "[417, 729, 534, 729, 534, 762, 417, 762]"
          }
        ],
        subRefers: [
          {
            tableName: "consolidated_balance44",
            id: 124455775,
            indicatorId: 20455775,
            name: "333sub777流动资产44",
            value: "744,685.04555",
            match: [
              {
                fileId: 12,
                fileName: "333sub777xxxxx年报44",
                fileUrl: "http://10.15.12.13:9009/xxxxx年报sub77744.pdf",
                pageId: 5,
                position: "[417, 729, 534, 729, 534, 762, 417, 762]"
              }
            ]
          },
          {
            tableName: "consolidated_balance444",
            id: 13444667776,
            indicatorId: 21446777664,
            name: "333sub777非流动资产444",
            value: "444,685.04",
            match: [
              {
                fileId: 13444,
                fileName: "333sub7777xxxxx年报4444",
                fileUrl: "http://10.15.12.13:9009/xxxxx年报sub777444.pdf",
                pageId: 57,
                position: "[417, 729, 534, 729, 534, 762, 417, 762]"
              }
            ]
          }
        ]
      }
    ]
  }
];
// mock end

const rootId = 9999999999;

const InfoDetail: React.FC<InfoDetailProps> = (props) => {
  const { item, isLoading, confirmInfoByType } = props;
  const [info, setInfo] = useState<any>({});
  const [chooseSourceList, setChooseSourceList] = useState<any[]>([]);
  const [multiValueFile, setMultiValueFile] = useState<any>({});
  const [customValue, setCustomValue] = useState<string>("");
  const [isExpandMap, setIsExpandMap] = useState<any>({});

  const stopPropagation = (e: any) => {
    e.stopPropagation();
  };

  const closeDrawer = () => {
    confirmInfoByType(InfoConfirmTypes.CLOSE, info, {});
  };

  const viewSourceFile = (fileInfo: any) => () => {
    confirmInfoByType(InfoConfirmTypes.SHOW_SOURCE_FILE, info, { fileInfo });
  };

  const chooseSourceFiles = (fileInfo: any) => () => {
    const _chooseSourceList = [...chooseSourceList];
    const idx = _chooseSourceList.findIndex((i: any) => i.id === fileInfo.id);
    let _list: any[] = [];
    if (idx < 0) {
      _list = [..._chooseSourceList, { ...fileInfo }];
    } else {
      _chooseSourceList.splice(idx, 1);
      _list = [..._chooseSourceList];
    }
    setChooseSourceList([..._list]);
    confirmInfoByType(InfoConfirmTypes.CHOOSE_SOURCE_FILE, info, {
      fileList: [
        ..._list.map((i: any) => {
          return i.match[0];
        })
      ]
    });
  };

  const chooseMultiValueFile = (fileInfo: any, idx: number) => () => {
    setMultiValueFile({ ...fileInfo, idx });
    setCustomValue("");
  };

  const customValueChange = (e: any) => {
    const val = e.target.value.trim();

    // if (val === "") {
    //   setCustomValue("");
    //   if (info.source && info.source.length) {
    //     setMultiValueFile({ ...info.source[0], idx: 0 });
    //   }
    //   return;
    // }

    const isValid = /^[-]?(\d*)?(\.)?(\d*)?$/.test(val);
    const decimalCount = (val.match(/\./g) || []).length;
    const hasMultipleDecimals = decimalCount > 1;

    if (
      !isValid ||
      hasMultipleDecimals ||
      (val.includes("-") && !val.startsWith("-"))
    ) {
      return;
    }

    // if (val.includes('.')) {
    //   const decimalPart = val.split('.')[1] || '';
    //   if (decimalPart.length > 4) {
    //     return;
    //   }
    // }

    setCustomValue(val);
    setMultiValueFile({});
  };

  const multiValueFileConfirm = () => {
    // console.log(multiValueFile, customValue);
    const newValue = customValue
      ? customValue.endsWith(".")
        ? customValue.replace(".", "")
        : customValue
      : "";
    const param =
      newValue !== "" ? { newValue } : { adoptIndex: multiValueFile.idx };
    confirmInfoByType(InfoConfirmTypes.MULTI_VALUED_CONFLICT, info, {
      ...param
    });
  };

  const toggleShowMatch = (row: any) => () => {
    const _isExpandMap = { ...isExpandMap };
    if (Object.keys(_isExpandMap).includes(String(row.id))) {
      Object.keys(_isExpandMap).forEach((key: string) => {
        if (key === String(row.id)) {
          _isExpandMap[key] = !_isExpandMap[key];
        } else {
          _isExpandMap[key] = false;
        }
      });
      setIsExpandMap({
        ..._isExpandMap
        // [row.id]: !_isExpandMap[row.id]
      });
    }
  };

  const fixItem = (row: any) => {
    const _row = JSON.parse(JSON.stringify(row));
    if (_row.state === 5 && _row.refers) {
      const _isExpandMap: any = { [rootId]: false };
      _row.refers.forEach((i: any, idx: number) => {
        if (i.id && !_isExpandMap[i.id]) {
          // _isExpandMap[i.id] = idx === 0 ? true : false;
          _isExpandMap[i.id] = false;
        }
      });
      setIsExpandMap({ ..._isExpandMap });
    }
    return _row;
  };

  const resetData = () => {
    setInfo({});
    setChooseSourceList([]);
    setMultiValueFile({});
    setCustomValue("");
    setIsExpandMap({});
  };

  const title = useMemo(() => {
    const _title = info && info[titleKey] ? info[titleKey] : "";
    if (info && info.state) {
      switch (info.state) {
        case 1:
          return "溯源文档";
        case 2:
          return `缺失溯源：${_title || "-"}`;
        case 4:
          return _title || "-";
        case 5:
          return `勾稽校验失败：${_title || "-"}`;
      }
    }
    return _title;
  }, [info]);

  const renderInfo = useCallback(() => {
    if (info && info.state) {
      switch (info.state) {
        case 1:
          return (info.source || []).map((i: any, idx: number) => {
            return (
              <div
                key={`source-file-${idx}`}
                className="h-10 leading-10 rounded px-3 box-border mb-3 mr-3 text-gray-2a text-xs "
                style={{ border: "1px solid #ececee" }}
                // onClick={
                //   i.match && i.match.length
                //     ? viewSourceFile(i.match[0])
                //     : stopPropagation
                // }
                // cursor-pointer hover:bg-[#f1f5ff]
              >
                <div className="flex relative">
                  <FilePdfIcon />
                  <span
                    className="ml-1 max-w-[300px] break-words text-ellipsis line-clamp-1"
                    title={i.match && i.match.length ? i.match[0].fileName : ""}
                  >
                    {i.match && i.match.length ? i.match[0].fileName : "-"}
                  </span>
                  <span className="ml-2">
                    {i.match && i.match.length
                      ? i.match[0].pageId
                        ? `第${i.match[0].pageId}页`
                        : ""
                      : "-"}
                  </span>
                </div>
              </div>
            );
          });
        case 2:
          return (
            <div className="">
              <div className="mb-2 text-gray-2a text-sm">推荐溯源（多选）</div>
              {(info.source || []).map((i: any, idx: number) => {
                return (
                  <div
                    key={`choost-source-file-${idx}`}
                    className={`flex px-3 py-2 rounded cursor-pointer mb-3 ${
                      chooseSourceList.some((j: any) => j.id === i.id)
                        ? "bg-[#f1f5ff]"
                        : "hover:bg-[#f1f5ff]"
                    }`}
                    style={{ border: "1px solid #ececee" }}
                    onClick={chooseSourceFiles(i)}
                  >
                    <div className="flex-1">
                      <div className="h-5 leading-5 text-sm text-[#1d2129] mb-1">
                        <b>{i.value}</b>
                      </div>
                      <div className="h-5 leading-5 box-border text-text-color2 text-xs">
                        <div className="flex relative">
                          <FilePdfIcon />
                          <span className="ml-1 max-w-[285px] break-words text-ellipsis line-clamp-1">
                            {i.match && i.match.length
                              ? i.match[0].fileName
                              : "-"}
                          </span>
                          <span className="ml-2">
                            {i.match && i.match.length
                              ? i.match[0].pageId
                                ? `第${i.match[0].pageId}页`
                                : ""
                              : "-"}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center">
                      {chooseSourceList.some((j: any) => j.id === i.id) ? (
                        <span className="inline-block w-5 h-5 text-center rounded-full bg-[#52c41a] border border-solid border-[#52c4aa]">
                          <CheckOutlined className="text-white w-3" />
                        </span>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          );
        case 4:
          return (
            <>
              {(info.source || []).map((i: any, idx: number) => {
                return (
                  <div
                    key={`choost-source-file-${idx}`}
                    className={`flex px-3 py-2 rounded cursor-pointer mb-3 ${
                      multiValueFile &&
                      multiValueFile.id &&
                      multiValueFile.id === i.id &&
                      customValue === ""
                        ? "bg-[#f1f5ff]"
                        : "hover:bg-[#f1f5ff]"
                    }`}
                    style={{ border: "1px solid #ececee" }}
                    onClick={chooseMultiValueFile(i, idx)}
                  >
                    <div className="flex-1">
                      <div className="h-5 leading-5 text-sm text-[#1d2129] mb-1">
                        <b>{i.value}</b>
                      </div>
                      <div className="h-5 leading-5 box-border text-text-color2 text-xs">
                        <div className="flex relative">
                          <FilePdfIcon />
                          <span className="ml-1 max-w-[285px] break-words text-ellipsis line-clamp-1">
                            {i.match && i.match.length
                              ? i.match[0].fileName
                              : "-"}
                          </span>
                          <span className="ml-2">
                            {i.match && i.match.length
                              ? i.match[0].pageId
                                ? `第${i.match[0].pageId}页`
                                : ""
                              : "-"}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center">
                      {multiValueFile &&
                      multiValueFile.id &&
                      multiValueFile.id === i.id &&
                      customValue === "" ? (
                        <span className="inline-block w-5 h-5 text-center rounded-full bg-[#52c41a] border border-solid border-[#52c4aa]">
                          <CheckOutlined className="text-white w-3" />
                        </span>
                      ) : null}
                    </div>
                  </div>
                );
              })}
              <div className="my-2 text-black text-sm">
                没有正确选项？手动输入值：
              </div>
              <div className="w-full pb-4">
                <Input
                  className="w-full"
                  placeholder="请输入"
                  value={customValue}
                  onChange={customValueChange}
                />
              </div>
            </>
          );
        case 5:
          return (
            <>
              {(info.refers || []).map((i: any, idx: number) => {
                return idx > 0 && !i.diff ? null : (
                  <>
                    {/* 差异 */}
                    <div
                      className={`rounded flex p-3 cursor-pointer mb-3 hover:opacity-85`}
                      style={{
                        border:
                          isExpandMap && isExpandMap[i.id]
                            ? "1px solid #ffccc7"
                            : "1px solid #eee",
                        background:
                          isExpandMap && isExpandMap[i.id]
                            ? "#fff2f0"
                            : "#f5f5f5"
                      }}
                      onClick={toggleShowMatch(i)}
                    >
                      <div className="w-4 flex items-center">
                        <div
                          className="w-3 h-3 bg-[#ff4d4f] rounded-full text-white flex items-center justify-center"
                          style={{ border: "2px solid #ff4d4f" }}
                        >
                          <CloseOutlined className="w-2 h-2 text-white" />
                        </div>
                      </div>
                      <div className="flex-1 px-2 text-gray-2a">
                        {/* 差异： */}
                        {i.diff || "-"}
                      </div>
                    </div>
                    <div className="mb-3">
                      {/* fx */}
                      <div
                        className={`${
                          isExpandMap && isExpandMap[i.id] ? "" : "hidden"
                        }`}
                      >
                        <div className="flex justify-between text-gray-2a mb-2">
                          <span className="leading-8">字段数据对比</span>
                          {idx > 0 && !i.formulas ? null : (
                            <Tooltip
                              placement="topRight"
                              zIndex={1}
                              color="white"
                              styles={{
                                root: {
                                  maxWidth: "300px"
                                }
                              }}
                              title={
                                <div className="text-gray-2a text-sm">
                                  <b>
                                    {i.formulas && i.formulas.length
                                      ? i.formulas.join("，")
                                      : "-"}
                                  </b>
                                </div>
                              }
                            >
                              <Button
                                type="text"
                                className="px-0"
                                icon={
                                  <FxIcon
                                    className={`"text-gray-2a cursor-pointer`}
                                    onClick={stopPropagation}
                                  />
                                }
                              />
                            </Tooltip>
                          )}
                        </div>
                        {/* {JSON.stringify(info)} */}
                        {/* 文件列表 */}
                        {(idx === 0 ? info.refers : i.subRefers || []).map(
                          (j: any, index: number) => {
                            return (
                              <div
                                key={`refers-${j.id}-${index}`}
                                className={`px-3 py-2 rounded mb-2 cursor-default hover:opacity-100 ${
                                  i.match ? "cursor-pointer-no" : ""
                                }`}
                                style={{ border: "1px solid #ececee" }}
                                // onClick={
                                //   j.match && j.match.length
                                //     ? viewSourceFile(j.match[0])
                                //     : stopPropagation
                                // }
                              >
                                <div className="h-5 leading-5 text-sm text-[#1d2129] mb-1">
                                  <b>
                                    {j.name ? `${j.name}：` : ""}
                                    {j.value}
                                  </b>
                                </div>
                                <div className="h-5 leading-5 box-border text-text-color2 text-xs">
                                  {j.match && j.match.length ? (
                                    <div className="flex relative">
                                      <FilePdfIcon />
                                      <span className="ml-1 max-w-[285px] break-words text-ellipsis line-clamp-1">
                                        {j.match[0].fileName}
                                      </span>
                                      <span className="ml-2">
                                        {j.match[0].pageId
                                          ? `第${j.match[0].pageId}页`
                                          : ""}
                                      </span>
                                    </div>
                                  ) : (
                                    <div>无相关文件</div>
                                  )}
                                </div>
                              </div>
                            );
                          }
                        )}
                      </div>
                    </div>
                  </>
                );
              })}
            </>
          );
      }
    }
    return <Empty className="mt-28" />;
  }, [info, chooseSourceList, multiValueFile, customValue, isExpandMap]);

  const renderBtn = useCallback(() => {
    if (info && info.state === 4) {
      return (
        <div className="absolute bottom-0 left-0 right-0 bg-white flex justify-end pr-3 pb-0 z-50">
          <Button
            type="primary"
            className="border-0 bg-[linear-gradient(99.9deg,#2B69FF,#8F91FF)]"
            disabled={!customValue && !multiValueFile.id}
            onClick={multiValueFileConfirm}
            loading={isLoading}
          >
            确认
          </Button>
        </div>
      );
    }
    return null;
  }, [info, multiValueFile, customValue, isLoading]);

  useEffect(() => {
    if (isMock) {
      // mock
      const idx = getRandomInt(0, 3);
      const _info = cases[isRandom ? idx : randomNum];
      if (_info && !info.state) {
        console.log(idx);
        setInfo({ ...fixItem(_info) });
      }
    } else {
      if (item && item.state) {
        // 判断item存在并保存
        setInfo(fixItem(item));
      } else {
        resetData();
      }
    }
  }, [item]);

  return (
    <>
      <div
        className="h-14 leading-[56px] flex justify-between text-base bg-white"
        style={{ borderBottom: "1px solid #ececee" }}
      >
        <div className="text-[#1d2129] pl-5 select-none">
          <b>{title || "-"}</b>
        </div>
        <Button
          className="mt-3 mr-2"
          type="text"
          onClick={closeDrawer}
          icon={
            <CloseOutlined className="w-4 cursor-pointer hover:opacity-80" />
          }
        />
      </div>
      <div className="pt-3 select-none relative h-[calc(100vh-340px)]">
        {renderBtn()}
        <div className="overflow-y-auto overflow-x-hidden h-[calc(100vh-380px)] bg-white pl-5 ">
          {renderInfo()}
        </div>
      </div>
    </>
  );
};

export default InfoDetail;
