import { useEffect, useMemo, useState } from "react";
import {
  deleteFaqFileById,
  faqParse,
  getFAQExtractStatusById,
  getFaqFileList
} from "./faqService";
import { message } from "antd";
let faqPollingInterval = null as any;
const initialPage = {
  pageNo: 1,
  pageSize: 10
};
const faqPollingTime = 5000;
export const useFAQTableController = ({
  knowledgeBaseId,
  kbInfo,
  isShowLogModal,
  setIsShowLogModal,
  curRow,
  setCurRow
}: any) => {
  const [uploadFaqModalOpen, setUploadFaqModalOpen] = useState(false);
  const [faqTableLoading, setFaqTableLoading] = useState(false);
  const [faqFileCount, setFaqFileCount] = useState(0);
  const [faqFileList, setFaqFileList] = useState<any[]>([]);
  const [faqPollingItemList, setFaqPollingItemList] = useState<Array<number>>(
    []
  );
  const [faqFileIds, setFaqFileIds] = useState<Array<number>>([]);
  const [faqPage, setFaqPage] = useState(initialPage);
  const [faqSelectedRowKeys, setFaqSelectedRowKeys] = useState<React.Key[]>([]);
  const [faqSelectedRows, setFaqSelectedRows] = useState([]);
  const [faqPollingResult, setFaqFaqPollingResult] = useState<EXTRACT_STATUS>(
    EXTRACT_STATUS.SUCCESS
  );
  const fetchFaqFileList = async (fuzzyNameOrId?: string) => {
    try {
      setFaqTableLoading(true);
      const param: any = {
        ...faqPage,
        kbId: knowledgeBaseId,
        pageNo: fuzzyNameOrId ? 1 : faqPage.pageNo,
        fileListType: 2
      };
      if (fuzzyNameOrId !== undefined) {
        param.fuzzyNameOrId = fuzzyNameOrId;
      }
      const res = await getFaqFileList(param);
      setFaqTableLoading(false);
      if (res) {
        const { records, total } = res;
        const _records = (records || []).map((item: any) =>
          Object.assign({}, item, {
            key: item.id
          })
        );
        setFaqFileList([..._records]);
        setFaqFileCount(total || 0);
      }
    } catch (e) {
      setFaqTableLoading(false);
    }
  };

  const onFaqPageSizeChange = (pageNo: number, pageSize: number) => {
    setFaqPage({
      pageNo,
      pageSize
    });
  };
  const faqRowSelection = {
    onChange: (_selectedRowKeys: React.Key[], _selectedRows: any) => {
      console.log(
        `faqSelectedRowKeys: ${_selectedRowKeys}`,
        "faqSelectedRows: ",
        _selectedRows
      );
      setFaqSelectedRowKeys(_selectedRowKeys);
      setFaqSelectedRows(_selectedRows);
    },
    faqSelectedRowKeys
  };

  const parseFilePath = (filePath: string) => {
    const pathArr = filePath.split("/");
    return pathArr.splice(3).join("/");
  };

  const handleFaqAnalysis = async (item: any, items?: any) => {
    let _files = [];
    let _fileIds = [] as number[];
    if (item) {
      _files.push({
        file_path: item?.filePath ? parseFilePath(item?.filePath) : "",
        file_size: `${item?.fileSize || 0}MB`,
        file_id: item.id
      });
      _fileIds = [Number(item.id)];
    } else {
      const _selectedRows = (faqSelectedRows || []).filter(
        (s: any) => s.faqExtractStatus !== EXTRACT_STATUS.SUCCESS
      );
      if (!_selectedRows.length) return message.warning("暂无可以解析的问题件");
      _fileIds = _selectedRows.map((s: any) => Number(s.id));
      _files = _selectedRows.map((item: any) => {
        return {
          file_path: item?.filePath ? parseFilePath(item?.filePath) : "",
          file_size: `${item?.fileSize || 0}MB`,
          file_id: item.id
        };
      });
    }
    setFaqPollingItemList([..._fileIds]);

    const params: any = {
      files: _files,
      knowledge_base_name: kbInfo?.kbName,
      knowledge_base_id: kbInfo.id,
      override: true
    };
    if (_fileIds.length) {
      try {
        setFaqTableLoading(true);
        const res = await faqParse(params);
        setFaqTableLoading(false);
        if (res) {
          message.info("开始抽取文件", 2);
          // 启动轮询
          fetchFaqFileList();
          const _ids = Array.from(new Set([...faqFileIds, ..._fileIds]));
          startFaqPolling(_ids);
        }
      } catch (e) {
        setFaqTableLoading(false);
      }
    }
  };

  const clearFaqPollingInterval = () => {
    if (faqPollingInterval) {
      clearInterval(faqPollingInterval);
      faqPollingInterval = null;
    }
  };

  const startFaqPolling = (ids: number[]) => {
    clearFaqPollingInterval();
    faqPollingInterval = setInterval(() => {
      Promise.all(
        ids.map((id: number) => getFAQExtractStatusById({ fileId: Number(id) }))
      )
        .then((res: any) => {
          const _list = (res || []).map(
            (sta: EXTRACT_STATUS, index: number) => {
              return { id: ids[index], sta };
            }
          );
          const _doneList = _list.filter((item: any) =>
            [EXTRACT_STATUS.FAILURE, EXTRACT_STATUS.SUCCESS].includes(item.sta)
          );
          const _notDoneList = _list
            .filter((item: any) =>
              [EXTRACT_STATUS.EXTRACTING].includes(item.sta)
            )
            .map((i: any) => i.id);
          setFaqPollingItemList(_notDoneList);

          // console.log("has done:", JSON.stringify(_doneList))
          if (_doneList.length === ids.length) {
            // console.log("done")
            clearFaqPollingInterval();
            fetchFaqFileList();
            if (
              faqPollingResult === EXTRACT_STATUS.FAILURE ||
              _doneList[0].sta === EXTRACT_STATUS.FAILURE
            ) {
              message.warning(
                `分析结束，${
                  faqSelectedRowKeys.length > 1
                    ? "有文件分析失败，请查看列表结果！"
                    : "解析失败！"
                }`
              );
              setFaqFaqPollingResult(EXTRACT_STATUS.SUCCESS);
            } else {
              message.success("抽取完成！");
            }
            setFaqFileIds([]);
          } else {
            // console.log("not done")
            _doneList.forEach((item: any) => {
              const _index = ids.findIndex((id: number) => id === item.id);
              console.log("splice:", JSON.stringify(item));
              ids.splice(_index, 1);
              if (
                faqPollingResult === EXTRACT_STATUS.SUCCESS &&
                item.sta === EXTRACT_STATUS.FAILURE
              ) {
                setFaqFaqPollingResult(item.sta);
              }
            });
            setFaqFileIds([...ids]);
            if (_doneList.length) {
              fetchFaqFileList();
            }
          }
        })
        .catch((e) => {
          console.log(e);
          clearFaqPollingInterval();
        });
    }, faqPollingTime);
  };

  const deleteFaqFileByIds = async (ids: Array<string | number>) => {
    try {
      setFaqTableLoading(true);
      const res = await deleteFaqFileById(ids.join(","));
      setFaqTableLoading(false);
      if (res) {
        message.success("文件删除成功！", 2);
        setFaqPage((pre) => {
          return { ...pre, pageNo: 1 };
        });
        fetchFaqFileList();
      } else {
        message.success("文件删除失败！", 2);
      }
    } catch (e) {
      setFaqTableLoading(false);
      message.success("文件删除失败！", 2);
    }
  };

  useEffect(() => {
    fetchFaqFileList();
  }, [faqPage]);

  return {
    faqFileCount,
    deleteFaqFileByIds,
    faqPage,
    faqRowSelection,
    onFaqPageSizeChange,
    faqSelectedRows,
    handleFaqAnalysis,
    faqPollingItemList,
    faqFileList,
    fetchFaqFileList,
    faqTableLoading,
    uploadFaqModalOpen,
    setUploadFaqModalOpen,
    isShowLogModal,
    setIsShowLogModal,
    curRow,
    setCurRow
  };
};
