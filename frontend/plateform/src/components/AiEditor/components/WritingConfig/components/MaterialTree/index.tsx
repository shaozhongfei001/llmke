/* eslint-disable no-case-declarations */
import { Tree, Button, Tooltip, Empty } from "antd";
import { useEffect, useState } from "react";
import {
  getFileIcon,
  elementTypes
} from "@/components/AiEditor/components/WritingConfig/components/SelectMaterialModal";
import { DeleteOutlined } from "@ant-design/icons";
import "./style.less";

interface Iprops {
  materialTreeData: any;
  materialList: any[];
  materialListRef?: any;
  delBtnShow?: boolean;
  treeHeight?: number;
  onTreeRowDelete?: (list: any[]) => void;
}

export enum usageType {
  both = "both",
  document = "content",
  template = "template"
}

export const fixTreeData = (materialTreeData: any, materialList: any[]) => {
  const { files, kbs } = materialTreeData;
  if (!files.length) {
    return [];
  }
  const mList: any[] = [];
  materialList.forEach((i: any) => {
    const item = mList.find((j: any) => String(j.refId) === String(i.refId));
    if (item) {
      if (String(item.usage) !== String(i.usage)) {
        item.usage = usageType.both;
      }
    } else {
      mList.push({ ...i, refId: Number(i.refId) });
    }
  });
  const _fileList: any[] = [];
  const _folderList: any[] = [];
  let _kbList: any[] = [];

  // 分拆当前选择的文件所涉及的所有文件、文件夹和知识库
  // 分别储存在_fileList、_folderList、_kbList中
  mList.forEach((file: any) => {
    const item = files.find((i: any) => String(i.key) === String(file.refId));
    if (item) {
      _fileList.push({
        ...item,
        ...file,
        isLeaf: true
      });
      if (item.parentId) {
        getFolders(item.parentId, _folderList, _kbList, materialTreeData);
      }
    }
  });

  if (!_kbList.length) {
    _kbList = Array.from(new Set(_fileList.map((i) => String(i.kbId)))).map(
      (i) => kbs.find((j: any) => j.refId === i)
    );
  }

  // 将子文件放入文件夹中
  const folders = [..._folderList].map((i: any) => ({
    ...i,
    isLeaf: false,
    children: _fileList.filter(
      (f: any) => String(f.parentId) === String(i.refId)
    )
  }));

  // 将子文件夹放入父文件夹中
  folders.forEach((i: any) => {
    const { parentId, kbId } = i;
    if (String(parentId) !== String(kbId)) {
      const parentFolder = folders.find(
        (f: any) => String(f.refId) === String(parentId)
      );
      parentFolder.children.push(i);
    }
  });

  const _folders = folders.filter((i) => String(i.parentId) === String(i.kbId));

  const treeList = [..._kbList].map((k: any) => {
    const fn = (f: any) => String(f.parentId) === String(k.refId);
    const childFolders = _folders.filter(fn);
    const childFiles = _fileList.filter(fn);
    return {
      ...k,
      isLeaf: false,
      elementType: elementTypes.KB,
      children: [...childFiles, ...childFolders]
    };
  });

  // console.log("files:", _fileList);
  // console.log("folders:", _folderList);
  // console.log("kbs:", _kbList);
  // console.log("mList:", mList);
  return addFieldImmutable(
    treeList
      .map((i: any) => calculateLeafCountImmutable(i))
      .filter((i: any) => i.children.length),
    0
  );
};

const addFieldImmutable = (treeData: any, depth: number) => {
  return (treeData || []).map((node: any) => ({
    ...node,
    depth: depth + 1,
    children: node.children ? addFieldImmutable(node.children, depth + 1) : []
  }));
};

const getFolders = (
  pId: number,
  folderList: any[],
  kbList: any[],
  materialTreeData: any
) => {
  const { folders, kbs } = materialTreeData;
  const folder = folders.find((i: any) => i.refId === pId);
  const kb = kbs.find((i: any) => i.refId === pId);

  if (kb && !kbList.some((i: any) => i.key === kb.key)) {
    kbList.push({ ...kb });
  }

  if (folder && !folderList.some((i: any) => i.key === folder.key)) {
    folderList.push({ ...folder });
    if (folder.parentId) {
      getFolders(folder.parentId, folderList, kbList, materialTreeData);
    }
  }
};

const calculateLeafCountImmutable = (node: any) => {
  const { elementType } = node;
  if (elementType === elementTypes.FILE) {
    return { ...node };
  }

  const newNode = { ...node, children: [] };

  if (!node.children || node.children.length === 0) {
    newNode.leafCount = 0;
    newNode.leafKeys = [];
    return newNode;
  }

  let total = 0;
  let leafKeys: number[] = [];
  for (const child of node.children) {
    const childNode = calculateLeafCountImmutable(child);
    newNode.children.push(childNode);
    total +=
      childNode.elementType === elementTypes.FILE ? 1 : childNode.leafCount;

    leafKeys =
      childNode.elementType === elementTypes.FILE
        ? [...leafKeys, childNode.key]
        : leafKeys.concat(childNode.leafKeys || []);
  }
  newNode.leafCount = total;
  newNode.leafKeys = leafKeys;
  return newNode;
};

export const MaterialTree = (props: Iprops) => {
  const {
    materialTreeData,
    materialList,
    materialListRef,
    delBtnShow = true,
    treeHeight = 330,
    onTreeRowDelete
  } = props;
  const [treeData, setTreeData] = useState<any[]>([]);

  const delTreeRow = (item: any) => () => {
    console.log("delete:", item);
    const fileKeys = collectLeafKeys(item);
    const newList = [
      ...materialList.filter((i: any) => !fileKeys.includes(Number(i.refId)))
    ];
    // console.log(fileKeys, materialList, newList);
    if (materialListRef) {
      materialListRef.current = [...newList];
    }

    const _treeData = deleteSubtree(treeData, item.key);
    const _data = _treeData.map((i: any) => calculateLeafCountImmutable(i));
    setTreeData([..._data]);
  };

  const deleteSubtree = (tree: any[], key: number) => {
    return tree.reduce((acc, node) => {
      if (node.key === key) {
        // 跳过目标节点
        return acc;
      }
      if (node.children) {
        node.children = deleteSubtree(node.children, key);
      }
      acc.push(node);
      return acc;
    }, []);
  };

  const collectLeafKeys = (node: any) => {
    const { children, elementType, refId } = node;
    return elementType === elementTypes.FILE
      ? [refId]
      : children.flatMap((child: any) => collectLeafKeys(child));
  };

  const getIcon = (item: any) => {
    const { elementType, fileName, name } = item;
    const _fileName = fileName || name || "";
    const type =
      _fileName && elementType === elementTypes.FILE
        ? getFileSuffix(_fileName)
        : elementType === elementTypes.FOLDER
          ? "folder"
          : "kb";
    return <span className="relative top-[2px]">{getFileIcon(type)}</span>;
  };

  const getFileSuffix = (fileName: string) => {
    const list = fileName.split(".");
    return list.length > 1 ? list[list.length - 1] : "";
  };

  useEffect(() => {
    if (materialList && materialList.length === 0) {
      setTreeData([]);
      return;
    }
    if (
      materialList &&
      materialList.length &&
      materialTreeData &&
      materialTreeData.files
    ) {
      setTreeData(fixTreeData(materialTreeData, materialList));
    }
  }, [materialTreeData, materialList]);

  useEffect(() => {
    onTreeRowDelete && onTreeRowDelete([...treeData]);
  }, [treeData]);

  return (
    <div className="-mx-3">
      <div className={`z-50 w-full material-tree`}>
        {treeData && treeData.length ? (
          <Tree
            treeData={treeData}
            selectable={false}
            height={treeHeight}
            titleRender={(node) => (
              <div className="flex min-h-8">
                <div className="flex-1 min-w-0 flex select-none overflow-hidden h-8 leading-8">
                  {getIcon(node)}
                  <span
                    title={node.name}
                    className="text-ellipsis overflow-hidden"
                  >
                    {node.name}
                  </span>
                  {node.elementType !== elementTypes.FILE ? (
                    <span className="text-[#888] text-xs leading-8">
                      （{node.leafCount}）
                    </span>
                  ) : null}
                </div>
                {delBtnShow && (
                  <div className="del-btn-wrap">
                    <Tooltip
                      placement="top"
                      color="white"
                      title={
                        <span className="text-[#2a2a2a]">
                          删除后写作时不再能关联素材
                        </span>
                      }
                    >
                      <Button
                        type="link"
                        onClick={delTreeRow(node)}
                        icon={
                          <DeleteOutlined className="text-[#888] hover:text-[#FF4D4F]" />
                        }
                      />
                    </Tooltip>
                  </div>
                )}
              </div>
            )}
          />
        ) : (
          <Empty className="my-2" />
        )}
        {/* {JSON.stringify(treeData)} */}
        {/* <hr /> */}
        {/* {JSON.stringify(mList)} */}
      </div>
    </div>
  );
};

export default MaterialTree;
