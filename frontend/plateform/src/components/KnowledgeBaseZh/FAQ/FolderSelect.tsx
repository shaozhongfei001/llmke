import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";
import { Tree } from "antd";
import { DirectoryTreeProps } from "antd/es/tree";
import { useEffect, useState } from "react";
const { DirectoryTree } = Tree;
const prefix = `${getUrlPrefix()}/index`;

const FolderSelect = ({ kbId, setValue }: { kbId: string; setValue: any }) => {
  const [expandedKeys, setExpandedKeys] = useState<any>([]);
  const [loading, setLoading] = useState(false);
  const [list, setList] = useState<any>([]);
  const onSelect: DirectoryTreeProps["onSelect"] = (keys, info) => {
    setValue(info.node);
    console.log("Trigger Select", keys, info);
  };
  const onExpand: DirectoryTreeProps["onExpand"] = (keys, info) => {
    console.log("Trigger Expand", keys, info);
    setExpandedKeys(keys);
  };

  const getRecursiveFolderByKb = (params: { kbId: string; type: number }) => {
    return new Promise((resolve, reject) => {
      axios$
        .get(`${prefix}/folder/file/list?kbId=${kbId}`)
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
      const params: any = {
        kbId
      };
      const res: any = await getRecursiveFolderByKb(params);
      setLoading(false);
      if (Array.isArray(res)) {
        const setIdAsFolderId = (nodes: any[]) => {
          return nodes.map((node) => {
            const newNode = { ...node, id: node.fileId || node.folderId };
            if (Array.isArray(newNode.subs) && newNode.subs.length > 0) {
              newNode.subs = setIdAsFolderId(newNode.subs);
            }
            return newNode;
          });
        };
        const resWithId = setIdAsFolderId(res);
        setList(resWithId);
      }
    } catch (error) {
      setLoading(false);
      console.log("error", error);
    }
  };

  useEffect(() => {
    createCollectFn();
  }, []);
  return (
    <DirectoryTree
      multiple
      defaultExpandAll
      defaultSelectedKeys={[-1]}
      onSelect={onSelect}
      treeData={list}
      expandedKeys={expandedKeys}
      onExpand={onExpand}
      defaultExpandParent
      fieldNames={{
        title: "name",
        children: "subs",
        key: "id"
      }}
    />
  );
};

export default FolderSelect;
