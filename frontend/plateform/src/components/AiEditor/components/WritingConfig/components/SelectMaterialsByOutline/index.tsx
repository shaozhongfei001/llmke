import { Button, Checkbox, CheckboxChangeEvent, Tree } from "antd";
import { MaterialItemWithCustomId, MaterialItem } from "../type";
import { useEffect, useMemo, useRef, useState } from "react";
import ItemName from "../ItemName";
import { traversalTree } from "../help";
import IconLink from "../../../../assets/icon/icon-link.svg";

interface IProps {
  outlineData: MaterialItem[];
  getData: (list: MaterialItemWithCustomId[] | null) => any;
  materialTreeData?: any[];
}

const elementTypeObj: any = {
  1: "kb",
  2: "folder",
  3: "document"
};

enum ElementType {
  Kb = 1,
  Folder,
  Document
}

const renderNode = (nodeData: any) => {
  return (
    <div className="max-w-[550px]">
      <ItemName item={nodeData} iconSize="16px" iconRight="8px" />
    </div>
  );
};

const initTreeData = (tree: any[], cb: any) => {
  if (!tree || tree.length === 0) return [];
  const rowNode: any[] = [];
  tree.forEach((node) => {
    const { leafCount, elementType } = node;
    // 不是文件且没有子节点，舍弃
    if (elementType === ElementType.Document || leafCount) {
      const curNode = cb(node);

      if (node?.children && node.children.length !== 0)
        curNode.children = initTreeData(node?.children, cb);

      rowNode.push(curNode);
    }
  });
  return rowNode;
};

const SelectMaterialsByOutline = ({
  outlineData,
  getData,
  materialTreeData
}: IProps) => {
  const [contentOpen, setContentOpen] = useState<boolean>(false);
  const [value, setValue] = useState<any[]>([]);
  const [isAllChecked, setIsAllChecked] = useState(true);
  const contenRef = useRef<HTMLDivElement>(null);

  // 监听点击事件，用于关闭选择素材弹框
  useEffect(() => {
    const handleClick = (e: any) => {
      if (contenRef.current && contenRef.current.contains(e.target as Node)) {
        return;
      } else {
        setContentOpen(false);
      }
    };
    addEventListener("click", handleClick);
    return () => {
      setContentOpen(false);
      removeEventListener("click", handleClick);
    };
  }, []);

  // initTreeData
  const treeData = useMemo(() => {
    if (!materialTreeData || materialTreeData.length === 0) return [];
    return initTreeData(materialTreeData, (node: any) => {
      const { key, elementType, leafCount, leafKeys, name, refId, usage } =
        node;
      const _refEntityType = elementTypeObj[elementType];
      const _curTitle = renderNode({
        refEntityType: _refEntityType,
        refName: name,
        leafKeys
      });
      return {
        title: _curTitle,
        key,
        leafCount,
        leafKeys,
        refEntityType: _refEntityType,
        refName: name,
        refId: refId,
        usage
      };
    });
  }, [materialTreeData]);

  // 监听弹窗关闭，向外传送数据
  useEffect(() => {
    if (contentOpen) return;
    if (isAllChecked) {
      getData(null);
      return;
    }
    const _list: any[] = [];
    traversalTree(treeData, (node) => {
      if (value.includes(node.key)) {
        const { refEntityType, refName, refId, usage } = node;
        _list.push({ refEntityType, refName, refId, usage });
      }
    });
    getData(_list);
  }, [contentOpen, value, treeData]);

  // 获取叶子节点列表，用于全选和回显
  const treeLeafArr = useMemo(() => {
    const _treeLeafArr: any[] = [];
    const cb = (node: any) => {
      if (!node["children"] || node["children"].length === 0) {
        _treeLeafArr.push(node.key);
      }
    };
    traversalTree(treeData, cb, "children");
    return _treeLeafArr;
  }, [treeData]);

  // 回显
  useEffect(() => {
    if (outlineData == null) {
      const _value: string[] = [];
      const _cb = (node: any) => {
        if (!node["children"] || node["children"].length === 0) {
          _value.push(node.key);
        }
      };
      traversalTree(treeData, _cb);
      setValue(_value);
      return;
    }

    // 回显需要舍弃已经删除的部分
    const preRefIds = (outlineData || []).map((i) => String(i.refId));
    const _value = treeLeafArr.filter((key) => preRefIds.includes(key));
    setValue(_value);
  }, [outlineData, treeLeafArr]);

  const treeLen = useMemo(() => {
    return treeLeafArr?.length || 0;
  }, [treeLeafArr]);

  // 判断是否全选
  useEffect(() => {
    setIsAllChecked(treeLen !== 0 && value.length === treeLen);
  }, [value, treeLen]);

  // 选中项改变
  const onTreeCheck = (_, { checked, node }: any) => {
    const { leafKeys, key } = node;
    console.log(node);
    let _value = [...value];
    if (leafKeys && leafKeys.length !== 0) {
      // 文件夹或知识库
      if (checked) {
        _value = [...new Set([..._value, ...leafKeys])];
      } else {
        _value = _value.filter((i) => !leafKeys.includes(i));
      }
    } else {
      // 文件
      if (checked) {
        _value = [..._value, key];
      } else {
        _value = _value.filter((i) => i !== key);
      }
    }
    setValue(_value);
  };

  // 全选
  const onCheckAllChange = (e: CheckboxChangeEvent) => {
    const { checked } = e.target;
    const _value: string[] = [];
    if (checked) {
      const _cb = (node: any) => {
        if (!node["children"] || node["children"].length === 0) {
          _value.push(node.key);
        }
      };
      traversalTree(treeData, _cb);
    }
    setValue(_value);
  };

  return (
    <div ref={contenRef}>
      <Button
        onClick={() => setContentOpen(true)}
        className="w-full border-[1px] border-solid border-[#eee] text-[#555]"
      >
        <img src={IconLink} alt="" />
        关联文件（{value.length}）
      </Button>
      <div
        className="fixed top-[5vh] right-[451px] h-[90vh] p-5 box-border rounded-lg bg-white overflow-x-hidden overflow-y-auto transition-[0.3s]"
        style={{
          width: contentOpen ? "700px" : "0px",
          opacity: contentOpen ? "1" : "0"
        }}
      >
        <div className="ml-2">
          <Checkbox
            className="mr-3"
            indeterminate={value.length > 0 && value.length < treeLen}
            checked={isAllChecked}
            onChange={onCheckAllChange}
          />
          全部
        </div>
        <Tree
          className="w-[360px]"
          checkedKeys={value}
          checkable
          treeData={treeData}
          onCheck={onTreeCheck}
        />
      </div>
    </div>
  );
};

export default SelectMaterialsByOutline;
