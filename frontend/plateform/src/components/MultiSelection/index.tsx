import { Checkbox, Input, Spin } from "antd";
import SelectCom from "../../pages/Components/SelectRight";
import {
  CloseOutlined,
  RightOutlined,
  SearchOutlined
} from "@ant-design/icons";
import IconHeader from "../../pages/Components/IconHeader";
import { useEffect, useMemo, useState } from "react";
import { ELEMENT_TYPE, PERMISSION_STATUS } from "@root/src/const/permission";
import { cloneDeep } from "lodash";
import useSystemApi from "@root/src/apis/system";
import _ from "lodash";

export const getId = (item: any) => {
  return `${item.id}_${item.elementType}`;
};

const MultiSelection = ({
  checkedData,
  setCheckedData,
  allList,
  clickNavbar,
  curPartment,
  loading,
  width,
  placeholder,
  type
}: {
  checkedData: any;
  allList: any[];
  clickNavbar: (arg: any) => void;
  setCheckedData: (arg: any) => void;
  curPartment: any[];
  loading: boolean;
  width: number;
  placeholder?: string;
  type?: string;
}) => {
  const api = useSystemApi();
  const [listMap, setListMap] = useState(new Map());
  const [listData, setListData]: any = useState([]);
  const [searchList, setSearchList]: any = useState([]);
  const [searchInput, setSearchInput] = useState("");
  const getMap = (data: any) => {
    const res = new Map();
    const recursionFn = (data: any, parentMap: Map<any, any>) => {
      data.forEach((item: any) => {
        item.id = getId(item);
        const existingItem = parentMap.get(item.id);
        if (existingItem) {
          // if (item.id === "3_1") {
          //   //debugger;
          // }
          // Object.assign(existingItem, item);
          // res.set(item.id, existingItem);
        } else {
          res.set(item.id, item);
        }
        if (item?.children?.length) {
          recursionFn(item.children, res);
        }
      });
    };
    recursionFn(data, res);
    return res;
  };

  const getCheckedData = () => {
    const result: any[] = [];
    listMap.forEach((value: any) => {
      if (value.checked) {
        result.push(value);
      }
    });
    return result;
  };

  const frameSearchFn = async (searchInput: string) => {
    try {
      const res: any = await api.frameSearch({ fuzzy: searchInput });
      if (res.success) {
        setSearchList(
          res.data.map((item: any) => {
            const id = getId(item);
            return {
              ...item,
              id,
              checked: listMap.get(id)?.checked
            };
          })
        );
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  const searchDept = _.debounce((v) => {
    if (v) {
      frameSearchFn(v);
    } else {
      setSearchList([]);
    }
  }, 300);

  const onSearchChange = (v: any) => {
    setSearchInput(v);
    searchDept(v);
  };

  useEffect(() => {
    setCheckedData(getCheckedData());
  }, [listMap]);

  useEffect(() => {
    const data = cloneDeep(allList);
    setListData(data);
    const map = getMap(data);
    setListMap(map);
  }, [allList]);

  useEffect(() => {
    if (curPartment?.length) {
      const curP = curPartment[curPartment.length - 1];
      setListData(listMap?.get(curP)?.children || []);
    }
  }, [curPartment, listMap]);

  const renderList = (list: any[], type?: string) => {
    return (
      <>
        {list.map((item: any) => {
          return (
            <div
              key={item.id}
              className="flex mb-[12px] cursor-pointer justify-between"
              onClick={() => clickNavbar && clickNavbar(item)}
            >
              <div className="flex items-center flex-1">
                {!item.hideCheck && (
                  <Checkbox
                    checked={item.checked}
                    onClick={(e) => {
                      e.stopPropagation();
                    }}
                    onChange={(e) => {
                      const cur = listMap.get(item.id);
                      if (!cur) return;

                      cur.checked = e.target.checked;
                      if (!cur.permission) {
                        cur.permission = PERMISSION_STATUS.READ_ONLY;
                      }
                      setListMap(new Map(listMap));
                      setListData((pre: any) => {
                        pre.forEach((v: any) => {
                          if (item.id === v.id) {
                            item.checked = cur.checked;
                          }
                        });
                        return [...pre];
                      });
                      setSearchList((pre: any) => {
                        pre.forEach((v: any) => {
                          if (item.id === v.id) {
                            item.checked = cur.checked;
                          }
                        });
                        return [...pre];
                      });
                    }}
                    className="mr-[12px]"
                  />
                )}
                <IconHeader
                  text={item.name || item.userRealname || item.userName}
                  size={28}
                  type={item.elementType}
                  rounded="rounded-full"
                />
                <div className="text-ellipsis line-clamp-1 mr-[12px] text-[#2A2A2A] leading-[28px]">
                  {item.name || item.userRealname || item.userName}
                </div>
              </div>
              {item.elementType === ELEMENT_TYPE.DEPARTMENT &&
              type !== "search" ? (
                <RightOutlined
                  className={`text-[10px] ${item.checked ? "text-[#bbbbbb]" : "text-[#055aff]"} mr-[5px]`}
                />
              ) : (
                <></>
              )}
            </div>
          );
        })}
      </>
    );
  };

  useEffect(() => {
    console.log("listData------->", listData);
    console.log("curPartment------->", curPartment);
    console.log("searchList------->", searchList);
    console.log("searchInput------->", searchInput);
    console.log("!searchInput------->", !searchInput);
  }, [searchList]);

  return (
    <div className="w-full h-full flex relative">
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-white bg-opacity-75">
          <Spin size="large" />
        </div>
      )}
      <div
        className={`flex flex-col flex-1 h-full border-solid box-border border-l-0 border-t-0 border-b-0 border-r-[1px] border-[#D9D9D9] p-[16px] shrink-0`}
        style={{ width: `${width / 2}px` }}
      >
        <Input
          placeholder={placeholder || "搜索用户、群组、部门或用户组"}
          suffix={<SearchOutlined onClick={() => {}} />}
          style={{ width: "100%" }}
          value={searchInput}
          onChange={(e) => onSearchChange(e?.target?.value || "")}
        />
        {!searchInput && (
          <div className="flex items-center mt-[16px] flex-wrap">
            {(curPartment || []).map((item: any, index: number) => {
              return (
                <div
                  key={item}
                  onClick={() => clickNavbar(listMap.get(item))}
                  className={`flex ${curPartment?.length && index < curPartment.length - 1 ? "hover:text-[#69B1FF] active:text-[#055AFF] text-[#055AFF] font-normal cursor-pointer" : "text-text-color1 cursor-default font-bold"}`}
                >
                  {index !== 0 && (
                    <RightOutlined className="text-[10px] text-[#ccc] mr-[8px]" />
                  )}
                  <div className="mr-[8px]">{listMap.get(item)?.name}</div>
                </div>
              );
            })}
          </div>
        )}
        <div className="mt-[16px] flex-1 overflow-y-auto">
          <div style={{ display: searchInput ? "" : "none" }}>
            {renderList(searchList, "search")}
          </div>
          <div style={{ display: searchInput ? "none" : "" }}>
            {renderList(listData)}
          </div>
        </div>
      </div>
      <div
        className={`flex-1 w-1/2 p-[16px] text-[13px] text-text-color1 shrink-0`}
        style={{ width: `${width / 2}px` }}
      >
        <div>已选: &nbsp;&nbsp;{checkedData.length} 个</div>
        <div className="mt-[16px] h-[260px] overflow-y-auto">
          {checkedData.map((item: any) => {
            return (
              <div
                key={item.id}
                className="flex mb-[12px] cursor-pointer items-center"
              >
                <IconHeader
                  text={item.name || item.userRealname || item.userName}
                  size={28}
                  type={item.elementType}
                  rounded="rounded-full"
                  bg={
                    item.permission === 1
                      ? "linear-gradient(90deg,#FF9A53,#FFCF70)"
                      : item.permission === 2
                        ? "linear-gradient(90deg,#4088F4,#7FC0FB)"
                        : "linear-gradient(90deg,#99D65B,#7FDBCB)"
                  }
                />
                <div
                  className="text-ellipsis line-clamp-1 mr-[12px] text-[#2A2A2A]"
                  style={{ width: `${width / 2 - 249}px` }}
                >
                  {item.name || item.userRealname || item.userName}
                </div>
                <SelectCom
                  value={item.permission}
                  onChange={(value: number) => {
                    const cur = listMap.get(item.id);
                    if (!cur) return;
                    cur.permission = value;
                    setListMap(new Map(listMap));
                  }}
                  className="mr-[12px]"
                  type={type}
                />
                <CloseOutlined
                  className="text-[#666666] mr-[5px]"
                  onClick={(e) => {
                    const cur = listMap.get(item.id);
                    if (!cur) return;
                    cur.checked = false;
                    setListMap(new Map(listMap));
                  }}
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default MultiSelection;
