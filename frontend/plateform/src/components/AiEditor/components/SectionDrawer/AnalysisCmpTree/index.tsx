import { useEffect, useState, useMemo, useRef } from "react";
import { Checkbox, Tree, Empty } from "antd";
import type { TreeProps } from "antd";
import { DependencyIcon } from "@/components/Icon";

interface Iprops {
  sectionInfo: any;
  analysisTreeOrigin: any[];
  clsoeExceptCls?: string;
  panelCls?: string;
  isVersion?: boolean;
  setAnalysisComponents: (list: any[]) => void;
  closeTreeHandler: () => void;
}

const AnalysisCmpTree = (props: Iprops) => {
  const {
    sectionInfo,
    analysisTreeOrigin = [],
    clsoeExceptCls = "",
    panelCls = "",
    isVersion = false,
    setAnalysisComponents,
    closeTreeHandler
  } = props;
  const [checkedKeys, setCheckedKeys] = useState<React.Key[]>([]);
  const [isAllChecked, setIsAllChecked] = useState<boolean>(false);

  const onTreeCheck: TreeProps["onCheck"] = (keys) => {
    setCheckedKeys(keys as React.Key[]);
  };

  const makeTreeImmutable = (
    treeData: any,
    depth: number,
    pardenId?: string | number
  ) => {
    return (treeData || []).map((node: any) => {
      const { categoryName, id, subCategories, components, status, name } =
        node;
      const isLeaf = !categoryName && !subCategories && !components;
      const key = isLeaf ? Number(id) : `${id}-${depth + 1}`;
      return {
        id: key,
        key,
        title: isLeaf ? name : categoryName,
        pardenId: pardenId ? pardenId : undefined,
        depth: depth + 1,
        isLeaf,
        status,
        children: subCategories
          ? makeTreeImmutable(subCategories, depth + 1, id)
          : components
            ? makeTreeImmutable(components, depth + 1, id)
            : []
      };
    });
  };

  const onCheckAllChange = (e: any) => {
    const isCheck = !!e.target.checked;
    setIsAllChecked(isCheck);
    setCheckedKeys(isCheck ? allLeafs.map((i: any) => i.id) : []);
  };

  const filterTreeDataByLeaf = (nodes: any[]) => {
    if (!nodes || !nodes.length) {
      return [];
    }
    return nodes.reduce((acc, node) => {
      const newNode = { ...node };
      if (newNode.children) {
        const filteredChildren = filterTreeDataByLeaf(newNode.children);
        newNode.children =
          filteredChildren.length > 0 ? filteredChildren : undefined;
      }
      if (newNode.isLeaf) {
        return [...acc, newNode];
      }

      return newNode.children ? [...acc, newNode] : acc;
    }, []);
  };

  const findLeafNodesByIds = (tree: any[], ids: number[], isAll?: boolean) => {
    const result: any[] = [];
    const idSet = new Set(ids);
    const isAllReturn = !!isAll;

    const traverse = (node: any) => {
      const { isLeaf, id } = node;
      if (isLeaf) {
        if (isAllReturn || idSet.has(id)) {
          result.push(node);
        }
      }
      if (node.children && node.children.length) {
        node.children.forEach((child: any) => traverse(child));
      }
    };

    tree.forEach((root: any) => traverse(root));
    return result;
  };

  const isNumber = (str: any) => {
    return Object.prototype.toString.call(str) === "[object Number]";
  };

  const analysisTreeData = useMemo(() => {
    return analysisTreeOrigin.length
      ? filterTreeDataByLeaf(makeTreeImmutable(analysisTreeOrigin, 0))
      : [];
  }, [analysisTreeOrigin]);

  const allLeafs = useMemo(() => {
    return analysisTreeData.length
      ? findLeafNodesByIds(analysisTreeData, [], true)
      : [];
  }, [analysisTreeData]);

  const checkedLeafs = useMemo(() => {
    return checkedKeys.filter((i) => isNumber(i));
  }, [checkedKeys]);

  useEffect(() => {
    setAnalysisComponents([...checkedLeafs]);
  }, [checkedLeafs]);

  useEffect(() => {
    if (checkedLeafs.length > 0 && checkedLeafs.length === allLeafs.length) {
      setIsAllChecked(true);
    }
  }, [checkedLeafs, allLeafs]);

  useEffect(() => {
    if (sectionInfo && sectionInfo.component && sectionInfo.component.length) {
      setCheckedKeys([...sectionInfo.component]);
    }
  }, [sectionInfo]);

  const clickListener = (e: any) => {
    const { target } = e;
    isCloseTree(target);
  };

  const isCloseTree = (el: any) => {
    const { tagName, nodeType, className, parentNode } = el;
    if (tagName === "BODY") {
      // console.log("可以关闭了");
      closeTreeHandler();
      return;
    }
    if (
      (nodeType === 1 &&
        className &&
        className.toString().includes(panelCls)) ||
      className.toString().includes(clsoeExceptCls)
    ) {
      return;
    }
    // console.log(parentNode);
    isCloseTree(parentNode);
  };

  useEffect(() => {
    window.addEventListener("click", clickListener);
    return () => {
      window.removeEventListener("click", clickListener);
    };
  }, []);

  return (
    <>
      <div className="mb-3">
        {/* <div className="a">
          // {JSON.stringify(checkedKeys)}--{allLeafs.length}
        </div> */}
        {/* <div className="a">{JSON.stringify(analysisTreeData)}</div> */}
        <Checkbox
          disabled={!analysisTreeData.length || isVersion}
          className="mr-3"
          indeterminate={
            checkedKeys.length > 0 && checkedLeafs.length < allLeafs.length
          }
          checked={isAllChecked}
          onChange={onCheckAllChange}
        />
        全部
      </div>
      {analysisTreeData.length ? (
        <Tree
          className="w-[360px]"
          checkedKeys={checkedKeys}
          checkable={!isVersion}
          selectable={false}
          defaultExpandAll={true}
          treeData={analysisTreeData}
          onCheck={onTreeCheck}
          titleRender={(node: any) => (
            <div className="flex">
              {node.isLeaf ? <DependencyIcon className="mr-1" /> : null}
              <span className="truncate">{node.title}</span>
            </div>
          )}
        />
      ) : (
        <div className="w-full h-[60vh] min-h-52 flex items-center justify-center">
          <Empty />
        </div>
      )}
    </>
  );
};

export default AnalysisCmpTree;
