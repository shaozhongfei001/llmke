import { Button, Input, Select } from "antd";
import { ChangeEventHandler } from "react";
import { SearchOutlined, PlusCircleOutlined } from "@ant-design/icons";
import { konwledgeTitles, ITabs } from "@/const/knowledgebase";
import "@/assets/styles/knowledgebase.less";

interface INavBar {
  isShowSearchBar: boolean;
  currentTab: number;
  fuzzyNameOrId: any;
  disabled: boolean;
  onTabChange: (tabKey: number) => void;
  onCreateClick: () => void;
  fetchList: (str?: string) => void;
  konwledgeTitlesTab?:
    | {
        key: number;
        label: string;
      }[]
    | "hide";
  uploadBtn?: React.ReactNode;
  selectOpt?: {
    value: number;
    label: string;
  }[];
  platform?: string;
  emitEvent: (type: string, data?: any) => void;
}

const NavBar = (props: INavBar) => {
  const {
    currentTab,
    fuzzyNameOrId,
    disabled,
    onTabChange,
    onCreateClick,
    konwledgeTitlesTab = konwledgeTitles,
    uploadBtn,
    selectOpt,
    platform = "rag-qa",
    emitEvent
  } = props;

  const fuzzyNameOrIdOnChange: ChangeEventHandler<HTMLInputElement> = (e) => {
    const inputElement = e.target as HTMLInputElement;
    fuzzyNameOrId.current = inputElement.value.trim();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      emitEvent("search", fuzzyNameOrId.current);
    }
  };

  return (
    <div className="title-wrap">
      {konwledgeTitlesTab === "hide" ? null : (
        <div className="tabs-wrap">
          {konwledgeTitlesTab.map((item: ITabs, idx: number) => {
            return (
              <div
                className={`tab${currentTab === item.key ? " active" : ""}`}
                key={`knowledge-tab-${idx}`}
                onClick={() => {
                  onTabChange(item.key);
                }}
              >
                <span>{item.label}</span>
              </div>
            );
          })}
        </div>
      )}
      <div className="search-bar">
        {currentTab == 1 && (
          <div>
            {uploadBtn ? (
              uploadBtn
            ) : (
              <Button
                type="default"
                disabled={disabled}
                icon={<PlusCircleOutlined />}
                style={{
                  background: `linear-gradient(313.7deg, #BD9CFF -2.37%, #0359FF 100%)`,
                  color: "#fff",
                  border: "none"
                }}
                onClick={onCreateClick}
              >
                新建
              </Button>
            )}
          </div>
        )}
        {currentTab != 1 && <div></div>}
        <div className="flex">
          {platform !== "rag-qa" && (
            <div className="mr-4 w-[110px]">
              <Select
                className="w-full"
                defaultValue={1}
                options={selectOpt}
                popupClassName="kb-select-box"
                onChange={onTabChange}
                value={currentTab}
              />
            </div>
          )}
          <Input
            // allowClear
            disabled={disabled}
            placeholder="输入名称或id搜索"
            style={{
              width: "240px",
              marginRight: "16px"
            }}
            suffix={
              <SearchOutlined
                style={{ color: "#999", fontSize: 12 }}
                onClick={() => emitEvent("search", fuzzyNameOrId.current)}
              />
            }
            onChange={fuzzyNameOrIdOnChange}
            onKeyDown={handleKeyDown}
          />
        </div>
      </div>
    </div>
  );
};

export default NavBar;
