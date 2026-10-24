import { useState, useMemo, useCallback } from "react";
import { Input, Tree, Checkbox } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import type { TreeDataNode, TreeProps } from "antd";
import { useServices } from "../service.ts";
interface Iprops {
  tableTree: any[];
  chooseTableKeys: number[];
  setChooseTableKeys: (tbs: any[]) => void;
  handleSelectedTable: (id: any) => void;
}

const SelectTable = ({
  tableTree = [],
  chooseTableKeys,
  setChooseTableKeys,
  handleSelectedTable
}: Iprops) => {
  const [searchVal, setSearchVal] = useState<string>("");

  const onSelect: TreeProps["onSelect"] = (selectedKeys, info) => {
    console.log("selected", selectedKeys, info);
    const { node } = info;
    if (node?.isLeaf) {
      // 获取表详情
      handleSelectedTable(node.id);
    }
  };

  const onCheck: TreeProps["onCheck"] = (checkedKeys, info) => {
    console.log("onCheck", checkedKeys, info);
    setChooseTableKeys(checkedKeys as React.Key[]);
    const nodes = info.checkedNodes;
    const nodeKeys = nodes.filter((n) => n.isLeaf).map((n) => n.id);
    setChooseTableKeys([...nodeKeys]);
  };

  const getAllTableKeys = useCallback(() => {
    const allTableKeys: any[] = [];

    tableTree.map((item) => {
      if (item.tables && item.tables?.length > 0) {
        item.tables.forEach((tb) => {
          allTableKeys.push(tb.key);
        });
      }
    });
    return allTableKeys;
  }, [tableTree]);

  const onAllSelect = (e) => {
    if (e.target.checked) {
      const allTableKeys: any[] = [];

      tableTree.map((item) => {
        if (item.tables && item.tables?.length > 0) {
          item.tables.forEach((tb) => {
            allTableKeys.push(tb.key);
          });
        }
      });

      setChooseTableKeys(allTableKeys);
    } else {
      setChooseTableKeys([]);
    }
  };

  const treeData = useMemo(() => {
    if (searchVal.trim().length > 0) {
      const searchData: any[] = [];

      tableTree.map((item) => {
        if (item.tables && item.tables?.length > 0) {
          item.tables.forEach((tb) => {
            const strTitle = tb.name as string;
            const index = strTitle.indexOf(searchVal);
            if (index > -1) {
              searchData.push(tb);
            }
          });
        }
      });

      return searchData;
    }
    return tableTree;
  }, [searchVal, tableTree]);

  const checkAll = getAllTableKeys().length === chooseTableKeys.length;
  const indeterminate =
    chooseTableKeys.length > 0 &&
    chooseTableKeys.length < getAllTableKeys().length;

  return (
    <div className="p-[12px] flex flex-col h-[376px]">
      <Input
        placeholder="搜索数据表名称"
        className="w-[240px] h-[32px] mb-[12px]"
        suffix={
          <SearchOutlined
            style={{ color: "#999", fontSize: 16 }}
            onClick={() => {}}
          />
        }
        onChange={(e) => {
          setSearchVal(e.target.value);
        }}
      />

      <Checkbox
        onChange={onAllSelect}
        checked={checkAll}
        indeterminate={indeterminate}
      >
        全选
      </Checkbox>
      <Tree
        className="mt-[8px] ml-[-6px] overflow-y-auto"
        checkable
        onSelect={onSelect}
        onCheck={onCheck}
        defaultCheckedKeys={[...chooseTableKeys]}
        checkedKeys={chooseTableKeys}
        treeData={treeData}
        showIcon={true}
        fieldNames={{
          title: "name",
          children: "tables"
        }}
      />
    </div>
  );
};

export default SelectTable;
