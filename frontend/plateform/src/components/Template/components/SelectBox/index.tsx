import { Checkbox, Flex, Input } from "antd";
import {
  ChangeEventHandler,
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react";
import "./styles.less";
import chuansuo from "@/assets/img/chuansuo.png";
import CloseCircle from "@/assets/img/CloseCircle.png";
import { SearchOutlined } from "@ant-design/icons";

interface ICheckedData {
  id: string;
  name: string;
  isDelete?: boolean;
}
const SelectBox = ({
  options,
  checkedData,
  setCheckedData,
  sensitiveWords, //初始值
  title,
  isVersion // 查看版本时，不可操作
}: any) => {
  const [fuzzyNameOrId, setFuzzyNameOrId] = useState("");
  const [tempFuzzy, setTempFuzzy] = useState("");
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
      setCheckedData((pre: ICheckedData[]) => {
        return [item, ...pre];
      });
    } else {
      const res = checkedData.filter((i: ICheckedData) => i.id !== id);
      setCheckedData([...res]);
    }
  };

  const handleRemove = (item: any) => {
    const res = checkedData.filter((i: ICheckedData) => i.id !== item.id);
    setCheckedData(res);
  };

  const checkedOptions = useMemo(() => {
    return options
      .map((item: any) => {
        return {
          ...item,
          checked: checkedData.find((i) => i.id == item.id)
        };
      })
      .filter((item: any) => item.name.indexOf(fuzzyNameOrId) > -1);
  }, [checkedData, options, fuzzyNameOrId]);

  // 将敏感词库已删除的，删除线展示
  // 排序，删除的展示到最后面
  const handleSensitiveWords = (
    sensitiveWords: ICheckedData[],
    options: ICheckedData[]
  ) => {
    const result = sensitiveWords.map((item) => {
      const isDelete = !options.some((aItem) => aItem.id === item.id);
      return { ...item, isDelete };
    });
    const sortedRes = [...result].sort((a, b) => a.isDelete - b.isDelete);
    return sortedRes;
  };

  useEffect(() => {
    const res = handleSensitiveWords(sensitiveWords, options);
    setCheckedData(res);
    setFuzzyNameOrId("");
    setTempFuzzy("");
  }, [sensitiveWords, options]);

  return (
    <Flex
      justify="space-between"
      className="selectBox"
      aria-disabled={isVersion}
    >
      <div className="w-[calc(50%-32px)]">
        <div className="mb-[8px] flex justify-between">
          {title}（共{options?.length || 0}个）
        </div>
        <div
          style={{
            width: "100%",
            height: "317px",
            overflowY: "hidden",
            border: "1px solid #d9d9d9",
            borderRadius: " 4px",
            padding: "12px"
          }}
        >
          <Input
            // allowClear
            disabled={isVersion}
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
              height: "260px",
              marginTop: "12px"
            }}
          >
            {checkedOptions.map((item: any, index: number) => {
              return (
                <div
                  className="h-[32px] flex items-center rounded-[4px] mb-[2px] overflow-hidden px-[8px]"
                  style={{ backgroundColor: item?.checked ? "#F4F5F7" : "" }}
                  key={`${item.id}`}
                >
                  <Checkbox
                    disabled={isVersion}
                    key={item.id}
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
                    onChange={(checkedValue) =>
                      handleChecked(checkedValue, item)
                    }
                    checked={item.checked}
                  >
                    {item.name}
                  </Checkbox>
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <div className="w-[32px]">
        <img src={chuansuo} width={32} height={32} className="mt-[60px]" />
      </div>
      <div className="w-[calc(50%-32px)]">
        <div className="mb-[8px]">已选择{checkedData.length || 0}个</div>
        <div
          style={{
            width: "100%",
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
              height: "317px"
            }}
          >
            {checkedData.map((item: any, index: any) => {
              return (
                <div
                  key={`check-${item.id}`}
                  className="flex justify-between items-center h-[32px] mb-[2px]"
                >
                  <div
                    className={`${item.isDelete && "line-through text-[#888888]"}`}
                  >
                    {item?.name}
                  </div>
                  <img
                    src={CloseCircle}
                    width={16}
                    height={16}
                    className={`mr-[4px] ${
                      isVersion ? "cursor-not-allowed" : " cursor-pointer"
                    }`}
                    onClick={() => {
                      if (isVersion) return;
                      handleRemove(item);
                    }}
                  />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Flex>
  );
};

export default SelectBox;
