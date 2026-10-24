import React, { useState, useMemo, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { Button, Input, Tooltip, Spin, message, Empty, Drawer } from "antd";
import {
  useSplitLayout,
  EventTypes
} from "@/components/SplitLayout/SplitLayoutContext";
import {
  getIndicatorTree,
  addIndicator,
  editIndicator,
  deleteIndicator,
  copyIndicator,
  moveIndicator
} from "./common/useIndicatorsService";
import { SearchOutlined, PlusOutlined, CloseOutlined } from "@ant-design/icons";
import {
  IconCollapseDown,
  IconCollapseUp,
  FilterIcon
} from "@/components/Icon";
import ListItem, { DropPosition } from "./ListItem";
import IndicatorEditor from "@/components/IndicatorEditor";
import { PrimaryBtn } from "../common/components/PrimaryBtn";

export enum indicatorTypeEnum {
  origin = "1",
  statistics = "2"
}

const indicatorTypeObj: any = {
  [indicatorTypeEnum.origin]: "原始指标", //tree
  [indicatorTypeEnum.statistics]: "统计指标"
};
export const childrenKey = "subIndicators";

export const dataTypes: any = {
  "0": "全部",
  "1": "数值",
  "2": "比率",
  "3": "日期",
  "4": "文本",
  "5": "其他"
};

export const dataTypeList = Object.keys(dataTypes).map((key: string) => {
  return {
    value: key,
    label: dataTypes[key]
  };
});

export enum changeType {
  DATA_TYPE_CHANGE = "dataType",
  CALCULATOR_CLICK = "calculator",
  DIS_ENABLE = "disEnable",
  COPY = "copy",
  DELETE = "delete",
  SOURCE_CHANGE = "source",
  ADD_CHILD = "addChild",
  ADD_NODE = "addNode",
  EDIT_ROW = "editRow",
  EDIT_INIT = "editInit"
}

export const initialLitRow = {
  categoryId: 0,
  description: "",
  id: "listRow",
  indicatorName: "",
  indicatorType: Number(indicatorTypeEnum.statistics),
  parentId: 0
};

export const initialTreeRow = {
  id: "treeNode",
  categoryId: 0,
  parentId: 0,
  indicatorType: Number(indicatorTypeEnum.origin),
  indicatorName: "",
  description: ""
};

export enum editTypeObj {
  indicatorName = "indicatorName",
  alias = "alias",
  description = "description"
}

const initialDrawerData = {
  open: false,
  curCalculator: null
};

const addFieldImmutable = (
  treeData: any,
  depth: number,
  parentId?: string | number
) => {
  return (treeData || []).map((node: any) => ({
    ...node,
    parentId: parentId ? parentId : 0,
    depth: depth + 1,
    isLeaf: !node[childrenKey] || node[childrenKey].length === 0,
    isExternal: false,
    [childrenKey]: node[childrenKey]
      ? addFieldImmutable(node[childrenKey], depth + 1, node.id)
      : []
  }));
};

const IndicatorDetail: React.FC<{ leftWidth?: number }> = ({
  leftWidth = 0
}) => {
  const navigator = useNavigate();
  const [item, setItem] = useState<any>({});
  const [searchVal, setSearchVal] = useState<string>("");
  const [treeDataOrigin, setTreeDataOrigin] = useState<any[]>([]);
  const [treeData, setTreeData] = useState<any[]>([]);
  const [indicatorListOrigin, setIndicatorListOrigin] = useState<any[]>([]);
  const [indicatorList, setIndicatorList] = useState<any[]>([]);
  const [editListId, setEditListId] = useState<string | undefined>(undefined);
  const [editType, setEditType] = useState<string>("");
  const [listLoading, setListLoading] = useState<boolean>(false);
  const [visibleDataType, setVisibleDataType] = useState(false);
  const [isEditDesc, setIsEditDesc] = useState<boolean>(false);
  const [filterDataType, setFilterDataType] = useState<string>("0");
  const [highLightNodeId, setHighLightNodeId] = useState<string | undefined>(
    undefined
  );
  const [visibleSearch, setVisibleSearch] = useState(false);
  const [filterList, setFilterList] = useState<any[]>([]);
  const descIptRef = useRef<any>(null);
  const tooltipContentRef = useRef<HTMLDivElement>(null);
  const dataTypeContentRef = useRef<HTMLDivElement>(null);
  const nodeRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const treeBodyRef = useRef(null);
  const [isAllExpand, setIsAllExpand] = useState<boolean>(true);

  const [calculatorInfo, setCalculatorInfo] = useState<any>({
    ...initialDrawerData
  });

  const registerNodeRef = (id: string, element: HTMLDivElement | null) => {
    if (element) {
      nodeRefs.current.set(id, element);
    } else {
      nodeRefs.current.delete(id);
    }
  };

  const { useSubscribe, publish } = useSplitLayout();

  const publishSelectIndicator = (params: any) => {
    publish(EventTypes.CATEGORY_DESC_CHANGE, params);
  };

  const publishCaclutorsSave = () => {
    publish(EventTypes.SAVE_CALCULATOR_CONFIRM, {});
  };

  const publishCalculatorSaveId = (id: string) => {
    publish(EventTypes.SAVE_CALCULATOR_ID, id);
  };

  useSubscribe<number>(EventTypes.INDICATOR_FORM_CLICK, (indicator: any) => {
    setIndicatorListOrigin([]);
    setTreeDataOrigin([]);
    setItem(indicator);
    setVisibleSearch(false);
    setIsEditDesc(false);
  });

  useSubscribe<number>(EventTypes.CATEGORY_DESC_CHANGE_DONE, (description) => {
    setItem({ ...item, description });
    setIsEditDesc(false);
  });

  useSubscribe<number>(EventTypes.SAVE_CALCULATOR, (calculators) => {
    if (calculatorInfo.curCalculator && calculatorInfo.curCalculator.id) {
      editNode(
        {
          id: calculatorInfo.curCalculator.id,
          calculators
        },
        () => {
          closeCalculatorDrawer();
          publishCalculatorSaveId(calculatorInfo.curCalculator.id);
          message.success("公式保存成功！");
        }
      );
    }
  });

  const resetEdit = () => {
    setEditListId("");
    setEditType("");
  };

  const handleSearchValChange = (e: any) => {
    const val = e.target.value.trim();
    setSearchVal(val);
  };

  const filterTreeData = () => {
    if (searchVal) {
      const _treeData = isOriginal ? treeData : indicatorList;
      const res = searchTree(_treeData, searchVal);
      setFilterList([...res]);
      setVisibleSearch(true);
    }
  };

  const searchTree = (treeData: any[], searchTerm: string) => {
    const results: any[] = [];

    const dfs = (node: any, parentPath: any[] = []) => {
      const nodeCopy = { ...node };
      nodeCopy.path = [...parentPath];
      const _indicatorName = node.indicatorName || "";
      const _alias =
        node.alias && node.alias.length ? node.alias.toString() : "";

      if (
        (_indicatorName &&
          _indicatorName.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (_alias && _alias.toLowerCase().includes(searchTerm.toLowerCase()))
      ) {
        if (nodeCopy[childrenKey]) {
          delete nodeCopy[childrenKey];
        }
        results.push(nodeCopy);
      }

      const currentPath: any[] = [...parentPath, node.indicatorName];

      if (node[childrenKey] && node[childrenKey].length > 0) {
        for (const child of node[childrenKey]) {
          dfs(child, currentPath);
        }
      }
    };

    for (const node of treeData) {
      dfs(node);
    }

    return results;
  };

  const fetchIndicatorDetail = (p?: any) => {
    if (item && item.id) {
      setListLoading(true);
      const params = p
        ? { ...p, categoryId: item.id }
        : {
            categoryId: item.id
          };
      getIndicatorTree(params)
        .then((res: any) => {
          if (res) {
            if (isOriginal) {
              setTreeDataOrigin([...addFieldImmutable(res, 0)]);
            } else if (isStatistics) {
              setIndicatorListOrigin([...addFieldImmutable(res, 0)]);
            } else {
              setTreeDataOrigin([]);
              setIndicatorList([]);
            }
          }
        })
        .finally(() => {
          setListLoading(false);
        })
        .catch((e) => {
          setListLoading(false);
        });
    }
  };

  const resetFilter = () => {
    if (isOriginal && filterDataType) {
      setFilterDataType("0");
      setTreeData(JSON.parse(JSON.stringify(treeDataOrigin)));
    }
  };

  const rowDataChange = (row: any, type: changeType, obj: any, cb?: any) => {
    const { id, parentId } = row;
    const {
      dataType,
      enable,
      indicatorName,
      description,
      alias,
      editIptType,
      sourceType
    } = obj;
    let isEditChange = false;
    switch (type) {
      case changeType.ADD_CHILD:
        if (!indicatorName) {
          resetFilter();
          handlerAddChildNode(id);
        }
        break;
      case changeType.ADD_NODE:
        if (indicatorName === row.indicatorName) {
          if (!indicatorName) {
            if (parentId) {
              deleteChildNode();
            } else {
              deleteNode();
            }
          }
          resetEdit();
        } else {
          resetFilter();
          const params = {
            categoryId: item.id,
            indicatorName,
            parentId: parentId
          };
          addNode(params);
        }
        break;
      case changeType.CALCULATOR_CLICK:
        setCalculatorInfo({
          ...calculatorInfo,
          open: true,
          curCalculator: row
        });
        break;
      case changeType.COPY:
        copyNode(id);
        break;
      case changeType.DATA_TYPE_CHANGE:
        editNode({
          dataType,
          id
        });
        break;
      case changeType.DELETE:
        deleteNode(id);
        break;
      case changeType.DIS_ENABLE:
        editNode({
          state: enable ? 1 : 2,
          id
        });
        break;
      case changeType.SOURCE_CHANGE:
        editNode({
          sourceType,
          id
        });
        break;
      case changeType.EDIT_ROW:
        if (
          indicatorName !== undefined &&
          indicatorName !== row.indicatorName
        ) {
          isEditChange = true;
          editNode({
            indicatorName,
            id
          });
        }

        if (description !== undefined && description !== row.description) {
          isEditChange = true;
          editNode(
            {
              description,
              id
            },
            cb
          );
        }

        if (alias !== undefined && String(alias) !== String(row.alias)) {
          isEditChange = true;
          editNode(
            {
              alias,
              id
            },
            cb
          );
        }

        if (!isEditChange) {
          resetEdit();
        }
        break;
      case changeType.EDIT_INIT:
        setEditListId(id);
        setEditType(editIptType);
        break;
    }
  };

  const addNode = (params: any) => {
    setListLoading(true);
    addIndicator(params)
      .then((res: any) => {
        if (res) {
          message.success("新建指标成功！");
          fetchIndicatorDetail();
        }
      })
      .finally(() => {
        setListLoading(false);
      })
      .catch((e) => {
        setListLoading(false);
      });
  };

  const editNode = (params: any, cb?: any) => {
    setListLoading(true);
    editIndicator(params)
      .then((res: any) => {
        if (res) {
          // fetchIndicatorDetail();
          updateRowData(JSON.parse(JSON.stringify(res)));
          cb && cb();
        }
      })
      .finally(() => {
        resetEdit();
        setListLoading(false);
      })
      .catch((e) => {
        setListLoading(false);
      });
  };

  const updateRowData = (newRow: any) => {
    if (isStatistics) {
      const _indicatorListOrigin = [...indicatorListOrigin];
      const idx = _indicatorListOrigin.findIndex(
        (i: any) => i.id === newRow.id
      );
      if (idx >= 0) {
        _indicatorListOrigin.splice(idx, 1, newRow);
        setIndicatorListOrigin([..._indicatorListOrigin]);
      } else {
        fetchIndicatorDetail();
      }
    } else {
      const _treeDataOrigin = replaceTreeNode(
        treeDataOrigin,
        newRow.id,
        newRow
      );
      setTreeDataOrigin([..._treeDataOrigin]);
    }
  };

  const replaceTreeNode = (
    tree: any[],
    id: string | number,
    newNode: any
  ): any[] => {
    return tree.map((node) => {
      // 找到目标节点
      if (String(node.id) === String(id)) {
        return node[childrenKey]
          ? {
              ...newNode, // 扩展新节点属性
              [childrenKey]: node[childrenKey]
            }
          : { ...newNode };
      }

      if (node[childrenKey] && node[childrenKey].length > 0) {
        return {
          ...node,
          [childrenKey]: replaceTreeNode(node[childrenKey], id, newNode)
        };
      }

      return node;
    });
  };

  const deleteNode = (id?: string) => {
    if (!id) {
      if (isStatistics) {
        const _indicatorList = [...indicatorList];
        const idx = _indicatorList.findIndex(
          (i: any) => i.id === initialLitRow.id
        );
        if (idx >= 0) {
          _indicatorList.splice(idx, 1);
        }
        setIndicatorList([..._indicatorList]);
      }
      if (isOriginal) {
        const _treeData = [...treeData];
        const idx = _treeData.findIndex((i: any) => i.id === initialTreeRow.id);
        if (idx >= 0) {
          _treeData.splice(idx, 1);
        }
        setTreeData([..._treeData]);
      }
    } else {
      setListLoading(true);
      deleteIndicator(id)
        .then((res: any) => {
          if (res) {
            if (isStatistics) {
              const _indicatorList = [...indicatorList];
              const idx = _indicatorList.findIndex((i: any) => i.id === id);
              if (idx >= 0) {
                _indicatorList.splice(idx, 1);
                setIndicatorList([..._indicatorList]);
              }
            } else {
              fetchIndicatorDetail();
            }
            message.success("删除指标成功！");
          }
        })
        .finally(() => {
          setListLoading(false);
        })
        .catch((e) => {
          setListLoading(false);
        });
    }
  };

  const deleteChildNode = () => {
    const updatedTree = removeTempNode(initialTreeRow.id);
    setTreeData([...updatedTree]);
    resetEdit();
  };

  const removeTempNode = (id: string) => {
    const updatedTree = JSON.parse(JSON.stringify(treeData));
    const findAndDeleteNode = (nodes: any[]) => {
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].id === id) {
          nodes.splice(i, 1);
          return true;
        }

        if (nodes[i][childrenKey] && nodes[i][childrenKey].length > 0) {
          if (findAndDeleteNode(nodes[i][childrenKey])) {
            return true;
          }
        }
      }
      return false;
    };

    findAndDeleteNode(updatedTree);
    return updatedTree;
  };

  const copyNode = (id: string) => {
    setListLoading(true);
    copyIndicator(id)
      .then((res: any) => {
        if (res) {
          fetchIndicatorDetail();
          message.success("复制指标成功！");
        }
      })
      .finally(() => {
        setListLoading(false);
      })
      .catch((e) => {
        setListLoading(false);
      });
  };

  const handlerAddNode = () => {
    if (isStatistics) {
      // console.log(indicatorList);
      const idx = indicatorList.findIndex(
        (i: any) => i.id === initialLitRow.id
      );
      if (idx < 0) {
        const _indicatorList = [...indicatorList, { ...initialLitRow }];
        setIndicatorList([..._indicatorList]);
        setEditListId(initialLitRow.id);
        setEditType(editTypeObj.indicatorName);
      }
    } else {
      // console.log(treeData);
      const idx = treeData.findIndex((i: any) => i.id === initialTreeRow.id);
      if (idx < 0) {
        const _treeData = [
          ...JSON.parse(JSON.stringify(treeData)),
          { ...initialTreeRow }
        ];
        setTreeData([..._treeData]);
        setEditListId(initialTreeRow.id);
        setEditType(editTypeObj.indicatorName);
      }
    }
  };

  const handlerAddChildNode = (parentId: string) => {
    const _treeData = updateNode(treeData, parentId);
    setTreeData([..._treeData]);
    setEditListId(initialTreeRow.id);
    setEditType(editTypeObj.indicatorName);
  };

  const updateNode = (treeData: any[], nodeId: string) => {
    const updatedTree = JSON.parse(JSON.stringify(treeData));
    const findAndUpdateNode = (nodes: any[]) => {
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].id === nodeId) {
          if (nodes[i][childrenKey]) {
            nodes[i][childrenKey] = [
              ...nodes[i][childrenKey],
              { ...Object.assign({}, initialTreeRow, { parentId: nodeId }) }
            ];
          } else {
            nodes[i][childrenKey] = [
              { ...Object.assign({}, initialTreeRow, { parentId: nodeId }) }
            ];
          }
          return true;
        }

        if (nodes[i][childrenKey] && nodes[i][childrenKey].length > 0) {
          if (findAndUpdateNode(nodes[i][childrenKey])) {
            return true;
          }
        }
      }
      return false;
    };

    findAndUpdateNode(updatedTree);
    return updatedTree;
  };

  const showVisibleDataType = () => {
    setVisibleDataType(true);
  };

  const handleDataTypeMouseLeave = () => {
    setTimeout(() => {
      if (
        !document.activeElement ||
        !dataTypeContentRef.current ||
        !dataTypeContentRef.current.contains(document.activeElement)
      ) {
        setVisibleDataType(false);
      }
    }, 100);
  };

  const filterIndicatorList = (type: string) => () => {
    if (type !== filterDataType) {
      if (isStatistics) {
        // console.log(type, indicatorList);
        const _indicatorList =
          type === "0"
            ? [...indicatorListOrigin]
            : (indicatorListOrigin || []).filter(
                (i: any) => String(i.dataType) === String(type)
              );
        setIndicatorList([..._indicatorList]);
      }
      if (isOriginal) {
        // console.log(type, treeData);
        const _treeData =
          type === "0"
            ? [...treeDataOrigin]
            : filterTreeByDataType(treeDataOrigin, type);
        setTreeData([..._treeData]);
      }
      setFilterDataType(type);
      setVisibleDataType(false);
    }
  };

  const filterTreeByDataType = (nodes: any[], dataType: string) => {
    const result = [];
    const stack = [...nodes];

    while (stack.length) {
      const node = stack.pop();

      if (String(node.dataType) === dataType) {
        const { subIndicators, ...nodeWithoutChildren } = node;
        result.push(nodeWithoutChildren);
      }

      if (node[childrenKey] && node[childrenKey].length > 0) {
        for (let i = node[childrenKey].length - 1; i >= 0; i--) {
          stack.push(node[childrenKey][i]);
        }
      }
    }

    return result;
  };

  const handleTooltipMouseLeave = () => {
    setTimeout(() => {
      if (
        !document.activeElement ||
        !tooltipContentRef.current ||
        !tooltipContentRef.current.contains(document.activeElement)
      ) {
        setVisibleSearch(false);
      }
    }, 100);
  };

  const filterConfirm = (id: string) => () => {
    setHighLightNodeId(id);
    setTimeout(() => {
      setVisibleSearch(false);
      if (nodeRefs.current.has(id)) {
        const element = nodeRefs.current.get(id);
        element?.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
          inline: "start"
        });
      }
    }, 50);
    setTimeout(() => {
      setHighLightNodeId(undefined);
    }, 4000);
  };

  const stopPropagation = (e: any) => {
    e.stopPropagation();
  };

  const handlerEditDesc = () => {
    setIsEditDesc(true);
    setTimeout(() => {
      descIptRef.current.focus();
    });
  };

  const handlerIptDescConfirm = (e: any) => {
    const description = e.target.value.trim();

    publishSelectIndicator({
      id: item.id,
      description
    });
  };

  const findNode = (nodes: any[], id: string): any | undefined => {
    for (const node of nodes) {
      if (node.id === id) {
        return node;
      }
      if (node[childrenKey] && node[childrenKey].length > 0) {
        const found = findNode(node[childrenKey], id);
        if (found) {
          return found;
        }
      }
    }
  };

  const moveNode = (
    nodes: any[],
    dragId: string,
    targetId: string,
    position: DropPosition
  ): any[] => {
    // 深拷贝保证数据不可变
    const cloneTree = JSON.parse(JSON.stringify(nodes)) as any[];
    // 查找节点辅助方法

    // 查找拖拽节点和目标节点
    const dragInfo = nodeAddParent(cloneTree, dragId);
    const targetInfo = nodeAddParent(cloneTree, targetId);

    // 边界检查
    if (!dragInfo || !targetInfo || dragId === targetId) {
      return nodes;
    }

    // 从原父节点移除
    dragInfo.parent.splice(dragInfo.parent.indexOf(dragInfo.node), 1);

    // 计算新位置
    let newParent: any[];
    let newDepth: number;
    let insertIndex: number;

    const { node, parent } = targetInfo;
    const { depth } = node;
    if (position === DropPosition.child) {
      newParent = node[childrenKey] || [];
      newDepth = depth ? depth + 1 : 1;
      insertIndex = newParent.length;
    } else {
      newParent = parent || [];
      newDepth = depth || 0;
      insertIndex =
        newParent.indexOf(targetInfo.node) +
        (position === DropPosition.after ? 1 : 0);
    }

    // 插入到新位置
    dragInfo.node.parentId =
      position === DropPosition.child ? targetId : targetInfo.node.parentId;
    dragInfo.node.rootId = targetInfo.node.rootId;
    dragInfo.node.depth = newDepth;
    newParent.splice(insertIndex, 0, dragInfo.node);

    // 递归更新子节点
    const updateChildren = (node: any) => {
      const _children = node[childrenKey] || [];
      _children.forEach((child: any) => {
        child.parentId = node.id;
        child.depth = node.depth ? node.depth + 1 : 1;
        updateChildren(child);
      });
    };
    updateChildren(dragInfo.node);

    return cloneTree;
  };

  // 给树数据增加parent对象
  const nodeAddParent = (
    nodes: any[],
    id: string
  ): { node: any; parent: any[] } | null => {
    for (const node of nodes) {
      if (node.id === id) {
        return { node, parent: nodes };
      }
      const _children = node[childrenKey] || [];
      if (_children.length > 0) {
        const result = nodeAddParent(_children, id);
        if (result) {
          return result;
        }
      }
    }
    return null;
  };

  const handleDrop = async (
    dragNode: any,
    targetId: string,
    position: DropPosition
  ) => {
    const { id } = dragNode;
    const dragId = id;
    // console.log("drop:", dragId, targetId, position, dragNode);

    const newData = isOriginal
      ? [...JSON.parse(JSON.stringify(treeDataOrigin))]
      : [...JSON.parse(JSON.stringify(indicatorListOrigin))];

    if (dragId === targetId) {
      return;
    }
    const targetNode = findNode(newData, targetId);

    // const _newList = moveNode(newData, dragId, targetId, position);

    // console.log("new _newList:", _newList, treeDataOrigin, treeData);

    const params: any = {
      id: dragId,
      newParentId: targetNode.parentId
    };

    switch (position) {
      case "before":
        params.nextId = targetId;
        break;
      case "after":
        params.prevId = targetId;
        break;
      case "child":
        params.newParentId = targetId;
        break;
    }
    setListLoading(true);
    moveIndicator(params)
      .then((res) => {
        if (res) {
          fetchIndicatorDetail();
          // setTreeDataOrigin([..._newList]);
          // setTimeout(() => {
          //   setHighLightNodeId(dragId);
          //   setTimeout(() => {
          //     setHighLightNodeId(undefined);
          //   }, 4000);
          // }, 500);
        }
      })
      .finally(() => {
        setListLoading(false);
      })
      .catch((e) => {
        console.log(e);
        setListLoading(false);
      });
  };

  const gotoConfigArticulation = () => {
    navigator(`/docWriting/indicator/articulation`);
  };

  const changeExpandSta = () => {
    setIsAllExpand(!isAllExpand);
  };

  const isOriginal = useMemo(() => {
    return !!(item && item.indicatorType === Number(indicatorTypeEnum.origin));
  }, [item]);

  const isStatistics = useMemo(() => {
    return !!(
      item && item.indicatorType === Number(indicatorTypeEnum.statistics)
    );
  }, [item]);

  const indicatorTypeName = useMemo(() => {
    let str = "-";
    if (item && item.indicatorType) {
      const name = indicatorTypeObj[Number(item.indicatorType)];
      if (name) {
        str = name;
      }
    }
    return str;
  }, [item]);

  // 指标配置公式相关
  const closeCalculatorDrawer = () => {
    setCalculatorInfo({
      curCalculator: null,
      open: false
    });
  };

  useEffect(() => {
    if (indicatorListOrigin) {
      setIndicatorList([...indicatorListOrigin]);
    }
  }, [indicatorListOrigin]);

  useEffect(() => {
    if (treeDataOrigin) {
      setTreeData(JSON.parse(JSON.stringify(treeDataOrigin)));
    }
  }, [treeDataOrigin]);

  useEffect(() => {
    if (item.id) {
      fetchIndicatorDetail();
      resetEdit();
      setFilterDataType("0");
    }
  }, [item.id]);

  return (
    <div className="py-4 pl-5 pr-2 h-full min-w-[890px]">
      <div className="flex justify-between mb-4 pr-3">
        <div className="flex-1">
          <div className="flex h-6 leading-6 mb-1">
            <b className="text-base text-gray-2a">{item.categoryName}</b>
            <div className="py-1 leading-4">
              <span className="ml-1 inline-block h-4 px-2 bg-[#e5f6ff] text-[#1886ec] text-xs">
                {indicatorTypeName}
              </span>
            </div>
          </div>
          <div className={`flex w-full text-xs pr-2`}>
            <div className={`text-text-color2 w-10 min-w-10 h-6 leading-7`}>
              描述：
            </div>
            {isEditDesc ? (
              <Input
                className="py-1 box-border text-xs h-7 leading-7"
                defaultValue={item.description}
                ref={descIptRef}
                placeholder="请输入描述"
                allowClear
                onClick={stopPropagation}
                onBlur={handlerIptDescConfirm}
                onPressEnter={handlerIptDescConfirm}
              />
            ) : (
              <span
                className="select-none px-2 py-[6px] cursor-pointer rounded border-[#d9d9d9] hover:border-solid hover:border hover:px-[7px] hover:py-[5px]"
                onClick={handlerEditDesc}
              >
                {item.description ? (
                  <Tooltip
                    placement="top"
                    color="white"
                    styles={{ root: { maxWidth: 400 } }}
                    title={
                      <span className="text-gray-2a my-1 inline-block">
                        {item.description}
                      </span>
                    }
                  >
                    <span className="text-text-color2 break-words text-ellipsis line-clamp-1">
                      {item.description}
                    </span>
                  </Tooltip>
                ) : (
                  <span className="text-[#bbb] break-words text-ellipsis line-clamp-1">
                    请输入描述
                  </span>
                )}
              </span>
            )}
          </div>
        </div>
        <div className="w-[438px] flex gap-3 h-8 leading-8 mt-[6px] justify-end">
          <Tooltip
            placement="bottomRight"
            arrow={false}
            trigger={[]}
            color="white"
            open={visibleSearch}
            styles={{
              root: {
                maxWidth: 600
              },
              body: {
                borderRadius: "8px"
              }
            }}
            align={{ offset: [0, 10] }}
            title={
              <div
                className="text-gray-2a flex items-center flex-col w-[446px] ml-1 py-2 max-h-[calc(100vh-300px)] min-h-20 overflow-y-auto overflow-x-hidden"
                ref={tooltipContentRef}
                onMouseLeave={handleTooltipMouseLeave}
              >
                {filterList.length ? (
                  filterList.map((i: any, idx: number) => {
                    return (
                      <div
                        className="h-[66px] w-[426px] bg-[#fafafa] mb-1 px-4 pt-4 py-3 box-border cursor-pointer hover:bg-[#f1f5ff]"
                        key={`filter-indicator-${i.id}-${idx}`}
                        onClick={filterConfirm(i.id)}
                      >
                        <div className="mb-2 h-5 leading-5 text-sm text-gray-2a">
                          <b>{i.indicatorName}</b>
                        </div>
                        <div className="h-4 leading-4 text-xs text-[#888]">
                          {i.path && i.path.length ? i.path.join(" / ") : "-"}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <Empty className="my-20" />
                )}
              </div>
            }
          >
            <Input
              className="w-60 border-[#d9d9d9]"
              placeholder="搜索指标名称 / 别名"
              value={searchVal}
              onChange={handleSearchValChange}
              onPressEnter={filterTreeData}
              suffix={
                <SearchOutlined
                  className="text-base cursor-pointer text-text-color3 hover:opacity-80"
                  onClick={filterTreeData}
                />
              }
            />
          </Tooltip>
          <Tooltip
            placement="top"
            color="white"
            title={
              <span className="text-gray-2a my-1 inline-block">新建指标</span>
            }
          >
            <Button
              className={`w-8 h-8 text-primary-color border-[#d9d9d9]`}
              icon={<PlusOutlined className="w-4" />}
              onClick={handlerAddNode}
            />
          </Tooltip>
          <Button
            className={`h-8 text-gray-2a border-[#d9d9d9]`}
            onClick={gotoConfigArticulation}
          >
            勾稽关系配置
          </Button>
        </div>
      </div>
      <div
        className="flex h-12 py-1 leading-10 mr-3 box-border bg-[#fafafa] select-none min-w-[950px]"
        style={{
          borderBottom: "1px solid #e4e8f6"
        }}
      >
        <div
          className={`${
            isOriginal ? "pl-4" : "pl-6"
          } w-1/4 box-border min-w-60 flex`}
        >
          <span>指标名称</span>
          {isOriginal ? (
            <Button
              type="text"
              size="small"
              title={`一键${isAllExpand ? "收起" : "展开"}`}
              className="w-6 h-6 mt-2 text-[#888] hover:!text-primary-color hover:!bg-[#f1f5ff]"
              icon={
                isAllExpand ? (
                  <IconCollapseUp className="p-1 text-base" />
                ) : (
                  <IconCollapseDown className="p-1 text-base" />
                )
              }
              onClick={changeExpandSta}
            />
          ) : null}
        </div>
        <div className="w-3/4 flex min-w-[710px]">
          <div className="w-[17%] min-w-[120px] pl-4 flex box-border">
            <span>数据类型</span>
            <Tooltip
              placement="bottom"
              arrow={false}
              color="white"
              className="p-0"
              open={visibleDataType}
              // onOpenChange={setVisibleDataType}
              title={
                <div
                  className="text-gray-2a -my-1 -mx-2"
                  ref={dataTypeContentRef}
                  onMouseLeave={handleDataTypeMouseLeave}
                >
                  {dataTypeList.map((d: any, idx: number) => {
                    return (
                      <div
                        className={`w-[52px] text-center rounded-lg h-8 leading-8 hover:bg-[#f1f5ff] select-none ${
                          d.value === filterDataType
                            ? "bg-[#f1f5ff]"
                            : " cursor-pointer"
                        }`}
                        key={`data-type-${d.value}-${idx}`}
                        onClick={filterIndicatorList(d.value)}
                      >
                        {d.label}
                      </div>
                    );
                  })}
                </div>
              }
            >
              <Button
                type="text"
                size="small"
                className={`relative top-3 w-5 h-5 text-[#000] hover:!text-primary-color hover:!bg-[#f1f5ff] hover:opacity-100 ${
                  (filterDataType && filterDataType !== "0") || visibleDataType
                    ? "text-primary-color"
                    : "opacity-25"
                }`}
                icon={<FilterIcon />}
                onClick={showVisibleDataType}
              />
            </Tooltip>
          </div>
          <div
            className={`${
              isOriginal ? "w-[27%] min-w-[180px]" : "w-[35%] min-w-[250px]"
            } pl-4 box-border`}
          >
            描述
          </div>
          <div
            className={`${
              isOriginal ? "w-[17%] min-w-32" : "w-[22%] min-w-40"
            } pl-4 box-border`}
          >
            别名
          </div>
          {isOriginal ? (
            <div className="w-[22%] min-w-40 pl-4 box-border">来源</div>
          ) : null}
          {isStatistics ? (
            <div className="w-[9%] min-w-[60px] pl-4 box-border">公式</div>
          ) : null}
          <div className="w-[8.5%] min-w-[60px] pl-4 box-border">启用</div>
          <div className="w-[8.5%] min-w-[60px] pl-4 box-border">操作</div>
        </div>
      </div>

      <DndProvider backend={HTML5Backend}>
        <Spin spinning={listLoading}>
          <div
            ref={treeBodyRef}
            className="overflow-y-auto overflow-x-hidden pr-3 h-[calc(100vh-280px)] min-w-[882px] scrollbar-thin"
          >
            {isOriginal ? (
              treeData.length ? (
                treeData.map((rootNode: any, idx: number) => {
                  return (
                    <ListItem
                      key={`origin-tree-${item.id}-${idx}`}
                      indicator={rootNode}
                      indicatorType={indicatorTypeEnum.origin}
                      editListId={editListId}
                      editType={editType}
                      highLightNodeId={highLightNodeId}
                      leftWidth={leftWidth}
                      isAllExpand={isAllExpand}
                      rowDataChange={rowDataChange}
                      registerNodeRef={registerNodeRef}
                      onDrop={handleDrop}
                      resetEdit={resetEdit}
                    />
                  );
                })
              ) : (
                <Empty className="mt-32" />
              )
            ) : null}
            {isStatistics ? (
              indicatorList.length ? (
                indicatorList.map((indicator: any, idx: number) => {
                  return (
                    <ListItem
                      key={`statistics-list-${item.id}-${idx}`}
                      indicator={indicator}
                      indicatorType={indicatorTypeEnum.statistics}
                      editListId={editListId}
                      editType={editType}
                      highLightNodeId={highLightNodeId}
                      leftWidth={leftWidth}
                      rowDataChange={rowDataChange}
                      registerNodeRef={registerNodeRef}
                      onDrop={handleDrop}
                      resetEdit={resetEdit}
                    />
                  );
                })
              ) : (
                <Empty className="mt-32" />
              )
            ) : null}
          </div>
        </Spin>
      </DndProvider>
      <Drawer
        destroyOnClose={true}
        open={calculatorInfo.open}
        onClose={closeCalculatorDrawer}
        closeIcon={null}
        size={"large"}
        extra={
          <CloseOutlined
            className="cursor-pointer"
            onClick={closeCalculatorDrawer}
          />
        }
        title={`${calculatorInfo.curCalculator?.indicatorName || "--"}公式配置`}
        styles={{
          header: {
            height: "56px"
          },
          footer: {
            height: "72px"
          },
          body: {
            padding: "16px 20px"
          }
        }}
        footer={
          <div className="h-full flex items-center justify-end gap-[16px]">
            <Button onClick={closeCalculatorDrawer} className="text-[#2a2a2a]">
              取消
            </Button>
            <PrimaryBtn onClick={publishCaclutorsSave} loading={listLoading}>
              保存
            </PrimaryBtn>
          </div>
        }
      >
        <IndicatorEditor
          indicators={calculatorInfo.curCalculator?.calculators}
        />
      </Drawer>
    </div>
  );
};

export default IndicatorDetail;
