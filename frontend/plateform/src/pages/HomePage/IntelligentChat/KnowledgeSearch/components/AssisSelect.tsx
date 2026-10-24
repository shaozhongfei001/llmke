import React, { useState, useMemo } from "react";
import { Flex, Input, Select } from "antd";
import { IAssistant } from "@/components/AiChatComparison/@types/props";
import Search from "@/components/AiChatComparison/assets/img/search.svg";
import IconAi from "@/components/AiChatComparison/assets/img/iconAi.svg";
import IconAiClick from "@/components/AiChatComparison/assets/img/answerAwartar.png";
import Selected from "@/components/AiChatComparison/assets/img/selected.svg";
import "./new-style.less";

interface AssistantSelectorProps {
  assistList: IAssistant[];
  value: string;
  loading: boolean;
  disabled?: boolean;
  className?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  onBlurHandler?: () => void;
}

const AssisSelect: React.FC<AssistantSelectorProps> = ({
  assistList,
  value,
  loading,
  defaultValue,
  disabled = false,
  className = "",
  onChange,
  onBlurHandler = () => {}
}) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [filteredAssistantList, setFilteredAssistantList] =
    useState<IAssistant[]>();

  const handleSearchAssistant = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (assistList && assistList.length > 0) {
      const filteredList = assistList.filter((item) =>
        item.label.toLowerCase().includes(e.target.value.toLowerCase())
      );
      setFilteredAssistantList(filteredList);
    }
  };

  const handleSelect = (selectedValue: string) => {
    onChange && onChange(selectedValue || "");
    setDropdownOpen(false);
  };

  const getAssistDetailInfo = useMemo(() => {
    return (value: string) => {
      const assist = assistList.find((assist) => assist.value === value);
      return {
        modelName: assist?.details.model_name || "N/A",
        temperature: assist?.details.temperature || "N/A",
        maxTokens: assist?.details.max_tokens || "N/A"
      };
    };
  }, [assistList]);

  const dropdownRender = () => {
    return (
      <div className="p2 mt-1 w-full bg-white drop-down-wrap">
        <Input
          placeholder="请输入"
          onChange={handleSearchAssistant}
          suffix={<img src={Search} />}
          className="mb-2"
        />
        <div className="overflow-y-auto overflow-x-hidden max-h-64 pr-2">
          {(filteredAssistantList || assistList).map((item, index) => (
            <Flex
              align="center"
              className="h-16 rounded-2 mt-2 cursor-pointer"
              style={{
                backgroundColor: value === item.value ? "#F1F7FF" : "#fff"
              }}
              onClick={() => handleSelect(item.value)}
              key={index}
            >
              <img
                src={value === item.value ? IconAiClick : IconAi}
                width={24}
                height={24}
                className="mx-2"
              />
              <div className="min-w-80 w-full">
                <div className="w-full text-[#2a2a2a] text-sm text-ellipsis break-words line-clamp-1">
                  {item.label}
                </div>
                <div className="w-full text-[#888888] text-xs text-ellipsis break-words line-clamp-1 mt-1">
                  大模型：{getAssistDetailInfo(item.value).modelName}
                  <span className="mx-2">
                    温度：
                    {getAssistDetailInfo(item.value).temperature}
                  </span>
                  最大标记：
                  {getAssistDetailInfo(item.value).maxTokens}
                </div>
              </div>
              <div className="w-8 h-full flex justify-center items-center">
                {value === item.value && <img src={Selected} />}
              </div>
            </Flex>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div
      className={`w-full relative ${className} bg-white h-11 assis-select-wrap min-w-80`}
    >
      <img src={IconAiClick} width={20} height={20} className="absolute" />
      <Select
        open={dropdownOpen}
        onDropdownVisibleChange={setDropdownOpen}
        popupMatchSelectWidth={false}
        disabled={disabled}
        className="assistantSelector h-8 w-full"
        dropdownRender={dropdownRender}
        value={value}
        onChange={handleSelect}
        options={(filteredAssistantList || assistList).map((item) => ({
          value: item.value,
          label: item.label
        }))}
        placeholder="没有助手可选，请先创建助手配置"
        defaultValue={defaultValue}
        loading={loading}
        onBlur={onBlurHandler}
      />
    </div>
  );
};

export default AssisSelect;
