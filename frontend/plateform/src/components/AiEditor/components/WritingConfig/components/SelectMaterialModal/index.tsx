/* eslint-disable no-case-declarations */
import { Button, Input, Modal, Tabs, Tree, Checkbox, Empty, Spin } from "antd";
import type { TreeProps, CheckboxProps } from "antd";
import { useEffect, useMemo, useState, useRef } from "react";
import "./style.less";
import { PrimaryBtn } from "@/pages/HomePage/Writing/common/components/PrimaryBtn";
import { UploadOutlined } from "@ant-design/icons";
import { MaterialItemWithCustomId } from "../type";
import { getCecAllFileList } from "@/components/KnowledgeBaseZh/common/faqService";
import { SearchOutlined } from "@ant-design/icons";
import { ANALYSIS_STATUS } from "@/const/knowledgebase";
import {
  FileCsvIcon,
  FileKbIcon,
  FileDocIcon,
  FileIcon,
  FolderIcon,
  FilePdfIcon,
  FilePicIcon,
  FilePptIcon,
  FileTxtIcon,
  FileHtmIcon,
  FileXlsIcon,
  FileZipIcon,
  DbTableIcon,
  DbMongoIcon,
  DbMysqlIcon
} from "@/components/Icon";
import defaultDbIcon from "@/assets/svg/db.svg";

const dbTypes: any = {
  0: <DbMysqlIcon className="mr-2" />,
  1: <DbMongoIcon className="mr-2" />
};

import { useServices } from "../../service";
// import { mockData } from "./mockData";
const mockData = false;

export const getFileIcon = (fileType: string, node?: any) => {
  const _type = fileType.toLocaleLowerCase();
  switch (_type) {
    case "kb":
      return <FileKbIcon className="mr-2" />;
    case "folder":
      return <FolderIcon className="mr-2" />;
    case "pdf":
      return <FilePdfIcon className="mr-2" />;
    case "doc":
    case "docx":
      return <FileDocIcon className="mr-2" />;
    case "txt":
      return <FileTxtIcon className="mr-2" />;
    case "ppt":
    case "pptx":
      return <FilePptIcon className="mr-2" />;
    case "xls":
    case "xlsx":
      return <FileXlsIcon className="mr-2" />;
    case "csv":
      return <FileCsvIcon className="mr-2" />;
    case "png":
    case "jpg":
    case "jpeg":
      return <FilePicIcon className="mr-2" />;
    case "htm":
    case "html":
      return <FileHtmIcon className="mr-2" />;
    case "zip":
    case "rar":
      return <FileZipIcon className="mr-2" />;
    case "db":
      if (node && node.iconType) {
        const { iconType, type } = node;
        switch (iconType) {
          case "table":
            return <DbTableIcon className="mr-2" />;
          case "db":
            return (
              dbTypes[type] || (
                <img src={defaultDbIcon} className="w-6 p-1 mr-2" />
              )
            );
        }
      }
      break;
    default:
      return <FileIcon className="mr-2" />;
  }
};

export enum writingTypes {
  Segmented = "segmented",
  Full = "full"
}
enum sourceTypes {
  knowledge_base = "knowledge_base",
  database = "database"
}
interface Iprops {
  sourceType?: sourceTypes;
  openSelectModal: boolean;
  writingType?: writingTypes;
  initSelectedArr?: any[];
  isMaterialApisFetching?: boolean;
  initKbList?: any[];
  setOpenSelectModal: (sta: boolean) => void;
  getAllMertail: (
    item: MaterialItemWithCustomId[],
    sourceType: sourceTypes
  ) => any;
  getKbListCb?: (kbList: any[]) => void;
  getAllFilesCb?: (materialTreeData: any) => void;
  setIsMaterialApisFetching?: (sta: boolean) => void;
}

enum tabTypes {
  ContentSource = "contentSource",
  SampleText = "sampleText"
}

export enum elementTypes {
  KB = 1,
  FOLDER = 2,
  FILE = 3
}

const tabItems = [
  {
    key: tabTypes.ContentSource,
    label: "切片检索"
  },
  {
    key: tabTypes.SampleText,
    label: "全文引用"
  }
];

const initialPage = {
  pageNo: 1,
  pageSize: 9999
};

const params = {
  scope: "own",
  withFolder: true
};

const platform = "intelbrain-dw";

const originDataType = {
  allFiles: [],
  kbs: [],
  folders: [],
  files: [],
  type: tabTypes.ContentSource
};

type keysObjType = {
  [tabTypes.ContentSource]: React.Key[];
  [tabTypes.SampleText]: React.Key[];
};

const initKeysObj: keysObjType = {
  [tabTypes.ContentSource]: [],
  [tabTypes.SampleText]: []
};

enum usageTypes {
  TEMPLATE = "template",
  CONTENT = "content",
  BOTH = "both"
}

export const SelectMaterialModal = ({
  openSelectModal,
  writingType = writingTypes.Full,
  initSelectedArr = [],
  isMaterialApisFetching = false,
  sourceType = sourceTypes.knowledge_base,
  initKbList,
  setOpenSelectModal,
  getAllMertail,
  getKbListCb,
  getAllFilesCb,
  setIsMaterialApisFetching
}: Iprops) => {
  const { getKnowledgeList, getShareList } = useServices(platform);
  const [activeTab, setActiveTab] = useState<tabTypes>(tabTypes.ContentSource);

  const [originData, setOriginData] = useState<any>({ ...originDataType });
  // const [treeData, setTreeData] = useState<any[]>([]);
  const [kbList, setKbList] = useState<any[]>([]);
  const [expandedKeys, setExpandedKeys] = useState<keysObjType>({
    ...initKeysObj
  });
  const [checkedKeys, setCheckedKeys] = useState<keysObjType>({
    ...initKeysObj
  });
  const [allCheckedKeys, setAllCheckedKeys] = useState<keysObjType>({
    ...initKeysObj
  });
  const [autoExpandParent, setAutoExpandParent] = useState<boolean>(true);
  const [filterName, setFilterName] = useState<string>("");
  const [allChecked, setAllChecked] = useState<boolean>(false);
  const [filterListShow, setFilterListShow] = useState<boolean>(false);
  const [filterList, setFilterList] = useState<any[]>([]);
  const filterRef = useRef<any>(null);

  // 详情页tab切换
  const handleTabChange = (key: string) => {
    if (
      key !== activeTab &&
      (tabTypes.ContentSource === key || tabTypes.SampleText === key)
    ) {
      setActiveTab(key);
      const _files =
        key === tabTypes.ContentSource
          ? [...originData.allFiles].filter((i: any) => !!i.chunking)
          : [...originData.allFiles];
      setOriginData({
        ...originData,
        // files: _files.filter((i: any) => i.name.includes(filterName)),
        files: _files,
        type: activeTab
      });
      filterListOnChange(undefined, key);
    }
  };

  const goToUpload = () => {
    window.open(location.origin + "/docWriting/resource");
  };

  // 取消弹窗
  const handleCancelModal = () => {
    setOpenSelectModal(false);
    setActiveTab(tabTypes.ContentSource);
  };

  // 点击确定，收集所有选中数据，处理字段为下一个组件需要的字段
  const handleConfirmSelect = () => {
    const _allSelectedArr: any = [];
    const { allFiles } = originData;
    const { contentSource, sampleText } = allCheckedKeys;
    const _kbs: number[] = [];

    contentSource.forEach((key: React.Key) => {
      const item = allFiles.find((i: any) => i.key === key);
      if (item) {
        const { key, name, kbId, refId, sourceType } = item;
        if (!_kbs.some((i: number) => i === kbId)) {
          _kbs.push(kbId);
        }
        _allSelectedArr.push({
          customId: key,
          refId,
          refEntityType: "document",
          refName: name,
          usage: usageTypes.CONTENT,
          sourceType
        });
      }
    });

    sampleText.forEach((key: React.Key) => {
      const item = allFiles.find((i: any) => i.key === key);
      if (item) {
        const { key, name, kbId, refId, sourceType } = item;
        if (!_kbs.some((i: number) => i === kbId)) {
          _kbs.push(kbId);
        }
        _allSelectedArr.push({
          customId: key,
          refId,
          refEntityType: "document",
          refName: name,
          usage: usageTypes.TEMPLATE,
          sourceType
        });
      }
    });

    getAllMertail && getAllMertail(_allSelectedArr, sourceTypes.knowledge_base);
    setFilterName("");
    setOpenSelectModal(false);
  };

  const saveOriginData = (list: any[]) => {
    const allFiles = list
      .filter(
        (i: any) =>
          i.elementType === elementTypes.FILE &&
          i.status === ANALYSIS_STATUS.SUCCESS
      )
      .map((i: any) => {
        const {
          id,
          fileName,
          chunking,
          elementType,
          filePath,
          convertedFilePath,
          kbId,
          folderId,
          status
        } = i;
        return {
          // key: id,
          key: `${id}`,
          name: fileName,
          chunking,
          elementType,
          filePath,
          convertedFilePath,
          kbId,
          parentId: folderId || kbId,
          status,
          title: fileName,
          refId: id,
          sourceType
        };
      });
    // getAllFilesCb && getAllFilesCb([...allFiles]);
    const files =
      activeTab === tabTypes.ContentSource
        ? [...allFiles].filter((i: any) => !!i.chunking)
        : [...allFiles];

    const folders = list
      .filter((i: any) => i.elementType === elementTypes.FOLDER)
      .map((i: any) => {
        const { id, folderName, elementType, parentId, kbId } = i;
        return {
          // key: id,
          key: `folder-${id}`,
          name: folderName,
          elementType,
          kbId,
          parentId: parentId || kbId,
          title: folderName,
          refId: id
        };
      });

    const kbs = list
      .filter((i: any) => i.elementType === elementTypes.KB)
      .map((i: any) => {
        return {
          // key: i.id,
          key: `kb-${i.id}`,
          name: i.kbName,
          title: i.kbName,
          refId: i.id
        };
      });

    setOriginData({
      ...originData,
      allFiles,
      kbs,
      folders,
      files
    });
    getAllFilesCb &&
      getAllFilesCb({
        kbs: [...kbs],
        folders: [...folders],
        files: [...allFiles]
      });
  };

  const fixFolderStatistics = (list: any[], arr: any[] = []) => {
    list.forEach((item: any) => {
      const { children, name, elementType } = item;
      if (elementType === elementTypes.FILE) {
        arr.push(item);
      } else {
        arr.push({
          ...item,
          children: children.length ? fixFolderStatistics(children) : []
        });
      }
    });

    return arr;
  };

  const calculateLeafCountImmutable = (node: any) => {
    const { elementType } = node;
    if (elementType === elementTypes.FILE) {
      return { ...node };
    }

    const newNode = { ...node, children: [] };

    if (!node.children || node.children.length === 0) {
      newNode.leafCount = 0;
      newNode.leafCheckedCount = 0;
      return newNode;
    }

    let leafCount = 0;
    let leafCheckedCount = 0;
    for (const child of node.children) {
      const childNode = calculateLeafCountImmutable(child);
      newNode.children.push(childNode);
      leafCount +=
        childNode.elementType === elementTypes.FILE ? 1 : childNode.leafCount;

      leafCheckedCount +=
        childNode.elementType === elementTypes.FILE
          ? checkedKeys[activeTab].includes(childNode.key)
            ? 1
            : 0
          : childNode.leafCheckedCount;
    }
    newNode.leafCount = leafCount;
    newNode.leafCheckedCount = leafCheckedCount;
    return newNode;
  };

  const fixTreeData = (originData: any) => {
    const { folders, kbs, files } = originData;
    const folderList = [...folders].map((i: any) => ({
      ...i,
      children: files.filter((f: any) => String(f.parentId) === String(i.refId))
    }));

    folderList.forEach((i: any) => {
      const { parentId, kbId } = i;
      if (parentId !== kbId) {
        const parentFolder = folderList.find(
          (f: any) => String(f.refId) === String(parentId)
        );
        if (parentFolder) {
          parentFolder.children.push(i);
        }
      }
    });

    const kbIds = kbs.map((i: any) => String(i.refId));

    const _folderList = (fixFolderStatistics(folderList) || []).filter(
      (i) => i.parentId === i.kbId
    );
    const _files = files.filter((f: any) => kbIds.includes(String(f.parentId)));
    // console.log("files:", _files);
    // console.log("folders:", _folderList);
    // console.log("kbs:", kbs);
    const _treeData = [...kbs].map((k: any) => {
      const { refId } = k;
      const childFolders = _folderList.filter(
        (f: any) => String(f.parentId) === String(refId)
      );
      const childFiles = _files.filter(
        (f: any) => String(f.parentId) === String(refId)
      );
      return {
        ...k,
        children: [...childFiles, ...childFolders]
      };
    });
    const _data: any[] = _treeData
      .map((i: any) => calculateLeafCountImmutable(i))
      .filter((i: any) => !!i.leafCount);
    return [...(_data || []).filter((i: any) => i.children.length)];
  };

  const getFileSuffix = (fileName: string) => {
    const list = fileName.split(".");
    return list.length > 1 ? list[list.length - 1] : "";
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

  const fetchKbList = async () => {
    setIsMaterialApisFetching && setIsMaterialApisFetching(true);
    try {
      const list = await Promise.all([
        getShareList.mutateAsync(initialPage),
        getKnowledgeList.mutateAsync(initialPage)
      ]);
      const _kbList: any[] = [];
      list.forEach((i: any) => {
        if (i && !i.error) {
          const { records } = i;
          if (records && records.length) {
            records.forEach((r: any) => {
              if (!_kbList.some((j: any) => j.kbId === r.id)) {
                _kbList.push({
                  kbId: r.id,
                  kbName: r.kbName
                });
              }
            });
          }
        }
      });

      getKbListCb && getKbListCb([..._kbList]);
      setKbList([..._kbList]);
      if (!_kbList.length && isMaterialApisFetching) {
        setIsMaterialApisFetching && setIsMaterialApisFetching(false);
      }
    } catch (e) {
      if (isMaterialApisFetching) {
        setIsMaterialApisFetching && setIsMaterialApisFetching(false);
      }
    }
  };

  const getTreeData = () => {
    if (kbList && kbList.length && !mockData) {
      getCecAllFileList({
        ...params,
        kbIds: kbList.map((i: any) => i.kbId).join(",")
      })
        .then((res) => {
          const _res = res || [];
          saveOriginData(_res);
        })
        .finally(() => {
          if (isMaterialApisFetching) {
            setIsMaterialApisFetching && setIsMaterialApisFetching(false);
          }
        });
    }
  };

  const onTreeExpand: TreeProps["onExpand"] = (expandedKeysValue) => {
    setExpandedKeys({
      ...expandedKeys,
      [activeTab]: expandedKeysValue
    });
    setAutoExpandParent(false);
  };

  const onTreeCheck: TreeProps["onCheck"] = (checkedKeysValue: any) => {
    // console.log({
    //   ...checkedKeys,
    //   [activeTab]: checkedKeysValue as React.Key[]
    // });
    fixCheckedFiles(checkedKeysValue);
  };

  const fixCheckedFiles = (ids: any) => {
    setCheckedKeys({
      ...checkedKeys,
      [activeTab]: ids as React.Key[]
    });
    const filteredKeysSet = new Set(getAllKeys(filterTreeData));
    const newAllCheckedKeys = Array.from(
      new Set([
        ...allCheckedKeys[activeTab].filter((key) => !filteredKeysSet.has(key)),
        ...ids
      ])
    );

    setAllCheckedKeys({
      ...allCheckedKeys,
      [activeTab]: newAllCheckedKeys
    });
  };

  const setExpandKbs = (ids?: any[]) => {
    const expandIds = ids || kbList.map((i: any) => `kb-${i.kbId}`);
    setExpandedKeys({
      [tabTypes.ContentSource]: [...expandIds],
      [tabTypes.SampleText]: [...expandIds]
    });
  };

  const filterNameKeyDownHandler = (e: any) => {
    const { key, keyCode } = e;
    if (key === "Enter" && keyCode === 13) {
      filterHandler();
    }
  };

  const filterHandler = () => {
    // console.log(filterRef.current);
    const { input } = filterRef.current;
    if (input) {
      const val = input.value.trim();
      setFilterName(val);
      // 20250819为演示改为筛选树数据注释掉下面两行
      // filterListOnChange(val);
      // !filterListShow && setFilterListShow(true);
    }
    // const _files =
    //   activeTab === tabTypes.ContentSource
    //     ? [...originData.allFiles].filter((i: any) => !!i.chunking)
    //     : [...originData.allFiles];

    // setOriginData({
    //   ...originData,
    //   files: filterName
    //     ? [..._files].filter((i: any) => i.name.includes(filterName))
    //     : [..._files]
    // });
  };

  const filterListConfirm = () => {
    const checkedFileIds = filterList
      .filter((i: any) => i.checked === true)
      .map((i: any) => i.key);
    // console.log(checkedFileIds, checkedKeys[activeTab]);
    const unCheckFileIds = filterList
      .filter((i: any) => i.checked === false)
      .map((i: any) => i.key);

    setCheckedKeys({
      ...checkedKeys,
      [activeTab]: [
        ...Array.from(new Set([...checkedFileIds, ...checkedKeys[activeTab]]))
      ].filter((i: number) => !unCheckFileIds.includes(i))
    });
    setFilterListShow(false);
  };

  const filterListOnChange = (fName?: string, tabType?: tabTypes) => {
    const _filterName = fName || fName === "" ? fName : filterName;
    const _activeTab = tabType || activeTab;
    const { allFiles, folders, kbs } = originData;
    const _files =
      _activeTab === tabTypes.ContentSource
        ? [...allFiles].filter((i: any) => !!i.chunking)
        : [...allFiles];

    // const _folders = folders.filter((i: any) =>
    //   _files.some((j: any) => j.parentId === i.key)
    // );
    // const _kbs = kbs.filter(
    //   (i: any) =>
    //     _files.some((j: any) => j.parentId === i.key) ||
    //     _folders.some((j: any) => j.parentId === i.key)
    // );

    // const _list = [..._kbs, ..._folders, ..._files]
    const _list = [..._files]
      .filter((i: any) => i.name.includes(_filterName))
      .map((i: any) => ({
        ...i,
        checked: checkedKeys[_activeTab].includes(i.key)
      }));

    setFilterList(_list);
  };

  const allCheckedOnChange: CheckboxProps["onChange"] = (e) => {
    const isChecked = e.target.checked;
    const { files, folders, kbs } = originData;
    const ids = isChecked
      ? [
          ...files.map((i: any) => i.key),
          ...folders.map((i: any) => i.key),
          ...kbs.map((i: any) => i.key)
        ]
      : [];
    fixCheckedFiles(ids);
    setAllChecked(e.target.checked);
  };

  const initCheckedFiles = () => {
    const contentIds = initSelectedArr
      .filter((i: any) =>
        [usageTypes.CONTENT, usageTypes.BOTH].includes(i.usage)
      )
      .map((i: any) => String(i.refId));
    const templateIds = initSelectedArr
      .filter((i: any) =>
        [usageTypes.TEMPLATE, usageTypes.BOTH].includes(i.usage)
      )
      .map((i: any) => String(i.refId));

    setCheckedKeys({
      [tabTypes.ContentSource]: contentIds,
      [tabTypes.SampleText]: templateIds
    });

    setAllCheckedKeys({
      [tabTypes.ContentSource]: contentIds,
      [tabTypes.SampleText]: templateIds
    });
  };

  const filterListCheckHandler = (item: any) => (e: any) => {
    const _filterList = [...filterList];
    const _index = _filterList.findIndex((i: any) => i.key === item.key);
    _filterList.splice(_index, 1, {
      ...item,
      checked: e.target.checked
    });
    setFilterList([..._filterList]);
  };

  const getKbName = (kbId: number) => {
    const item = kbList.find((i: any) => i.kbId === kbId);
    return item && item.kbName ? item.kbName : kbId;
  };

  const checkIsAllChecked = () => {
    const { files } = originData;
    const _files = checkedKeys[activeTab].length
      ? checkedKeys[activeTab].filter(
          (i: any) => i.indexOf("kb") < 0 && i.indexOf("folder") < 0
        )
      : [];
    return !!(_files.length && _files.length === files.length);
  };

  const filterTreeDataByFilterName = (list: any[], filterStr: string) => {
    if (!list || !list.length) {
      return [];
    }
    const searchLower = filterStr.toLowerCase();

    return list.reduce((acc, node) => {
      // 检查当前节点是否是我们要考虑的类型（1或3）
      const isKb = !!node.key.includes("kb-");
      const isFolder = !!node.key.includes("folder");
      // const isRelevantType = !isFolder;
      const isRelevantType = isKb;

      // 检查名称是否匹配（不区分大小写）
      const isNameMatch =
        isRelevantType &&
        node.name &&
        node.name.toLowerCase().includes(searchLower);

      // 特殊处理：如果命中的是知识库，保留所有子节点
      const shouldKeepAllChildren = isNameMatch && isKb;

      let children = node.children
        ? shouldKeepAllChildren
          ? node.children // 保留所有子节点
          : filterTreeDataByFilterName(node.children, filterStr) // 正常筛选子节点
        : undefined;

      // 处理t文件夹节点：如果没有子数据则移除
      if (children) {
        children = children.filter(
          (child: any) =>
            child.elementType !== 2 ||
            (child.children && child.children.length > 0)
        );
      }

      // 新增规则：如果知识库下只有文件夹且文件夹没有子元素，则忽略
      if (node.elementType === 1 && children) {
        const hasOnlyType2WithNoChildren = children.every(
          (child: any) =>
            child.elementType === 2 &&
            (!child.children || child.children.length === 0)
        );

        if (hasOnlyType2WithNoChildren) {
          children = undefined;
        }
      }

      // 如果当前节点匹配，或者有匹配的子节点，则保留该节点
      const shouldKeepNode = isNameMatch || (children && children.length > 0);

      if (shouldKeepNode) {
        const newNode = {
          ...node,
          children: children && children.length > 0 ? children : undefined
        };
        acc.push(newNode);
      }

      return acc;
    }, []);
  };

  const getAllKeys = (data: any[]): React.Key[] => {
    return data.flatMap((node) => [
      node.key,
      ...(node.children ? getAllKeys(node.children) : [])
    ]);
  };

  const treeData = useMemo(() => {
    return fixTreeData(originData);
  }, [originData, checkedKeys]);

  const isIndeterminate = useMemo(() => {
    return !!(checkedKeys[activeTab].length && !checkIsAllChecked());
  }, [checkedKeys, originData, activeTab]);

  // const isDisableSubmit = useMemo(() => {
  //   const { allFiles } = originData;
  //   const { contentSource, sampleText } = checkedKeys;
  //   return !allFiles.some(
  //     (i: any) => contentSource.includes(i.key) || sampleText.includes(i.key)
  //   );
  // }, [checkedKeys, originData]);

  const realTabItems = tabItems; //useMemo(() => {
  // return writingType === writingTypes.Full ? tabItems : [{ ...tabItems[0] }];
  //   return tabItems;
  // }, [writingType, tabItems]);

  const filterTreeData = useMemo(() => {
    return filterName
      ? JSON.parse(
          JSON.stringify(filterTreeDataByFilterName(treeData, filterName))
        ).map((i: any) => calculateLeafCountImmutable(i))
      : treeData;
  }, [treeData, filterName]);

  // 合并显示勾选状态：筛选显示的节点 + 所有被勾选的节点
  const mergedCheckedKeys = useMemo(() => {
    const filteredKeys = new Set(getAllKeys(filterTreeData));
    return Array.from(
      new Set([
        ...checkedKeys[activeTab].filter((key) => filteredKeys.has(key)),
        ...allCheckedKeys[activeTab]
      ])
    );
  }, [checkedKeys, allCheckedKeys, filterTreeData, activeTab]);

  useEffect(() => {
    if (initSelectedArr.length && openSelectModal) {
      initCheckedFiles();
    }
  }, [initSelectedArr, openSelectModal]);

  useEffect(() => {
    const isCheckAll = checkIsAllChecked();
    if (isCheckAll !== allChecked) {
      setAllChecked(isCheckAll);
    }
  }, [checkedKeys, activeTab]);

  useEffect(() => {
    getTreeData();
    setExpandKbs();
  }, [kbList]);

  useEffect(() => {
    if (!initKbList || (initKbList && initKbList.length === 0)) {
      console.log("initial material tree");
      fetchKbList();
      if (mockData) {
        saveOriginData(mockData);
      }
    } else {
      if (initKbList.length) {
        console.log("use old material data");
        const _kbList = initKbList.map((i: any) => ({
          ...i,
          kbId: i.key.replace("kb-", ""),
          kbName: i.name
        }));
        setKbList([..._kbList]);
      }
    }
  }, [initKbList]);

  return (
    <>
      <Modal
        destroyOnClose
        open={openSelectModal}
        width="880px"
        title={
          <div className="font-bold pl-[24px] inline-block pt-[20px]">
            选择文件
          </div>
        }
        onOk={handleConfirmSelect}
        onCancel={handleCancelModal}
        style={{ padding: 0, minWidth: "880px" }}
        wrapClassName="custom-modal"
        footer={
          <div
            className="flex justify-between px-[24px] py-[20px]"
            style={{ borderTop: "1px solid #E9E9E9" }}
          >
            <div className="flex items-center"></div>
            <div className="flex gap-[12px]">
              {filterListShow ? (
                <Button
                  // onClick={switchFilterListShow()}
                  onClick={handleCancelModal}
                  className="border-[#ebebeb] text-[#555]"
                >
                  取消
                </Button>
              ) : (
                <Button
                  onClick={handleCancelModal}
                  className="border-[#ebebeb] text-[#555]"
                >
                  取消
                </Button>
              )}
              {filterListShow ? (
                <PrimaryBtn onClick={filterListConfirm}>确定</PrimaryBtn>
              ) : (
                <PrimaryBtn
                  // disabled={isDisableSubmit}
                  onClick={handleConfirmSelect}
                >
                  确定
                </PrimaryBtn>
              )}
            </div>
          </div>
        }
      >
        <Spin spinning={isMaterialApisFetching}>
          <div className="cec-knowledge-base-box h-[490px] ">
            <div className="px-6">
              <Tabs
                defaultActiveKey="chunking"
                items={[...realTabItems]}
                activeKey={activeTab.toString()}
                onChange={handleTabChange}
              />
              {/* <div>{JSON.stringify(checkedKeys)}</div> */}
              <div className="flex mb-3 justify-between">
                <PrimaryBtn
                  type="primary"
                  icon={<UploadOutlined />}
                  onClick={goToUpload}
                >
                  上传
                </PrimaryBtn>
                <div className="w-[350px]">
                  <Input
                    ref={filterRef}
                    placeholder="搜索知识库名称"
                    disabled={!treeData.length}
                    onKeyDown={filterNameKeyDownHandler}
                    suffix={<SearchOutlined onClick={filterHandler} />}
                  />
                </div>
              </div>
            </div>
            {filterListShow ? (
              <div className="px-6 h-[360px] overflow-y-scroll mr-2">
                {filterList.length ? (
                  filterList.map((i: any, idx: number) => {
                    return (
                      <div
                        className="flex items-center py-3 border-solid border-0 border-b-[1px] border-[#eee]"
                        key={`filter-list-${idx}`}
                      >
                        <Checkbox
                          checked={i.checked}
                          onChange={filterListCheckHandler(i)}
                        />
                        <div className="ml-4 mr-3">{getIcon(i)}</div>
                        <div
                          className="flex-1 w-[740px] truncate"
                          title={i.title}
                        >
                          {i.name}
                        </div>
                        <div className="text-[#888] text-xs ml-14 px-1">
                          {getKbName(i.kbId)}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <Empty className="mt-24" />
                )}
              </div>
            ) : (
              <div className="px-6 ">
                <div className="mb-3">
                  <Checkbox
                    disabled={!filterTreeData.length}
                    checked={allChecked}
                    indeterminate={isIndeterminate}
                    onChange={allCheckedOnChange}
                  >
                    全选
                    {/* {String(allChecked)} */}
                  </Checkbox>
                </div>
                <div className="h-96 material-tree-wrap">
                  <Tree
                    checkable
                    expandedKeys={expandedKeys[activeTab]}
                    autoExpandParent={autoExpandParent}
                    checkedKeys={mergedCheckedKeys}
                    treeData={filterTreeData}
                    selectable={false}
                    onCheck={onTreeCheck}
                    onExpand={onTreeExpand}
                    height={330}
                    titleRender={(node: any) => (
                      <span className={`flex w-[750px] pr-10`}>
                        {getIcon(node)}
                        <span className="truncate" title={node.name}>
                          {node.name}
                        </span>
                        {node.elementType !== elementTypes.FILE ? (
                          <span className="text-[#888] text-xs pt-1">
                            （已选 {node.leafCheckedCount}/{node.leafCount}）
                          </span>
                        ) : null}
                      </span>
                    )}
                  />
                  {/* {JSON.stringify(treeData)} */}
                </div>
              </div>
            )}
          </div>
        </Spin>
      </Modal>
    </>
  );
};

export default SelectMaterialModal;
