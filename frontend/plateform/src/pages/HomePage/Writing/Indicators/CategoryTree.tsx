import React, {
  useState,
  useCallback,
  useEffect,
  useMemo,
  useRef
} from "react";
import {
  Button,
  Input,
  Tooltip,
  Tree,
  message,
  Modal,
  Empty,
  Spin
} from "antd";
import {
  SearchOutlined,
  CloseOutlined,
  PlusOutlined,
  CaretDownOutlined,
  CaretRightOutlined
} from "@ant-design/icons";
import {
  IconCollapseDown,
  IconCollapseUp,
  IndicatorFormIcon
} from "@/components/Icon";
import TreeItem from "./TreeItem";
import {
  useSplitLayout,
  EventTypes
} from "@/components/SplitLayout/SplitLayoutContext";
import {
  getIndicatorCategory,
  editIndicatorCategory,
  addIndicatorCategory,
  deleteIndicatorCategory
} from "./common/useIndicatorsService";
// import { mockIndicatorTreeList } from "./common/mockData";
import "./style.less";

const { TextArea } = Input;

export enum menuActionTypes {
  RENAME = "reName",
  RENAMECONFIRM = "reNameConfiem",
  DELETE = "delete",
  ADDNODE = "addNode",
  ADDFORM = "addForm",
  CLICK = "click"
}

const indicatorTypes = [
  {
    label: "原始指标",
    value: 1
  },
  {
    label: "统计指标",
    value: 2
  }
];

const initialCategory = {
  categoryName: "",
  categoryType: 0,
  id: "abced",
  indicatorType: indicatorTypes[0].value,
  parentId: "0",
  status: 1,
  subCategories: []
};

const childrenKey = "subCategories";

const fixIndicatorCategoryTree = (list: any[]) => {
  return list.map((i: any) => fixRow(i));
};

const fixRow = (item: any) => {
  const { id, parentId, categoryType } = item;
  if (item[childrenKey] && item[childrenKey].length) {
    item[childrenKey] = item[childrenKey].map((i: any) => fixRow(i));
  }
  return Object.assign({}, item, {
    id: String(id),
    parentId: String(parentId),
    selectable: !!(categoryType === 1)
  });
};

const CategoryTree: React.FC = () => {
  const [curIndicator, setCurIndicator] = useState<any>({});
  const [searchVal, setSearchVal] = useState<string>("");
  const [treeData, setTreeData] = useState<any[]>([]);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [dragItem, setDragItem] = useState<any>({});
  const [editRowId, setEditRowId] = useState<string>("");

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isShowSearch, setIsShowSearch] = useState<boolean>(false);
  const [isAllExpand, setIsAllExpand] = useState<boolean>(false);
  const [curCategory, setCurCategory] = useState<any>({});
  const [isShowAddFromModal, setIsShowAddFromModal] = useState<boolean>(false);
  const [formTitle, setFormTitle] = useState<string>("");
  const [indicatorType, setIndicatorType] = useState<number>(
    indicatorTypes[0].value
  );
  const [description, setDescription] = useState<string>("");
  const [isFormLoading, setIsFormLoading] = useState<boolean>(false);
  const [highLightNodeId, setHighLightNodeId] = useState<string | undefined>(
    undefined
  );
  const [filterTreeData, setFilterTreeData] = useState<any[]>([]);
  const [isExpandCategory, setIsExpandCategory] = useState<boolean>(true);
  const [isExpandForm, setIsExpandForm] = useState<boolean>(true);
  const treeContainerRef = useRef<any>(null);

  const { publish, useSubscribe } = useSplitLayout();

  const publishSelectIndicator = (node: any) => {
    publish(EventTypes.INDICATOR_FORM_CLICK, node);
  };

  useSubscribe<number>(EventTypes.CATEGORY_DESC_CHANGE, (params: any) => {
    editIndicatorCategoryTree(params, () => {
      publish(EventTypes.CATEGORY_DESC_CHANGE_DONE, params.description);
    });
  });

  const handleSearchValChange = (e: any) => {
    const val = e.target.value.trim();
    setSearchVal(val);
  };

  const filterTreeDataByKey = () => {
    if (searchVal) {
      const _treeData = filterTreeByName(treeData, searchVal);
      setFilterTreeData([..._treeData]);
    } else {
      setIsShowSearch(false);
    }
  };

  const toggleShowSearch = (sta: boolean) => () => {
    setIsShowSearch(sta);
  };

  const changeExpandSta = () => {
    if (isAllExpand) {
      setExpandedKeys([]);
    } else {
      expandAll();
    }
    setIsAllExpand(!isAllExpand);
  };

  const onExpand = (expandedKeys: any[]) => {
    setExpandedKeys(expandedKeys);
  };

  const fetchIndicatorCategoryTree = async (cb?: any) => {
    setIsLoading(true);
    getIndicatorCategory()
      .then((data: any) => {
        if (data && data.length) {
          const list = fixIndicatorCategoryTree(data || []);
          setTreeData([...list]);
          setTimeout(() => {
            cb && cb();
          }, 100);
        }
      })
      .finally(() => {
        setIsLoading(false);
      })
      .catch((e) => {
        setIsLoading(false);
      });
  };

  const editIndicatorCategoryTree = async (params: any, cb?: any) => {
    editIndicatorCategory(params).then((data: any) => {
      if (data) {
        fetchIndicatorCategoryTree();
        cb && cb();
      }
    });
  };

  const addIndicatorCategoryTree = async (params: any, cb?: any) => {
    addIndicatorCategory(params)
      .then((data: any) => {
        if (data) {
          fetchIndicatorCategoryTree();
          cb && cb(data);
        }
      })
      .catch(() => {
        setIsFormLoading(false);
      });
  };

  const deleteIndicatorCategoryTree = async (id: string, cb?: any) => {
    deleteIndicatorCategory(id).then((data: any) => {
      if (data) {
        cb && cb();
      }
    });
  };

  const findFirstLeaf: any = (nodes: any[], parentKeys: string[] = []) => {
    for (const node of nodes) {
      const ids = [...parentKeys, node.id];
      if (node.categoryType === 1) {
        setCurIndicator({ ...node });
        publishSelectIndicator({ ...node });
        return ids;
      }
      if (node[childrenKey] && node[childrenKey].length) {
        const leafKeys = findFirstLeaf(node[childrenKey], ids);
        if (leafKeys) {
          return leafKeys;
        }
      }
    }
    return null;
  };

  const allowDrop = useCallback(
    ({ dropNode }: { dropNode: any }) => {
      const { categoryType, parentId, id } = dropNode;
      const isNode = !!(categoryType === 1);
      const isAllowDrop = !!(
        !isNode ||
        // (!isNode && dragItem.parentId !== id) ||
        (isNode && parentId !== dragItem.parentId)
      );
      return isAllowDrop;
    },
    [dragItem]
  );

  const onDragStart = ({ node }: { node: any }) => {
    if (node[childrenKey] && node[childrenKey].length > 0 && node.expanded) {
      const _expandedKeys = [...expandedKeys];
      const idx = _expandedKeys.findIndex((key: string) => key === node.key);
      _expandedKeys.splice(idx, 1);
      setExpandedKeys([..._expandedKeys]);
    }
    setDragItem(node);
  };

  const onDragEnd = () => {
    setDragItem({});
  };

  const onDrop = (info: any) => {
    const { dragNode, node, dropPosition, dropToGap } = info;
    const dropPos = node.pos.split("-");
    const dropLevel = dropPos.length - 1;

    const isDropToRootLevel = dropLevel === 1 && dropToGap;
    // const isDropIntoRoot = dropLevel === 1 && !dropToGap;
    // const isDropBeforeFirstRoot = dropLevel === 1 && dropPosition === -1;
    console.log(
      `拖拽位置: dropPosition=${dropPosition}, dropToGap=${dropToGap}, dropLevel=${dropLevel}`
    );

    const isNode = !!(node.categoryType === 1);
    if (!isNode || (isNode && node.parentId !== dragNode.parentId)) {
      const isSelfParent = dragNode.parentId === node.id;
      const { id } = dragNode;
      const parentId = isSelfParent || isNode ? node.parentId : node.id;
      console.log(dragNode, node);
      if (isDropToRootLevel) {
        editIndicatorCategoryTree({ id, parentId: node.parentId });
      } else {
        editIndicatorCategoryTree({ id, parentId });
      }
    }
  };

  const treeAction = (action: string, node: any, title?: string) => {
    const { id, categoryType, categoryName, parentId } = node;
    switch (action) {
      case menuActionTypes.CLICK:
        if (categoryType === 1 && curIndicator && id !== curIndicator.id) {
          publishSelectIndicator({ ...node });
          setCurIndicator(node);
        }
        break;
      case menuActionTypes.DELETE:
        deleteNode(id);
        break;
      case menuActionTypes.RENAME:
        setEditRowId(id);
        break;
      case menuActionTypes.RENAMECONFIRM:
        if (categoryName === title) {
          if (!title) {
            deleteNode();
          }
          setEditRowId("");
        } else {
          if (categoryName) {
            editIndicatorCategoryTree({ id, categoryName: title }, () => {
              message.success("重命名成功");
              setEditRowId("");
            });
          } else {
            addIndicatorCategoryTree(
              {
                categoryName: title,
                categoryType: 0,
                parentId: Number(parentId)
              },
              (node?: any) => {
                message.success("添加分类成功");
                setEditRowId("");
                const _node = { ...node };
                const cb = (node: any) => () => {
                  if (node) {
                    // setHighLightNodeId(node.id);
                    // setTimeout(() => {
                    //   setHighLightNodeId(undefined);
                    // }, 3000);
                  }
                };
                fetchIndicatorCategoryTree(cb(_node));
              }
            );
          }
        }
        break;
      case menuActionTypes.ADDNODE:
        setExpandedKeys(getImmutabeKeys([id]));
        node[childrenKey] = node[childrenKey] || [];
        addCategory(node[childrenKey], node);
        break;
      case menuActionTypes.ADDFORM:
        setCurCategory({ ...node });
        setIsShowAddFromModal(true);
        break;
    }
  };

  const getImmutabeKeys = (ids: string[]) => {
    return Array.from(new Set([...expandedKeys, ...ids]));
  };

  const handlerAddCategory = () => {
    addCategory(treeData);
  };

  const deleteNode = (id?: string) => {
    if (!id) {
      const updatedTree = removeTempNode(initialCategory.id);
      setTreeData([...updatedTree]);
    } else {
      deleteIndicatorCategoryTree(id, () => {
        const updatedTree = removeTempNode(id);
        setTreeData([...updatedTree]);
        message.success("删除成功");
        if (curIndicator.id === id) {
          expandFirstLeaf();
        }
      });
    }
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

  const updateNode = (treeData: any[], nodeId: string) => {
    const updatedTree = JSON.parse(JSON.stringify(treeData));
    const findAndUpdateNode = (nodes: any[]) => {
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].id === nodeId) {
          nodes[i][childrenKey] = [
            ...nodes[i][childrenKey],
            { ...Object.assign({}, initialCategory, { parentId: nodeId }) }
          ];
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

  const addCategory = (list: any[], node?: any) => {
    let _treeData = list;
    const idx = _treeData.findIndex((i: any) => i.id === initialCategory.id);
    const id = idx < 0 ? initialCategory.id : _treeData[idx].id;
    console.log(id, idx, _treeData);

    if (idx < 0) {
      if (node && node.id) {
        // 子分类
        _treeData = updateNode(treeData, node.id);
        setTreeData([..._treeData]);
        setTimeout(() => {
          const _expandedKeys = getImmutabeKeys([node.id, initialCategory.id]);
          setExpandedKeys(_expandedKeys);
        }, 50);
      } else {
        setTreeData([..._treeData, { ...initialCategory }]);
      }
    }
    if (id !== editRowId) {
      setEditRowId(String(id));
    }
  };

  const filterTreeByName = (
    nodes: any[],
    categoryName: string,
    path: string[] = []
  ) => {
    const result = [];

    for (const node of nodes) {
      const { subCategories, ...nodeWithoutChildren } = node;
      const nodeWithParent = {
        ...nodeWithoutChildren,
        path
      };

      if (
        node.categoryName.toLowerCase().includes(categoryName.toLowerCase())
      ) {
        result.push(nodeWithParent);
      }

      if (node[childrenKey] && node[childrenKey].length > 0) {
        const newPath = [...path, node.categoryName];
        const childResults: any = filterTreeByName(
          node[childrenKey],
          categoryName,
          newPath
        );
        result.push(...childResults);
      }
    }

    return result;
  };

  const resetModal = () => {
    if (!isFormLoading) {
      setCurCategory({});
      setIsShowAddFromModal(false);
      setIndicatorType(indicatorTypes[0].value);
    }
  };

  const changeIndicatorType = (type: number) => () => {
    setIndicatorType(type);
  };

  const handlerFormTitleChange = (e: any) => {
    const val = e.target.value.trim();
    setFormTitle(val);
  };

  const handlerDescriptionChange = (e: any) => {
    const val = e.target.value.trim();
    setDescription(val);
  };

  const confirmAddForm = () => {
    if (!formTitle) {
      message.warning("指标表单名称未填写！");
    } else {
      setIsFormLoading(true);
      addIndicatorCategoryTree(
        {
          categoryName: formTitle,
          categoryType: 1,
          parentId: Number(curCategory.id),
          indicatorType,
          description
        },
        () => {
          message.success("添加表单成功");
          fetchIndicatorCategoryTree();
          setIsFormLoading(false);
          const _expandedKeys = getImmutabeKeys([curCategory.id]);
          setExpandedKeys([..._expandedKeys]);
          setIsShowAddFromModal(false);
        }
      );
    }
  };

  const getAllKeys = (treeData: any[]) => {
    let ids: any[] = [];
    treeData.forEach((node) => {
      ids.push(node.id);
      if (node[childrenKey] && node[childrenKey].length > 0) {
        ids = ids.concat(getAllKeys(node[childrenKey]));
      }
    });
    return ids;
  };

  const onToggleExpandCategory = () => {
    setIsExpandCategory(!isExpandCategory);
  };

  const onToggleExpandForm = () => {
    setIsExpandForm(!isExpandForm);
  };

  const findNodeById: any = (nodes: any[], id: string | number, path = []) => {
    for (const node of nodes) {
      const newPath = [...path, node.id];

      if (node.id === id) {
        return { node, path: newPath };
      }

      if (node[childrenKey] && node[childrenKey].length > 0) {
        const found = findNodeById(node[childrenKey], id, newPath);
        if (found) {
          return found;
        }
      }
    }
    return null;
  };

  const findFirstNonLeaf = (nodes: any[], startNode: any) => {
    const stack = startNode[childrenKey]
      ? [
          ...startNode[childrenKey].map((child: any) => ({
            node: child,
            path: [startNode.id]
          }))
        ].reverse()
      : [];

    while (stack.length > 0) {
      const { node, path } = stack.pop();

      if (node.categoryType === 1) {
        return { node, path };
      }

      if (node[childrenKey] && node[childrenKey].length > 0) {
        stack.push(
          ...node[childrenKey].map((child: any) => ({
            node: child,
            path: [...path, node.id]
          }))
        );
      }
    }

    return null;
  };

  const expandFirstLeaf = () => {
    const leafPath = findFirstLeaf(treeData);
    if (leafPath) {
      setExpandedKeys(leafPath);
    }
  };

  const handlerFilterCategory = (node: any) => () => {
    const startNodeInfo = findNodeById(treeData, node.id);
    const { node: startNode, path } = startNodeInfo;

    // 验证起始节点是非叶子节点
    if (!startNode[childrenKey] || startNode[childrenKey].length === 0) {
      const _expandedKeys = getImmutabeKeys(path);
      setExpandedKeys([..._expandedKeys]);
      setIsShowSearch(false);
      return;
    }

    const found = findFirstNonLeaf(treeData, startNode);
    if (!found) {
      message.warning("该分类下无表单可展示");
      setIsShowSearch(false);
      return;
    } else {
      const _expandedKeys = Array.from(
        new Set([...expandedKeys, ...found.path])
      );
      setExpandedKeys([..._expandedKeys]);
      setIsShowSearch(false);
      treeAction(menuActionTypes.CLICK, found.node);
      scrollToNode();
    }
  };

  const handlerFilterForm = (node: any) => () => {
    const { path } = findNodeById(treeData, node.id);
    const _expandedKeys = getImmutabeKeys(path);
    setExpandedKeys([..._expandedKeys]);
    setIsShowSearch(false);
    treeAction(menuActionTypes.CLICK, node);
    scrollToNode();
  };

  const scrollToNode = () => {
    setTimeout(() => {
      const selectedNode = treeContainerRef.current.querySelector(
        ".ant-tree-node-selected"
      );
      if (selectedNode) {
        selectedNode.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 100);
  };

  const renderNode = useCallback(
    (node: any) => {
      return (
        <TreeItem
          node={node}
          editRowId={editRowId}
          highLightNodeId={highLightNodeId}
          treeAction={treeAction}
        />
      );
    },
    [treeData, editRowId, curIndicator, highLightNodeId]
  );

  const allKeys = useMemo(() => getAllKeys(treeData), [treeData]);

  const expandAll = useCallback(() => {
    setExpandedKeys(allKeys);
  }, [allKeys]);

  const filterCategorys = useMemo(() => {
    return filterTreeData.filter((i: any) => i.categoryType === 0);
  }, [filterTreeData]);

  const filterForms = useMemo(() => {
    return filterTreeData.filter((i: any) => i.categoryType === 1);
  }, [filterTreeData]);

  useEffect(() => {
    if (treeData && treeData.length > 0 && expandedKeys.length === 0) {
      expandFirstLeaf();
    }
  }, [treeData]);

  useEffect(() => {
    fetchIndicatorCategoryTree();
  }, []);

  return (
    <div className="py-4 pl-4 pr-1 h-full flex flex-col category-tree">
      {/* <div>{JSON.stringify(allKeys)}</div> */}
      <div className="mb-3 flex justify-between select-none pr-3">
        <div className="flex-1">
          <Input
            placeholder="搜索分类名称 / 表单名称"
            disabled={isLoading}
            value={searchVal}
            onChange={handleSearchValChange}
            onPressEnter={filterTreeDataByKey}
            onFocus={toggleShowSearch(true)}
            suffix={
              <SearchOutlined
                className="text-base cursor-pointer text-text-color3 hover:opacity-80"
                onClick={filterTreeDataByKey}
              />
            }
          />
        </div>
        {isShowSearch ? (
          <div className="w-9">
            <div
              className="p-1 pt-2 ml-3 cursor-pointer hover:opacity-80"
              onClick={toggleShowSearch(false)}
            >
              <CloseOutlined className="text-text-color2 text-base" />
            </div>
          </div>
        ) : null}
      </div>
      {!isShowSearch ? (
        <div className="select-none">
          <div className="text-text-color2 text-sm px-1 flex justify-between pr-3 mb-3">
            <div className="flex-1 h-6 leading-6 flex">
              <span>所有分类与表单</span>
              <Tooltip
                placement="top"
                color="white"
                title={
                  <span className="text-gray-2a my-1 inline-block">{`一键${isAllExpand ? "收起" : "展开"}`}</span>
                }
              >
                <Button
                  type="text"
                  size="small"
                  className="w-6 h-6 text-[#888] hover:!text-primary-color hover:!bg-[#f1f5ff]"
                  icon={
                    isAllExpand ? (
                      <IconCollapseUp className="p-1 text-base" />
                    ) : (
                      <IconCollapseDown className="p-1 text-base" />
                    )
                  }
                  onClick={changeExpandSta}
                />
              </Tooltip>
            </div>
            <Tooltip
              placement="top"
              color="white"
              title={
                <span className="text-gray-2a my-1 inline-block">添加分类</span>
              }
            >
              <Button
                type="text"
                size="small"
                className={`w-6 h-6 text-text-color2 hover:!text-primary-color hover:!bg-[#f1f5ff]`}
                icon={<PlusOutlined />}
                onClick={handlerAddCategory}
              />
            </Tooltip>
          </div>
          <Spin spinning={isLoading}>
            <div
              ref={treeContainerRef}
              className="h-[calc(100vh-240px)] overflow-x-hidden overflow-y-auto pr-3 scrollbar-thin"
            >
              <Tree
                blockNode
                draggable
                treeData={treeData}
                expandedKeys={expandedKeys}
                selectedKeys={[String(curIndicator.id)]}
                fieldNames={{
                  title: "categoryName",
                  key: "id",
                  children: String(childrenKey)
                }}
                allowDrop={allowDrop}
                onDragStart={onDragStart}
                onDragEnd={onDragEnd}
                onDrop={onDrop}
                titleRender={renderNode}
                onExpand={onExpand}
              />
            </div>
          </Spin>
        </div>
      ) : null}
      {isShowSearch ? (
        <div className="select-none text-gray-2a pr-3 text-sm h-[calc(100vh-190px)] overflow-x-hidden overflow-y-auto scrollbar-thin">
          {filterTreeData.length ? (
            <>
              <div className="h-10 leading-10">
                {isExpandCategory ? (
                  <CaretDownOutlined
                    className="text-[#888] cursor-pointer"
                    title="关闭"
                    onClick={onToggleExpandCategory}
                  />
                ) : (
                  <CaretRightOutlined
                    className="text-[#888] cursor-pointer"
                    title="展开"
                    onClick={onToggleExpandCategory}
                  />
                )}
                <span className="ml-3">分类</span>
              </div>
              {isExpandCategory
                ? (filterCategorys || []).map((i: any, idx: number) => {
                    return (
                      <div
                        className="ml-3 pl-4 py-3 cursor-pointer rounded border-b border-b-solid border-b-[#eee] hover:bg-[#f5f5f5]"
                        key={`category-filter-${i.id}-${idx}`}
                        onClick={handlerFilterCategory(i)}
                      >
                        <div className="mb-2 h-5 leading-5 break-words text-ellipsis line-clamp-1">
                          {i.categoryName}
                        </div>
                        <div
                          className="h-4 left-4 text-[#888] text-xs break-words text-ellipsis line-clamp-1"
                          title={i.path.join("/")}
                        >
                          {i.path.join(" / ")}
                        </div>
                      </div>
                    );
                  })
                : null}
              <div className="h-10 leading-10">
                {isExpandForm ? (
                  <CaretDownOutlined
                    className="text-[#888] cursor-pointer"
                    title="关闭"
                    onClick={onToggleExpandForm}
                  />
                ) : (
                  <CaretRightOutlined
                    className="text-[#888] cursor-pointer"
                    title="展开"
                    onClick={onToggleExpandForm}
                  />
                )}
                <span className="ml-3">表单</span>
              </div>
              {isExpandForm
                ? (filterForms || []).map((i: any, idx: number) => {
                    return (
                      <div
                        className="ml-3 pl-4 py-3 cursor-pointer rounded border-solid border-0 border-b border-b-[#eee] hover:bg-[#f5f5f5]"
                        key={`form-filter-${i.id}-${idx}`}
                        onClick={handlerFilterForm(i)}
                      >
                        <div className="mb-2 h-5 leading-5 break-words text-ellipsis line-clamp-1">
                          <IndicatorFormIcon className="mr-1" />
                          {i.categoryName}
                        </div>
                        <div
                          className="h-4 left-4 text-[#888] text-xs break-words text-ellipsis line-clamp-1"
                          title={i.path.join("/")}
                        >
                          {i.path.join(" / ")}
                        </div>
                      </div>
                    );
                  })
                : null}
            </>
          ) : (
            <Empty className="mt-20" />
          )}
        </div>
      ) : null}
      <Modal
        open={isShowAddFromModal}
        width={520}
        onCancel={resetModal}
        title="新建指标表单"
        footer={
          <div className="flex justify-end gap-4">
            <Button
              key="back"
              className="border-solid border border-[#ebebeb]"
              onClick={resetModal}
              disabled={isFormLoading}
            >
              <span className="text-text-color2">取消</span>
            </Button>
            <Button
              key="submit"
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                border: "none"
              }}
              loading={isFormLoading}
              onClick={confirmAddForm}
            >
              <span>确认</span>
            </Button>
          </div>
        }
      >
        <div className="pt-5">
          <div className="mb-2">
            <span className="text-[#ff4d4f]">*</span>指标表单名称
          </div>
          <div className="mb-5">
            <Input
              placeholder="请输入指标表单名称"
              value={formTitle}
              onChange={handlerFormTitleChange}
            />
          </div>
          <div className="mb-2">
            <span className="text-[#ff4d4f]">*</span>指标类型
          </div>
          <div className="mb-5 flex gap-3">
            {indicatorTypes.map((i: any, idx: number) => {
              return (
                <div
                  key={`form-type-${idx}`}
                  className={`flex-1 h-8 leading-8 text-center cursor-pointer ${indicatorType === i.value ? "bg-[#e2e9ff] text-primary-color" : "bg-[#f5f6fa] text-gray-2a"}`}
                  onClick={changeIndicatorType(i.value)}
                >
                  {i.label}
                </div>
              );
            })}
          </div>
          <div className="mb-2">描述</div>
          <div className="mb-5">
            <TextArea
              placeholder="请输入"
              value={description}
              onChange={handlerDescriptionChange}
              style={{ resize: "none", height: "160px" }}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default CategoryTree;
