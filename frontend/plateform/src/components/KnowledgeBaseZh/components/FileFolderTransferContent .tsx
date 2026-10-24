import { SearchOutlined } from "@ant-design/icons";
import { Button, Empty, Input, message, Tree, Spin } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import axios$ from "@root/src/apis";
import { DirectoryTreeProps } from "antd/es/tree";
import { getUrlPrefix } from "@root/src/core/helps";
const prefix = `${getUrlPrefix()}/index`;
const { DirectoryTree } = Tree;
const FILE_LIST_TYPE = 4;
export const FileFolderTransferContent = ({
  drawConfig,
  handleEvent,
  btnLoading,
  kbName,
  fileListType,
  isFaq
}: {
  drawConfig: { type: string; data: any };
  handleEvent: (type: string, data?: any, cb?: (arg?: any) => void) => void;
  btnLoading: boolean;
  fileListType: number;
  kbName: string;
  isFaq?: boolean;
}) => {
  const { id: kbId }: any = useParams();
  const [list, setList] = useState<any>([]);
  const [value, setValue] = useState<any>([-1]);
  const [loading, setLoading] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [expandedKeys, setExpandedKeys] = useState<any>([]);

  const isFolder = (record: any) => {
    return record.isDir;
  };

  const getRecursiveFolderByKb = (params: {
    kbId: string;
    type: number;
    currentId: number;
    currentIds: any[];
    currentFileIds: any[];
  }) => {
    return new Promise((resolve, reject) => {
      axios$
        .post(`${prefix}/folder/recursiveFolderByKb`, params)
        .then((res: any) => {
          const { data, success, errorMsg } = res;
          if (success) {
            resolve(data);
          } else {
            reject(errorMsg || "保存失败，请联系管理员！");
          }
        })
        .catch((e) => {
          console.log("e", e);
          const { message } = e;
          reject(message);
        });
    });
  };

  const createCollectFn = async () => {
    try {
      setLoading(true);
      const curData = Array.isArray(drawConfig.data)
        ? drawConfig.data
        : [drawConfig.data];
      const currentIds: any = [],
        currentFileIds: any = [];
      curData.forEach((item: any) => {
        if (item.pk) return;
        if (fileListType === FILE_LIST_TYPE) {
          if (item.dataType === 1) {
            currentIds.push(item.folderId);
          } else if (item.dataType === 2) {
            currentFileIds.push(item.fileId);
          }
        } else {
          if (isFolder(item)) {
            currentIds.push(item.folderId);
          } else {
            currentFileIds.push(item.fileId);
          }
        }
      });
      const params: any = {
        kbId,
        type: fileListType,
        currentIds,
        currentFileIds
      };
      const res: any = await getRecursiveFolderByKb(params);
      setLoading(false);
      if (Array.isArray(res)) {
        setList(
          fileListType === FILE_LIST_TYPE && drawConfig.data?.dataType === 3
            ? res
            : [{ id: -1, name: "根文件夹", subFolders: res }]
        );
        setValue(
          fileListType === FILE_LIST_TYPE && drawConfig.data?.dataType === 3
            ? []
            : [-1]
        );
      }
    } catch (error) {
      setLoading(false);
      console.log("error", error);
    }
  };

  useEffect(() => {
    createCollectFn();
  }, []);

  const filterList = useMemo(() => {
    if (!searchInput) return list;

    const filterTree = (nodes: any[], search: string): any[] => {
      const a = nodes
        .map((node) => {
          const _name =
            node?.name && typeof node.name === "string" ? node.name : "";
          const match = _name.toLowerCase().includes(search.toLowerCase());
          if (node.subFolders) {
            const filteredChildren = filterTree(node.subFolders, search);
            if (filteredChildren.length > 0 || match) {
              setExpandedKeys((pre: any) => {
                const r = [...new Set([...pre, node.id])];
                return r;
              });
              return { ...node, subFolders: filteredChildren };
            }
          }

          return match ? { ...node, subFolders: [] } : null;
        })
        .filter((node) => node !== null);

      return a;
    };

    return filterTree(list || [], searchInput);
  }, [list, searchInput]);

  const onSelect: DirectoryTreeProps["onSelect"] = (keys, info) => {
    setValue(keys);
    console.log("Trigger Select", keys, info);
  };
  const onExpand: DirectoryTreeProps["onExpand"] = (keys, info) => {
    console.log("Trigger Expand", keys, info);
    setExpandedKeys(keys);
  };

  return (
    <div className="w-full h-full pt-[12px]">
      <div className="h-[calc(100%-30px)]">
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
              <DirectoryTree
                multiple
                defaultExpandAll
                defaultSelectedKeys={[-1]}
                onSelect={onSelect}
                treeData={filterList}
                expandedKeys={expandedKeys}
                onExpand={onExpand}
                defaultExpandParent
                fieldNames={{
                  title: "name",
                  children: "subFolders",
                  key: "id"
                }}
              />
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
            if (!value || value.length === 0) {
              return message.warning("请选择");
            }

            const targetFolderId = value[0] === -1 ? null : value[0];

            let params: any;
            let flag = false;

            const getTarget = (item: any) => {
              const isFoldered = isFolder(item);
              if (fileListType === FILE_LIST_TYPE) {
                if (item.dataType === 3 && !targetFolderId) {
                  flag = true;
                }
                return {
                  targetId:
                    item.dataType === 1
                      ? item.folderId
                      : item.dataType === 2
                      ? item.fileId
                      : item.pk,
                  bizType:
                    item.dataType === 1 ? 8 : item.dataType === 2 ? 10 : 7,
                  kbName
                };
              } else if (isFaq) {
                return {
                  targetId: isFoldered ? item.folderId : item.fileId,
                  bizType: isFoldered ? 9 : 11,
                  kbName
                };
              } else {
                return {
                  targetId: isFoldered ? item.folderId : item.fileId,
                  bizType: isFoldered ? 6 : 4,
                  kbName
                };
              }
            };

            if (Array.isArray(drawConfig.data)) {
              params = {
                targetFolderId,
                target: drawConfig.data.map(getTarget)
              };
            } else {
              if (fileListType === FILE_LIST_TYPE) {
                params = {
                  targetFolderId,
                  targetId:
                    drawConfig.data.dataType === 1
                      ? drawConfig.data.folderId
                      : drawConfig.data.dataType === 2
                      ? drawConfig.data.fileId
                      : drawConfig.data.pk
                };
              } else {
                params = {
                  targetFolderId,
                  targetId: isFolder(drawConfig.data)
                    ? drawConfig.data.folderId
                    : drawConfig.data.fileId
                };
              }
            }
            if (flag) {
              return message.warning("faq不能转移到根目录");
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
export default FileFolderTransferContent;
