import React, { useState, useMemo, useEffect } from "react";
import { Card, Flex, Form, Input, Select, Skeleton, Space, Spin } from "antd";
import { IAssistant } from "../../@types/props";
import "./style.less";
import Search from "../../assets/img/search.svg";
import IconAi from "../../assets/img/iconAi.svg";
import IconAiClick from "../../assets/img/answerAwartar.png";
import Selected from "../../assets/img/selected.svg";

interface AssistantSelectorProps {
  appData?: any;
  assistList: IAssistant[];
  value: string;
  onChange: (value: string) => void;
  loading: boolean;
  disabled?: boolean;
  className?: string;
}

const AssistantSelector: React.FC<AssistantSelectorProps> = ({
  appData,
  assistList,
  value,
  onChange,
  loading,
  disabled = false,
  className = ""
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
    onChange(selectedValue || "");
    setDropdownOpen(false);
  };

  useEffect(() => {
    if (appData && assistList && assistList.length > 0) {
      setFilteredAssistantList([...assistList]);
    }
  }, [appData]);

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

  return (
    <div className={`w-[443px] h-[40px] relative ${className}`}>
      {value !== "showLoading" && (
        <img
          src={IconAiClick}
          width={24}
          height={24}
          className="absolute z-10 top mr-[12px] ml-[12px] mt-[8px]"
        />
      )}
      {!disabled && (
        <Select
          open={dropdownOpen}
          onDropdownVisibleChange={setDropdownOpen}
          popupMatchSelectWidth={false}
          style={{ height: "40px", width: "312px" }}
          dropdownStyle={{
            width: "443px",
            maxHeight: "425px",
            overflowY: "auto",
            backgroundColor: "#fff"
          }}
          disabled={disabled}
          className="assistantSelector"
          dropdownRender={() => (
            <div style={{ padding: "8px", marginTop: "4px" }}>
              <Input
                placeholder="请输入"
                onChange={handleSearchAssistant}
                style={{ marginBottom: "8px" }}
                suffix={<img src={Search} />}
              />
              <div
                style={{
                  maxHeight: "calc(280px - 40px)",
                  overflowY: "auto",
                  overflowX: "hidden"
                }}
              >
                {(filteredAssistantList || assistList).map((item, index) => (
                  <Flex
                    align="center"
                    className="w-[420px] h-[68px] rounded-[8px] mt-[8px] cursor-pointer"
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
                      className="mr-[8px] ml-[8px]"
                    />
                    <div className="w-[344px]">
                      <div className="w-full text-[#2a2a2a] text-[14px] text-ellipsis break-words line-clamp-1">
                        {item.label}
                      </div>
                      <div className="w-full text-[#888888] text-[12px] text-ellipsis break-words line-clamp-1 mt-[2px]">
                        大模型：{getAssistDetailInfo(item.value).modelName}
                        :&nbsp;&nbsp; 温度：
                        {getAssistDetailInfo(item.value).temperature}
                        &nbsp;&nbsp; 最大标记：
                        {getAssistDetailInfo(item.value).maxTokens}
                      </div>
                    </div>
                    <div className="w-[32px] h-full flex justify-center items-center">
                      {value === item.value && <img src={Selected} />}
                    </div>
                  </Flex>
                  // <Card
                  //   key={item.value}
                  //   onClick={() => handleSelect(item.value)}
                  //   title={item.label}
                  //   style={{ width: '100%', marginBottom: '8px' }}
                  // >
                  //   <Space direction="vertical">
                  //     <div>模型名称: {getAssistDetailInfo(item.value).modelName}</div>
                  //     <div>温度: {getAssistDetailInfo(item.value).temperature}</div>
                  //     <div>最大标记: {getAssistDetailInfo(item.value).maxTokens}</div>
                  //   </Space>
                  // </Card>
                ))}
              </div>
            </div>
          )}
          value={value || ""}
          onChange={handleSelect}
          options={(filteredAssistantList || assistList).map((item) => ({
            value: item.value,
            label: item.label
          }))}
          loading={loading}
        />
      )}
      {disabled && (
        <div
          style={{
            height: 40,
            lineHeight: "40px",
            textIndent: 50,
            fontFamily: `Microsoft YaHei`,
            fontSize: "14px",
            fontWeight: "400"
          }}
        >
          {value === "showLoading" ? (
            <Skeleton active paragraph={{ rows: 0 }} />
          ) : (
            assistList.find((assist) => assist.value === value)?.label ||
            "无助手展示"
          )}
        </div>
      )}
    </div>
  );
};

export default AssistantSelector;
