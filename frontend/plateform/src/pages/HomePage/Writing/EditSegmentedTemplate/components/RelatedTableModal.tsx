import { useEffect, useState, useCallback } from "react";
import { Modal, Button } from "antd";
import loading from "@/assets/gif/loading.gif";
import SelectTable from "./SelectTable";
import TableDetail from "./TableDetail";
import { useServices } from "../service.ts";
import mysqlIcon from "@/assets/svg/mysql.svg";
import mongoIcon from "@/assets/svg/mongo.svg";
import db_table from "@/assets/img/db_table.png";
import defaultDbIcon from "@/assets/svg/db.svg";
import { filterTreeByIds, findTableList } from "../utils.ts";

import { v4 as uuid } from "uuid";

interface Iprops {
  isModalOpen: boolean;
  relationTables: any[];
  isCustomize?: boolean;
  setDbTreeData?: (list: any) => void;
  onClose: () => void;
  onConfirm: (chooseInfo: { tableList: any[]; tableTree: any }) => void;
}

const dbIcon: any = {
  0: mysqlIcon,
  1: mongoIcon
};

const RelatedTableModal = ({
  isModalOpen,
  relationTables,
  isCustomize = false,
  onClose,
  onConfirm,
  setDbTreeData
}: Iprops) => {
  const [chooseTableKeys, setChooseTableKeys] = useState<number[]>([]);
  const [tableTree, setTableTree] = useState<any[]>([]);
  const { getTableTree, getTableDetail } = useServices();
  const [tableDetail, setTableDetail] = useState();
  const [isLoading, setIsLoading] = useState(false);

  const getTableTreeData = useCallback(async () => {
    const treeData = await getTableTree();

    // 获取树,唯一key值
    const treeByUniqueId = treeData.map((db: any) => {
      const { tables, type, name } = db;
      const children = (tables || []).map((t: any) => {
        return {
          ...t,
          key: t.id,
          dbName: name,
          isLeaf: true,
          icon: (
            <div className="relative mr-2">
              <img src={db_table} width={16} className="mt-[5px]" />
            </div>
          ),
          title: t.name,
          iconType: "table",
          depth: 2
        };
      });
      return {
        ...db,
        key: uuid(),
        isLeaf: false,
        icon: (
          <img
            src={dbIcon[type] || defaultDbIcon}
            width={22}
            className="mr-2 mt-[4px]"
          />
        ),
        title: name,
        iconType: "db",
        depth: 1,
        children: [...children],
        tables: [...children]
      };
    });
    setDbTreeData && setDbTreeData(treeByUniqueId);
    setTableTree(treeByUniqueId);
  }, []);

  useEffect(() => {
    if (isModalOpen) {
      // getTableTreeData();
      setChooseTableKeys([...(relationTables || [])]);
    }
  }, [isModalOpen, getTableTreeData, relationTables]);

  useEffect(() => {
    getTableTreeData();
  }, []);

  const handleSelectedTable = async (id: any) => {
    try {
      setIsLoading(true);
      const res = await getTableDetail(id);
      setTableDetail(res);
      setIsLoading(false);
    } catch (e) {
      console.log("Get table detail err-------->", e);
    }
  };

  const submit = () => {
    const list = findTableList(tableTree, chooseTableKeys);
    const tree = filterTreeByIds(tableTree, chooseTableKeys);

    onConfirm &&
      onConfirm({
        tableList: list,
        tableTree: tree
      });
  };

  return (
    <Modal
      title="选择数据表"
      width={1200}
      height={650}
      open={isModalOpen}
      onCancel={onClose}
      destroyOnClose
      footer={null}
    >
      <div className="h-[400px] flex flex-row justify-between border-[#eeeeee] border-solid border-[1px] rounded-[4px]">
        <SelectTable
          tableTree={tableTree}
          chooseTableKeys={chooseTableKeys}
          setChooseTableKeys={setChooseTableKeys}
          handleSelectedTable={handleSelectedTable}
        />
        {isLoading ? (
          <div className="w-full h-full flex justify-center items-center">
            <img src={loading} width={36} />
          </div>
        ) : (
          <TableDetail tableDetail={tableDetail} />
        )}
      </div>

      <div className="w-full mt-[20px] flex flex-row justify-between align-center">
        <div className="text-sm text-[#2a2a2a] leading-[32px]">
          已选中 数据表
          <span className="text-sm text-[#888]">
            {chooseTableKeys?.length || 0}个
          </span>
        </div>
        <div className=" flex flex-row justify-end align-center">
          <Button
            type="primary"
            onClick={onClose}
            style={{
              color: `#555555`,
              backgroundColor: "#fff",
              borderRadius: "4px",
              border: "1px solid #dedede"
            }}
          >
            取消
          </Button>
          <Button
            ghost
            // disabled={isCustomize && chooseTableKeys.length === 0}
            onClick={submit}
            style={{
              background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
              color: "#fff",
              border: "none",
              marginLeft: "10px"
            }}
          >
            确定
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default RelatedTableModal;
