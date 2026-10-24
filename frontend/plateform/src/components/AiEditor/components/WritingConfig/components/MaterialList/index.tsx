import ItemName from "../ItemName";
import { DeleteOutlined } from "@ant-design/icons";
import { Empty, Tooltip } from "antd";

interface Iprops {
  hasBoder: boolean;
  listData: any[];
  setListData?: React.Dispatch<React.SetStateAction<any[]>>;
  initData?: any[];
  showDel?: boolean;
  onMouseEnter?: any;
  onMouseLeave?: any;
  showRight?: boolean;
}

const getUsageText = (usage: string) => {
  switch (usage) {
    case "content":
      return "切片检索";
    case "both":
      return "全部来源";
    case "template":
      return "全文引用";
    default:
      return;
  }
};

export const MaterialList = ({
  showRight = true,
  hasBoder = false,
  listData = [],
  setListData,
  initData,
  showDel = true,
  onMouseEnter = () => {},
  onMouseLeave = () => {}
}: Iprops) => {
  const handleDel = (clickItem: any) => {
    setListData &&
      setListData((_list) => {
        return _list.filter(
          (item) =>
            item.refEntityType + "-" + item.refId !==
            clickItem.refEntityType + "-" + clickItem.refId
        );
      });
  };

  return (
    <div
      className="w-full h-full overflow-y-auto overflow-x-hidden min-w-[300px]"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {!listData.length ? (
        <Empty />
      ) : (
        listData.map((i) => (
          <div
            className="flex flex-col"
            key={i.refEntityType + "-" + i.refId}
            style={{
              padding: hasBoder ? "" : "6px",
              marginTop: hasBoder ? "12px" : ""
            }}
          >
            <div
              className="w-full flex justify-between items-center text-[14px] text-[#2a2a2a] box-border"
              style={{
                border: hasBoder ? "1px solid #eee" : "",
                paddingLeft: hasBoder ? "8px" : "",
                height: hasBoder ? "32px" : ""
              }}
            >
              <div
                style={{
                  width: showRight ? "calc(100% - 150px)" : "100%"
                }}
              >
                <ItemName item={i} fontSize="14px" />
              </div>
              {showRight && (
                <div className="w-[100px] flex items-center">
                  <div className="text-[#888] px-1 bg-[#f2f2f2] mr-[16px] flex align-middle h-[20px]">
                    {getUsageText(i.usage)}
                  </div>
                  <>
                    {showDel && (
                      <Tooltip
                        title={<span className="text-[#2a2a2a]">删除</span>}
                        color="white"
                      >
                        <DeleteOutlined
                          style={{
                            cursor: "pointer"
                          }}
                          onClick={(_) => handleDel(i)}
                        />
                      </Tooltip>
                    )}
                  </>
                </div>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
};

export default MaterialList;
