import { Checkbox, Flex, Input, Popover, Select, Space } from "antd";
import {
  ChangeEventHandler,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import "./styles.less";
import chuansuo from "../../../../../assets/img/chuansuo.png";
import CloseCircle from "../../../../../assets/img/CloseCircle.png";
import { CloseOutlined, SearchOutlined } from "@ant-design/icons";
import { useServices } from "@root/src/components/KnowledgeBaseZh/service";
const SelectBox = ({
  options,
  checkedData,
  setCheckedData,
  sensitiveWordIds,
  title,
  disabled,
  max,
  type = "default"
}: any) => {
  const [fuzzyNameOrId, setFuzzyNameOrId] = useState("");
  const [tempFuzzy, setTempFuzzy] = useState("");
  const [labelOptions, setLabelOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const map = useRef(new Map()).current;
  const { getBizLabelLabels } = useServices();
  const fetchList = () => {
    setFuzzyNameOrId(tempFuzzy);
  };
  const fuzzyNameOrIdOnChange: ChangeEventHandler<HTMLInputElement> = (e) => {
    const inputElement = e.target as HTMLInputElement;
    setTempFuzzy(inputElement.value.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      fetchList();
    }
  };
  const handleChecked = (checkedValue: any, item: any) => {
    const { target } = checkedValue;
    const { id } = item;
    if (target.checked) {
      setCheckedData((pre: string[]) => {
        if (type === "default") {
          return [...pre, id];
        } else {
          return [...pre, { ...item, labels: [] }];
        }
      });
    } else {
      let res;
      if (type === "default") {
        res = checkedData.filter((i: string) => i !== id);
      } else {
        res = checkedData.filter((i: any) => i.id !== id);
      }
      setCheckedData([...res]);
    }
  };

  const handleRemove = (item: any) => {
    if (disabled) return;
    const res = checkedData.filter((i: any) => {
      return type === "default" ? i !== item : i.id !== item.id;
    });
    setCheckedData(res);
  };

  const checkedOptions = useMemo(() => {
    let checked = checkedData;
    if (type !== "default") {
      checked = checkedData.map((i: any) => i.id);
    }
    return options
      .map((item: any) => {
        return {
          ...item,
          checked: checked.includes(item.id)
        };
      })
      .filter((item: any) => {
        const res = item.name.indexOf(fuzzyNameOrId) > -1;
        return res;
      });
  }, [checkedData, options, fuzzyNameOrId]);

  useEffect(() => {
    setCheckedData(sensitiveWordIds);
    setFuzzyNameOrId("");
    setTempFuzzy("");
  }, [sensitiveWordIds]);

  const getPrefix = (item: any) => {
    return (
      <Popover placement="topLeft" content={item.name}>
        <div className="w-[80px] text-ellipsis line-clamp-1 cursor-default">
          {item.name}
        </div>
      </Popover>
    );
  };
  // 监听下拉框展开事件
  const handleDropdownVisibleChange = async (
    open: boolean,
    targetId: number
  ) => {
    if (open) {
      const o = map.get(targetId);
      if (o) {
        setLabelOptions(o);
        return;
      }
      // 如果尚未加载过数据，则发起请求
      if (!loading) {
        try {
          setLoading(true);
          const res: any = await getBizLabelLabels({ kbNames: [targetId] });

          if (Array.isArray(res)) {
            const label = res.length ? res[0].label : "";
            const labels = label
              ? (label || "").split(",").map((item: any) => {
                  return { label: item, value: item };
                })
              : [];

            map.set(targetId, labels);
            setLabelOptions(labels);
          }
          setLoading(false);
        } catch (error) {
          console.error("Error fetching data:", error);
          setLoading(false);
        }
      }
    }
  };

  const renderLeft = useMemo(() => {
    return (
      <>
        {checkedOptions.map((item: any, index: number) => {
          return (
            <div
              className="h-[32px] flex items-center rounded-[4px] mb-[2px] overflow-hidden px-[8px]"
              style={{ backgroundColor: item?.checked ? "#F4F5F7" : "" }}
            >
              <Checkbox
                style={{
                  height: "24px",
                  margin: "10px",
                  fontFamily: "Source Han Sans CN",
                  fontSize: "14px",
                  fontWeight: "400",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap"
                }}
                onChange={(checkedValue) => handleChecked(checkedValue, item)}
                checked={item.checked}
                disabled={max && checkedData?.length >= max}
              >
                {item.name}
              </Checkbox>
            </div>
          );
        })}
      </>
    );
  }, [checkedOptions, checkedData]);
  return (
    <Flex justify="space-between" className="selectBox">
      <div>
        <div className="mb-[8px]">
          {title}（共{options?.length || 0}个）
        </div>
        <div
          style={{
            width: "324px",
            height: "317px",
            overflowY: "hidden",
            border: "1px solid #d9d9d9",
            borderRadius: " 4px",
            padding: "12px"
          }}
        >
          <Input
            // allowClear
            placeholder="请输入内容"
            value={tempFuzzy}
            suffix={
              <SearchOutlined
                style={{ color: "#999", fontSize: 12 }}
                onClick={() => fetchList()}
              />
            }
            onChange={fuzzyNameOrIdOnChange}
            onKeyDown={handleKeyDown}
          />
          <div
            style={{
              overflowY: "auto",
              height: "250px",
              marginTop: "12px"
            }}
          >
            {renderLeft}
          </div>
        </div>
      </div>
      <div>
        <img src={chuansuo} width={32} height={32} className="mt-[60px]" />
      </div>
      <div>
        <div className="mb-[8px] flex justify-between items-end">
          <span>已选择{checkedData.length || 0}个</span>
          {max && checkedData?.length >= max && (
            <span className="text-[#FF3B30] text-[12px]">
              已达上限，如需调整，删除后重选
            </span>
          )}
        </div>
        <div
          style={{
            width: "324px",
            height: "317px",
            border: "1px solid #d9d9d9",
            overflowY: "hidden",
            borderRadius: " 4px",
            padding: "12px"
          }}
        >
          <div
            style={{
              overflowY: "auto",
              overflowX: "hidden",
              height: "305px"
            }}
          >
            {checkedData.map((item: any, index: any) => {
              return (
                <>
                  {type === "default" ? (
                    <div
                      key={item}
                      className="flex justify-between items-center h-[32px] mb-[2px]"
                    >
                      <>
                        <div>
                          {
                            checkedOptions.find((v: any) => {
                              return v.id == item;
                            })?.name
                          }
                        </div>

                        <img
                          src={CloseCircle}
                          width={16}
                          height={16}
                          className={` mr-[4px] ${
                            disabled ? "cursor-not-allowed" : "cursor-pointer"
                          } z-50`}
                          onClick={() => handleRemove(item)}
                        />
                      </>
                    </div>
                  ) : (
                    <div
                      key={`${item.id}`}
                      className={`flex justify-between items-center h-[32px] mb-[8px] ${
                        type === "default" ? "h-[32px]" : "h-[40px]"
                      }`}
                    >
                      <Select
                        prefix={getPrefix(item)}
                        className="knowledge_select mr-[8px]"
                        onChange={(value: any) => {
                          setCheckedData((pre: any) => {
                            const cur = pre.find((v: any) => v.id === item.id);
                            cur.labels = value;
                            return [...pre];
                          });
                        }}
                        removeIcon={
                          <CloseOutlined className="text-[#1d70f5]" />
                        }
                        style={{ width: "270px" }}
                        value={item.labels}
                        mode="multiple"
                        maxTagCount={1}
                        options={labelOptions}
                        loading={loading}
                        onDropdownVisibleChange={(open: boolean) => {
                          handleDropdownVisibleChange(
                            open,
                            item.knowledge_base_name
                          );
                        }}
                      />
                      <img
                        src={CloseCircle}
                        width={16}
                        height={16}
                        className={` mr-[4px] ${
                          disabled ? "cursor-not-allowed" : "cursor-pointer"
                        } z-50`}
                        onClick={() => handleRemove(item)}
                      />
                    </div>
                  )}
                </>
              );
            })}
          </div>
        </div>
      </div>
    </Flex>
  );
};

export default SelectBox;
