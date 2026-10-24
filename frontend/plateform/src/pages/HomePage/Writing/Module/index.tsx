import { Tabs, Input } from "antd";
import { useEffect, useState, useMemo } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { SearchOutlined, PlusOutlined } from "@ant-design/icons";
import { IAnalysis } from "./common/type.ts";
import ListItem from "./components/ListItem.tsx";
import { useServices } from "./common/server.ts";

enum ModuleType {
  Chapter = "1",
  Analyze = "2"
}

const items = [
  {
    key: ModuleType.Chapter,
    label: "章节组件"
  },
  {
    key: ModuleType.Analyze,
    label: "分析组件"
  }
];

const urlObj: any = {
  [ModuleType.Chapter]: "/docWriting/component/chapter",
  [ModuleType.Analyze]: "/docWriting/component/analyze"
};

function Module() {
  const [activeKey, setActiveKey] = useState<string>(ModuleType.Chapter);

  const location = useLocation();
  const navigator = useNavigate();

  const [searchVal, setSearchVal] = useState<string>();
  const [searchRes, setSearchRes] = useState<IAnalysis[]>();

  const { getAnalysisList } = useServices();

  useEffect(() => {
    if (
      location.pathname === "/docWriting/component" ||
      location.pathname === "docWriting/component"
    ) {
      onChange(ModuleType.Chapter);
    } else {
      const key = Object.keys(urlObj).find((key) => {
        return urlObj[key] === location.pathname;
      });
      if (key) {
        setActiveKey(key);
      } else {
        setActiveKey(ModuleType.Chapter);
      }
    }
  }, [location]);

  const onChange = (activeKey: string) => {
    setActiveKey(activeKey);
    navigator(urlObj[activeKey]);
  };

  const isSearching = useMemo(() => {
    return searchVal && searchVal.trim()?.length > 0;
  }, [searchVal]);

  const getList = async () => {
    try {
      if (searchVal) {
        const res = await getAnalysisList.mutateAsync({ search: searchVal });
        setSearchRes(res?.details);
      }
    } catch (e) {
      console.log("search analysis err ------>", e);
    }
  };

  return (
    <div className="h-full relative overflow-hidden component-module">
      <span className="text-[#2a2a2a] font-bold text-[16px] inline-block mb-[16px]">
        组件管理
      </span>
      <div className="w-full h-[calc(100%-56px)] bg-white overflow-hidden rounded-[8px]">
        <div className="custom-tab-box px-5 relative">
          <Tabs
            className="font-bold text-[#555]"
            activeKey={activeKey}
            items={items}
            onChange={onChange}
          />
          {activeKey == "2" && (
            <>
              <Input
                placeholder="输入组件名称搜索"
                className="w-[240px] h-[32px] absolute right-[10px] top-[12px]"
                suffix={
                  <SearchOutlined
                    style={{ color: "#999", fontSize: 16 }}
                    onClick={async () => {
                      if (isSearching) {
                        getList();
                      }
                    }}
                  />
                }
                value={searchVal}
                onChange={(e) => {
                  setSearchVal(e.target.value);
                }}
              />
            </>
          )}
        </div>
        {activeKey == "2" && searchRes && searchRes?.length > 0 && (
          <div
            className=" absolute right-2 w-[466px] max-h-[596pa] overflow-y-auto p-[20px]"
            style={{
              boxShadow: "1px 8px 20px #7d8aa433",
              zIndex: 999,
              backgroundColor: "#fff"
            }}
            onMouseLeave={() => setSearchRes([])}
          >
            {searchRes.map((s: IAnalysis) => {
              const path = (s.categories || [])
                .map((c) => c.categoryName)
                .join(" / ");
              return (
                <ListItem
                  key={`list-${s.id}`}
                  title={s.name}
                  path={path}
                  clickListItem={() => {
                    navigator(`/docWriting/component/analyze/${s.id}`);
                    setSearchRes([]);
                  }}
                />
              );
            })}
          </div>
        )}
        <Outlet />
      </div>
    </div>
  );
}

export default Module;
