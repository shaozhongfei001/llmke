import {
  CaretDownOutlined,
  CaretRightOutlined,
  CheckCircleFilled,
  SearchOutlined
} from "@ant-design/icons";
import { useMyHttpClient } from "@root/src/apis/api/index.js";
import { Api } from "@root/src/apis/api/Api";
import { Button, Empty, Input, message, Radio, Spin } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
export const TransferContent = ({
  drawConfig,
  handleEvent,
  btnLoading,
  isFaq,
  fileListType
}: {
  drawConfig: { type: string; data: any };
  handleEvent: (type: string, data?: any, cb?: (arg?: any) => void) => void;
  btnLoading: boolean;
  isFaq: boolean;
  fileListType: number;
}) => {
  const api = new Api(useMyHttpClient());
  const { id: kbId }: any = useParams();
  const [list, setList] = useState<any>([]);
  const [value, setValue] = useState("");
  const curItem: any = useRef(null);
  const [loading, setLoading] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const isMoreFiles = (record: any) => {
    return record.kbFiles && record.kbFiles.length > 1;
  };
  const createCollectFn = async () => {
    try {
      setLoading(true);
      const res: any = await api.collectList({
        kbId,
        fileListType: isFaq ? 2 : 1
      });
      setLoading(false);
      if (res.success) {
        if (Array.isArray(drawConfig.data)) {
          setList(res.data || []);
        } else {
          setList(
            (res.data || []).filter((item: any) => {
              return item.groupId !== drawConfig.data.groupId;
            })
          );
        }
      }
    } catch (error) {
      setLoading(false);
      console.log("error", error);
    }
  };

  const getByGroupIdFn = async (groupId: string) => {
    try {
      const res: any = await api.getByGroupId({ kbId, groupId, fileListType });
      if (res.success) {
        setList((pre: any) => {
          const item = pre.find((item: any) => item.groupId === groupId);
          item.loading = false;
          item.children = res.data;
          return [...pre];
        });
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  useEffect(() => {
    createCollectFn();
  }, []);

  const filterList = useMemo(() => {
    if (!searchInput) return list;
    return list.filter((item: any) => {
      const _searchInput =
        searchInput && typeof searchInput === "string" ? searchInput : "";
      const _parentFileName =
        item?.parentFileName && typeof item.parentFileName === "string"
          ? item.parentFileName
          : "";
      return _parentFileName.toLowerCase().includes(_searchInput.toLowerCase());
    });
  }, [list, searchInput]);

  return (
    <div className="w-full h-full pt-[12px]">
      <div className="h-[calc(100%-80px)]">
        <div className="box-border border-solid border-[1px] border-[#D9D9D9] h-full overflow-y-auto rounded-[4px] p-[16px]">
          <Input
            placeholder="搜索归集名称"
            suffix={<SearchOutlined onClick={() => {}} />}
            value={searchInput}
            onChange={(e: any) => setSearchInput(e?.target?.value || "")}
            className="mb-[10px]"
          />
          {loading ? (
            <div className="py-[50px] flex justify-center w-full">
              <Spin tip="加载中……" size="large" className="bg-transparent" />
            </div>
          ) : (
            <div className="h-[calc(100%-56px)] overflow-y-auto overflow-x-hidden">
              {filterList.length ? (
                filterList.map((item: any) => {
                  return (
                    <ItemCom
                      item={item}
                      value={value}
                      onCLick={(e: any) => {
                        curItem.current = e;
                        setValue(e ? e.groupId : e);
                      }}
                      onOpenChange={(item: any, open: boolean) => {
                        if (!open) {
                          item.open = false;
                          setList([...list]);
                          return;
                        }
                        const curItem = list.find(
                          (v: any) => v.groupId === item.groupId
                        );
                        if (curItem.children) {
                          item.open = true;
                        } else {
                          item.loading = true;
                          item.open = true;
                          getByGroupIdFn(item.groupId);
                        }
                        setList([...list]);
                      }}
                    />
                  );
                })
              ) : (
                <Empty />
              )}
            </div>
          )}
        </div>
      </div>
      <div className="h-[20px] w-[5px]"></div>
      <div
        className="flex justify-end h-[38px] pt-[16px]"
        style={{ borderTop: "1px solid #EBEBEB" }}
      >
        <Button
          style={{
            border: "1px solid #EBEBEB",
            color: "#555555",
            marginRight: "16px"
          }}
          onClick={() => {
            handleEvent("closeDrawer");
          }}
        >
          取消
        </Button>
        <Button
          style={{
            border: "none",
            color: "#fff",
            background:
              "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
          }}
          loading={btnLoading}
          onClick={() => {
            if (!value) return message.warning("请选择");
            const fileIds: any = [],
              srcGroupIds: any = [];
            const data = Array.isArray(drawConfig.data)
              ? drawConfig.data
              : [drawConfig.data];

            data.forEach((item: any) => {
              if (isMoreFiles(item)) {
                srcGroupIds.push(item.groupId);
              } else {
                fileIds.push(item.id);
              }
            });
            Array.isArray(drawConfig.data)
              ? drawConfig.data.map((item: any) => item.id)
              : [drawConfig.data.id];

            const params: any = {
              kbId,
              groupId: value,
              parentFileName: curItem.current.parentFileName
            };

            if (fileIds.length) {
              params.fileIds = fileIds;
            }
            if (srcGroupIds.length) {
              params.srcGroupIds = srcGroupIds;
            }
            handleEvent("save:transfer", params);
          }}
        >
          转移到此
        </Button>
      </div>
    </div>
  );
};
export default TransferContent;

const ItemCom = ({
  item,
  value,
  onCLick,
  onOpenChange
}: {
  item: any;
  value: string;
  onCLick: (arg: string) => void;
  onOpenChange: (arg: any, open: boolean) => void;
}) => {
  const contentStyle: React.CSSProperties = {
    padding: 50,
    background: "rgba(0, 0, 0, 0.05)",
    borderRadius: 4
  };
  const content = <div style={contentStyle} />;
  return (
    <div
      key={item.groupId}
      className={`${
        item.groupId === value ? "bg-[#F3F6FF]" : "bg-[#ffffff]"
      } items-center p-[16px] rounded-[4px]`}
    >
      <div className="flex">
        {item.groupId === value ? (
          <CheckCircleFilled
            onClick={() => {
              onCLick("");
            }}
            className="text-[20px] cursor-pointer text-primary-color"
          />
        ) : (
          <div
            className="w-[18px] h-[18px] border-solid border-[1px] border-[rgba(0,0,0,.15)] rounded-full cursor-pointer"
            onClick={(e: any) => {
              onCLick(item);
            }}
          ></div>
        )}

        {item.open ? (
          <CaretDownOutlined
            className="flex mx-[12px] text-primary-color cursor-pointer"
            onClick={() => onOpenChange(item, false)}
          />
        ) : (
          <CaretRightOutlined
            className="flex mx-[12px] text-text-color2 cursor-pointer"
            onClick={() => onOpenChange(item, true)}
          />
        )}

        <div
          className={`text-[14px] font-[500] ${
            item.open ? "text-primary-color" : "text-text-color1"
          }`}
        >
          {(item.parentFileName || "").split(".")[0]}
        </div>
      </div>
      {item.loading && (
        <div className="mt-[20px] flex justify-center">
          <Spin tip="加载中……" size="large" className="bg-transparent">
            {content}
          </Spin>
        </div>
      )}
      {item.open && !item.loading && (
        <div
          style={{
            borderTop: "1px solid #DAE0F3",
            marginTop: "10px",
            marginLeft: "60px",
            padding: "10px 0"
          }}
        >
          {item.children ? (
            item.children.map((child: any) => {
              return (
                <div
                  key={child.id || child.groupId}
                  className="text-[14px] text-text-color1 my-[8px] w-[391] text-ellipsis line-clamp-1"
                >
                  {child.fileName}
                </div>
              );
            })
          ) : (
            <div key={item.id} className="flex justify-center mt-[20px]">
              <Empty />
            </div>
          )}
        </div>
      )}
    </div>
  );
};
