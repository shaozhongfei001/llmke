import { ChangeEventHandler, useEffect, useMemo, useState } from "react";
import { EXTRACT_STATUS } from "@/const/knowledgebase";
import {
  createLibrary,
  deleteLibrary,
  getLibraryList,
  updateLibrary
} from "./sensiveService";
import { message } from "antd";
import { useNavigate } from "react-router-dom";
const initialPage = {
  pageNo: 1,
  pageSize: 10
};

export let sensitiveTableControllerType: any = {};
export const useSensitiveTableController = () => {
  const navigator = useNavigate();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [listCount, setListCount] = useState(0);
  const [tableList, setTableList] = useState<any[]>([]);
  const [page, setPage] = useState(initialPage);
  const [fuzzyNameOrId, setFuzzyNameOrId] = useState("");
  const [openType, setOpenType] = useState("add");
  const [editData, setEditData] = useState({});
  const [modalConfirmLoading, setModalConfirmLoading] = useState(false);

  const fuzzyNameOrIdOnChange: ChangeEventHandler<HTMLInputElement> = (e) => {
    const inputElement = e.target as HTMLInputElement;
    setFuzzyNameOrId(inputElement.value.trim());
    // setPage({
    //   pageNo: 1,
    //   pageSize: 10
    // });
  };

  const fetchList = async () => {
    try {
      setTableLoading(true);
      const param: any = {
        ...page
      };
      if (fuzzyNameOrId !== undefined) {
        param.name = fuzzyNameOrId;
      }
      const res = await getLibraryList(param);
      setTableLoading(false);
      if (res) {
        const { records, total } = res;
        const _records = (records || []).map((item: any) =>
          Object.assign({}, item, {
            key: item.id
          })
        );
        setTableList([..._records]);
        setListCount(total || 0);
      }
    } catch (e) {
      setTableLoading(false);
    }
  };

  const onPageSizeChange = (pageNo: number, pageSize: number) => {
    setPage({
      pageNo,
      pageSize
    });
  };

  const deleteByIds = async (ids: Array<string | number>) => {
    try {
      setTableLoading(true);
      const res = await deleteLibrary(ids[0]);
      setTableLoading(false);
      if (res) {
        message.success("删除成功！", 2);
        setPage((pre) => {
          return { ...pre, pageNo: 1 };
        });
        fetchList();
      } else {
        message.error("删除失败！", 2);
      }
    } catch (e) {
      setTableLoading(false);
      message.error("删除失败！", 2);
    }
  };

  const handleSearch = () => {
    setPage({
      pageNo: 1,
      pageSize: 10
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const fetchCreate = async (data: any, cb?: any) => {
    try {
      setModalConfirmLoading(true);
      const res = await createLibrary({
        name: data.name,
        words: []
      });
      setModalConfirmLoading(false);
      if (res) {
        message.success("新增敏感词成功!");
        cb && cb(res);
      } else {
        //message.error("新增敏感词失败!");
      }
    } catch (e) {
      setModalConfirmLoading(false);
      message.error("新增敏感词失败!");
    }
  };

  const handleEvent = (type: string, data: any) => {
    switch (type) {
      case "detail":
        navigator(`detail/${data.id}`);
        break;
      case "edit":
        setEditData(data);
        setOpenType("edit");
        setShowCreateModal(true);
        break;
      case "createOrEdit":
        fetchCreate(data, (res: any) => {
          navigator(`add/${res}`);
        });

        break;
    }
  };

  useEffect(() => {
    fetchList();
  }, [page]);

  const res = {
    fuzzyNameOrId,
    showCreateModal,
    setShowCreateModal,
    listCount,
    deleteByIds,
    page,
    onPageSizeChange,
    tableList,
    fetchList,
    tableLoading,
    fuzzyNameOrIdOnChange,
    handleKeyDown,
    openType,
    setOpenType,
    handleEvent,
    editData,
    modalConfirmLoading,
    handleSearch
  };

  sensitiveTableControllerType = typeof res;

  return res;
};
