import { DrawerStyles } from "antd/es/drawer/DrawerPanel";
import {
  ChangeEventHandler,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import {
  faqBatchType,
  faqBatchlist,
  ANALYSIS_STATUS,
  chatPathPrefix,
  tabItems,
  detailTypes
} from "@/const/knowledgebase";
import {
  addSimilarQuestion,
  batchTransferFolder,
  changeStatus,
  createFaq,
  deleteAll,
  deleteFaq,
  deleteFaqFolder,
  deleteFaqSimilarByPks,
  deleteFaqSimilarQuestion,
  faqPolish,
  filegetById,
  generateSimilarQuestion,
  getFaqList,
  getKbById,
  reExtractFAQ,
  setFolderTransfer,
  similarQuestionEdit,
  updateFaq
} from "./faqService";
import { message } from "antd";
import { UPLOAD_EVENTS } from "../components/UploadBox";
import { useServices } from "../service";
import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";
import { TypeDrawConfig } from "@root/src/pages/Components/PermissionConfig";
const initialCrumbs = [{ id: null, name: "全部文件", dataType: 1 }];
enum DelType {
  SIMILAR = "similar",
  QA = "qa"
}

export enum rowActionType {
  FOLDER_RENAME = "folder_rename",
  CLICK_FOLDER = "click_folder",
  PERMISSION = "permission",
  TRANSFER = "transfer",
  OPEN_SIMILAR = "open_similar",
  FAQ_POLISH = "faq_Polish",
  CHECK_QA = "check_qa",
  DELETE_QA = "delete_qa",
  DELETE_FOLDER = "delete_folder",
  EDIT_QA = "edit_qa",
  CANCLE_EDIT_QA = "cancle_edit_qa",
  SUBMIT_EDIT_QA = "submit_edit_qa",
  CHANGE_STATUS_QA = "change_status_qa",
  EXPAND_SIMILAR = "expand_similar",
  ADD_SIMILAR = "add_similar",
  CANCLE_ADD_SIMILAR = "cancle_add_similar",
  SUBMIT_ADD_SIMILAR = "submit_add_similar",
  DELETE_SIMILAR = "delete_simlilar",
  EDIT_SIMILAR = "edit_similar",
  SUBMIT_EDIT_SIMILAR = "submit_edit_similar",
  SAVE_TAGS = "saveTags",
  OPEN_TAGS = "open_tags"
}

const allBatchIdx = 99999999;
let pollingInterval = null as any;
const pollingTime = 5000;
let polishContentTimer: any = null;
let stopPolish = false;
export interface ICrumbs {
  id: number | null;
  name: string;
  dataType: number;
}

export const useFaqController = ({
  knowledgeBaseId,
  fileId,
  navigator,
  state,
  kbInfo,
  pathPrefix = chatPathPrefix,
  params
}: any) => {
  const {
    getFaqExtractStatusById,
    saveBizLabel,
    getBizLabelList,
    createFolder,
    renameFolder
  } = useServices();
  const drawerStyles: DrawerStyles = {
    mask: {
      background: "transparent"
    },
    content: {
      boxShadow: "-10px 0 10px #666"
    },
    header: { display: "none" },
    body: { padding: 0 },
    footer: {}
  };
  const [faqInfo, setFaqInfo]: any = useState({});
  const [showSpin, setShowSpin] = useState(false);
  const [faqData, setFaqData]: any = useState([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [page, setPage] = useState({ pageNo: 1, pageSize: 10 });
  const [total, setTotal] = useState(0);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [similarLoading, setSimilarLoading] = useState("");
  const [polishLoading, setPolishLoading] = useState(false);
  const [polishBtnLoading, setPolishBtnLoading] = useState(false);
  const [batchValue, setBatchValue] = useState(null);
  const [polishContentPage, setPolishContentPage]: any = useState({
    pageNo: 1
  });
  const [isCheckRepeatShow, setIsCheckRepeatShow] = useState<boolean>(false);
  const [repeatList, setRepeatList] = useState<Array<any>>([]);
  const [isBatchEnable, setIsBatchEnable] = useState<boolean>(false);
  const [editQaPk, setEditQaPk] = useState<string | undefined>(undefined);
  const [openDrawer, setOpenDrawer] = useState(false);
  const [addSimilarQaPk, setAddSimilarQaPk] = useState<string | undefined>(
    undefined
  );
  const [editQuestion, setEditQuestion] = useState("");
  const [editAnswer, setEditAnswer] = useState("");
  const [folder, setFolder] = useState<any>(null);
  const [type, setType] = useState("add");
  const [curItem, setCurItem] = useState<any>(null);
  const [curSimilarList, setCurSimilarList] = useState([]);
  const [curSimilarParentList, setCurSimilarParentList] = useState<any>();
  const [curPolishContent, setCurPolishContent] = useState("");
  const [polishContentList, setPolishContentList]: any = useState([]);
  const [checkAll, setCheckAll]: any = useState();
  const [expandSimilarQaPk, setExpandSimilarQaPk] = useState<
    string | undefined
  >(undefined);
  const [editSimilarPk, setEditSimilarPk] = useState<string | undefined>(
    undefined
  );
  const [fuzzy, setFuzzy] = useState("");
  const [isCreateFolderShow, setIsCreateFolderShow] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [crumbs, setCrumbs] = useState<any>([]);
  const [newFolderName, setNewFolderName] = useState("");
  const [editFolder, setEditFolder] = useState<any>(undefined);
  const faqCrumbsRef = useRef<Array<ICrumbs>>([...initialCrumbs]);
  const crumbsOnChange = (items: Array<ICrumbs>) => {
    faqCrumbsRef.current = [...items];
    setCrumbs([...items]);
    //resetPageNo();
    setPage((pre) => {
      return { ...pre, pageNo: 1 };
    });
  };
  const closeCreateFolder = () => {
    setIsCreateFolderShow(false);
    setNewFolderName("");
  };
  const enterFolder = (r: any) => {
    const { folderId, name, dataType } = r;
    const _tempCrumbs = faqCrumbsRef.current;
    const _crumbs = [...[..._tempCrumbs, { id: folderId, name, dataType }]];
    // console.log("*******进入*********", _crumbs, "**********进入*******");
    crumbsOnChange(_crumbs);
  };
  const returnFolder = (id: number | null) => {
    let _crumbs: Array<ICrumbs> = [...initialCrumbs];
    if (id !== null) {
      const _tempCrumbs = faqCrumbsRef.current;
      const idx = _tempCrumbs.findIndex((i: any) => i.id === id);
      _crumbs = [..._tempCrumbs.slice(0, idx + 1)];
      //   console.log("*******返回*********", _crumbs, "**********返回*******");
    }
    crumbsOnChange(_crumbs);
  };
  const newFolderNameOnChange: ChangeEventHandler<HTMLInputElement> = (e) => {
    const inputElement = e.target as HTMLInputElement;
    setNewFolderName(inputElement.value.trim());
  };
  const getCurFolderId = () => {
    const _crumbs = faqCrumbsRef.current;
    return _crumbs.length ? _crumbs[_crumbs.length - 1].id : null;
  };
  const getCurFolder = () => {
    const _crumbs = faqCrumbsRef.current;
    return _crumbs.length ? _crumbs[_crumbs.length - 1] : null;
  };
  const createFolderConfirm = () => {
    const curFolderId = getCurFolderId();
    const _params = {
      name: newFolderName,
      kbId: params.id,
      parentId: curFolderId,
      type: 4
    } as any;
    const isEdit = !!(editFolder && (editFolder.fileId || editFolder.folderId));
    if (isEdit) {
      _params.id =
        editFolder.dataType === 2 ? editFolder.fileId : editFolder.folderId;
    }
    const _api = isEdit ? renameFolder : createFolder;
    setTableLoading(true);
    _api(_params)
      .then((res: any) => {
        if (res) {
          message.success(`${isEdit ? "重命名" : "创建"}成功！`);
          fetchFaqList();
          closeCreateFolder();
        }
      })
      .finally(() => {
        setTableLoading(false);
      })
      .catch((e) => {
        console.log(e);
      });
  };

  const checkedNums = useMemo(() => {
    return faqData.filter((f: any) => f.isChecked).length;
  }, [faqData]);

  useEffect(() => {
    if (faqData.length && checkedNums === faqData.length) {
      if (!checkAll) {
        setCheckAll(1);
      }
    } else {
      setCheckAll(undefined);
    }
  }, [checkedNums, faqData]);

  const isFaqManage = useMemo(() => {
    return fileId === "all";
  }, [fileId]);

  const isAnyChecked = useMemo(() => {
    return (faqData || []).some((f: any) => f.isChecked) || checkAll === 2;
  }, [faqData, checkAll]);

  const batch_operations = useMemo(() => {
    return faqBatchlist.map((item: any) =>
      Object.assign({}, item, {
        disabled:
          (item.canDisabled && !isAnyChecked) ||
          getBtnDisabled(
            item.value === faqBatchType.DELETE ||
              item.value === faqBatchType.SIMILAR_DELETE
              ? FILE_BTN.DELETE
              : FILE_BTN.ADD,
            (kbInfo || faqInfo).permission
          )
      })
    );
  }, [isAnyChecked]);

  const goBack = () => {
    navigator(`${pathPrefix}/${knowledgeBaseId}`, {
      state: {
        prevTabKey:
          state && state.prevTabKey ? state.prevTabKey : tabItems[0].key,
        prevDetailType:
          state && state.prevDetailType
            ? state.prevDetailType
            : detailTypes[0].key
      }
    });
  };

  const fetchKBDetail = async () => {
    if (knowledgeBaseId) {
      const res = await getKbById(knowledgeBaseId);
      if (res) {
        const { permission } = res;
        if (permission === 0) {
          message.error("暂无操作权限，请联系管理员申请");
          return;
        }
        setFaqInfo({ ...Object.assign({}, res, { title: res.kbName }) });
      }
    }
  };

  const getFileById = async () => {
    if (knowledgeBaseId) {
      const res = await filegetById(fileId);
      if (res) {
        setFaqInfo({ ...Object.assign({}, res, { title: res.fileName }) });
      }
    }
  };

  const typewriterEffect = (answer: string, type?: string) => {
    if (stopPolish) {
      stopPolish = false;
      return;
    }
    let displayText = "";
    let index = 0;

    polishContentTimer = setInterval(() => {
      stopPolish = false;
      const chunkSize = Math.floor(Math.random() * 5) + 3;
      if (index < answer.length) {
        displayText += answer.slice(index, index + chunkSize);
        index = index + chunkSize;
        if (type === "reGenerate") {
          setPolishContentList((pre: any) => {
            pre[polishContentPage.pageNo - 1] = displayText;
            return [...pre];
          });
          setCurPolishContent(displayText);
        } else {
          setPolishContentList((pre: any) => {
            pre[0] = displayText;
            return [...pre];
          });
          setCurPolishContent(displayText);
        }
      } else {
        setPolishLoading(false);
        setPolishBtnLoading(false);
        clearInterval(polishContentTimer);
      }
    }, 50);
  };

  const toFaqPolish = async (type?: string) => {
    try {
      setPolishLoading(true);
      setPolishContentList((pre: any) => {
        return ["", ...pre];
      });
      setCurPolishContent("");
      setPolishContentPage({ pageNo: 1 });
      const res = await faqPolish({
        kbId: knowledgeBaseId,
        fileId: curItem.fileId ? curItem.fileId : undefined,
        pks: [curItem.pk]
      });

      if (res.length) {
        typewriterEffect(res[0].answer || "", type);
      } else {
        setPolishLoading(false);
        setPolishBtnLoading(false);
      }
    } catch (error) {
      setPolishLoading(false);
      setPolishBtnLoading(false);
      console.log("error", error);
    }
  };

  const onPolishPageSizeChange = ({
    pageNo,
    pageSize
  }: {
    pageNo: number;
    pageSize: number;
  }) => {
    setCurPolishContent(polishContentList[pageNo - 1]);
    setPolishContentPage({
      pageNo
    });
  };

  const isFolder = (record: any) => {
    return record.dataType === 1;
  };

  const fetchFaqList = async (pNo?: number, cb?: (res?: any) => void) => {
    if (!fileId) {
      return message.warning("id为空");
    }
    const { pageNo, pageSize } = page;

    let _params: any = null;
    if (isFaqManage) {
      _params = {
        kbId: knowledgeBaseId,
        pageNo: pNo || pageNo,
        pageSize: pageSize,
        fuzzy
      };
      const curFolder = getCurFolder();
      if (curFolder && curFolder.id) {
        if (curFolder.dataType === 2) {
          _params.fileId = curFolder.id;
          _params.folderId = curFolder.id;
        } else if (curFolder.dataType === 1) {
          _params.folderId = curFolder.id;
        }
      }
    } else {
      _params = {
        fileId,
        kbId: knowledgeBaseId,
        pageNo: pNo || pageNo,
        pageSize: pageSize,
        fuzzy
      };
    }

    setShowSpin(true);
    try {
      const res = await getFaqList(_params);
      setShowSpin(false);
      if (res) {
        const { records, total } = res;
        setFaqData([
          ...(records || []).map((i: any) =>
            Object.assign({}, i, {
              isChecked: false,
              isEdit: false,
              isSimilarExpand: false,
              isSimilarAdd: false
            })
          )
        ]);
        if (type === "similar" && openDrawer) {
          setCurSimilarList(
            (
              records.find(
                (item: any) => item.relatedPk === curSimilarParentList.relatedPk
              )?.similarQuestions || []
            ).map((item: any) => {
              return { similarQuestion: item.question, key: item.pk };
            }) || []
          );
        }
        setTotal(total);
        cb && cb(res);
      } else {
        // 接口不可用时如实提示，不静默当空列表（R13 FAQ 最小可用要求）
        setFaqData([]);
        setTotal(0);
        message.error("FAQ 列表加载失败，请检查服务是否可用");
      }
    } catch (e) {
      setShowSpin(false);
      message.error("FAQ 列表加载异常，请检查服务是否可用");
    }
  };

  const getBizType = (data: any) => {
    if (isFaqManage) {
      return data.dataType === 1 ? 8 : data.dataType === 2 ? 10 : 7;
    } else {
      return isFolder(data) ? 6 : 4;
    }
  };
  const transferFn = async (param: {
    targetFolderId: number;
    targetId: number;
  }) => {
    try {
      setBtnLoading(true);

      const res: any = await setFolderTransfer({
        ...param,
        bizType: getBizType(drawConfig.data),
        kbName: kbInfo.primitiveName
      });
      setBtnLoading(false);
      if (res.success) {
        message.success("转移成功");
        fetchFaqList();
        setOpenDraw(false);
      }
    } catch (error) {
      setBtnLoading(false);
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  const transferBatchFn = async (param: {
    targetFolderId: number;
    target: any[];
  }) => {
    try {
      setBtnLoading(true);
      const res: any = await batchTransferFolder({
        ...param
      });
      setBtnLoading(false);
      if (res.success) {
        message.success("转移成功");
        fetchFaqList();
        setOpenDraw(false);
      }
    } catch (error) {
      setBtnLoading(false);
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };
  const handleEvent = async (type: string, d?: any, cb?: () => void) => {
    switch (type) {
      case "save:transfer":
        if (Array.isArray(drawConfig.data)) {
          transferBatchFn(d);
        } else {
          transferFn(d);
        }
        break;
      case UPLOAD_EVENTS.FILE_UPLOADED:
        fetchFaqList();
        break;
    }
  };

  const deleteSimilar = async (batch?: boolean, param?: any) => {
    try {
      setShowSpin(true);
      if (checkAll == 2) {
        const res = await deleteFaqSimilarQuestion({
          kbId: knowledgeBaseId
        });
        setShowSpin(false);
        if (res) {
          setTimeout(() => {
            setPage((pre) => {
              return { ...pre, pageNo: 1 };
            });
          }, 800);
        } else {
          message.error("删除失败");
        }
      } else {
        let params: any = { kbId: knowledgeBaseId };
        if (!batch) {
          params = { ...params, ...param };
        } else {
          const { fileIds, folderIds, relatedPks }: any = getTIds(
            faqData.filter((f: any) => f.isChecked)
          );

          if (fileIds?.length) params.fileIds = fileIds;
          if (folderIds?.length) params.folderIds = folderIds;
          if (relatedPks?.length) params.relatedPks = relatedPks;
        }
        const res = await deleteFaqSimilarQuestion(params);
        setShowSpin(false);
        if (res) {
          setPage((pre) => {
            return { ...pre, pageNo: 1 };
          });
        } else {
          message.error("删除失败");
        }
      }
    } catch (error) {
      setShowSpin(false);
      console.log("error");
    }
  };

  const deleteFaqSimilarByPksFn = async (param: any) => {
    try {
      setShowSpin(true);
      let params: any = { kbId: knowledgeBaseId, ...param };

      const res: any = await deleteFaqSimilarByPks(params);
      setShowSpin(false);
      if (res) {
        setPage((pre) => {
          return { ...pre, pageNo: 1 };
        });
      } else {
        message.error("删除失败");
      }
    } catch (error) {
      setShowSpin(false);
      console.log("error");
    }
  };

  const genSimilar = async () => {
    try {
      setShowSpin(true);
      if (checkAll == 2) {
        const res = await generateSimilarQuestion({
          kbId: knowledgeBaseId
        });
        setShowSpin(false);
        if (res) {
          setPage((pre) => {
            return { ...pre, pageNo: 1 };
          });
        } else {
          message.error("获取失败");
        }
      } else {
        const { fileIds, folderIds, relatedPks }: any = getTIds(
          faqData.filter((f: any) => f.isChecked)
        );
        const params: any = { kbId: knowledgeBaseId };
        if (fileIds?.length) params.fileIds = fileIds;
        if (folderIds?.length) params.folderIds = folderIds;
        if (relatedPks?.length) params.relatedPks = relatedPks;
        const res = await generateSimilarQuestion(params);
        setShowSpin(false);
        if (res) {
          setPage((pre) => {
            return { ...pre, pageNo: 1 };
          });
        } else {
          message.error("获取失败");
        }
      }
    } catch (error) {
      setShowSpin(false);
      console.log("error");
    }
  };

  const handleBatchMenu = (batchName: any) => {
    setIsBatchEnable(false);
    switch (batchName) {
      case faqBatchType.TRANSFER:
        setDrawConfig({
          type: "transfer",
          data: faqData.filter((f: any) => f.isChecked)
        });
        setOpenDraw(true);
        break;
      case faqBatchType.SIMILAR_DELETE:
        deleteSimilar(true);
        break;
      case faqBatchType.SIMILAR_GENERATE:
        genSimilar();
        break;
      case faqBatchType.ENABLE:
        if (checkAll === 2) {
          setIsBatchEnable(true);
          changeFaqStatus(true, [1, 2], allBatchIdx);
          return;
        }
        changeFaqStatus(
          true,
          faqData.filter((f: any) => f.isChecked && f.status !== 1)
        );
        break;
      case faqBatchType.FORBIDDEN:
        if (checkAll === 2) {
          setIsBatchEnable(true);
          changeFaqStatus(false, [1, 2], allBatchIdx);
          return;
        }
        changeFaqStatus(
          false,
          faqData.filter((f: any) => f.isChecked && f.status !== 0)
        );
        break;
      case faqBatchType.DELETE:
        if (checkAll === 2) {
          deleteQA(true, null, allBatchIdx);
        } else {
          deleteQA(true, null);
        }
        break;
    }
    setBatchValue(null);
  };

  const fuzzyOnChange: ChangeEventHandler<HTMLInputElement> = (e) => {
    const inputElement = e.target as HTMLInputElement;
    setFuzzy(inputElement.value.trim());
  };

  const faqUpdateOnChange = (idx: number, newData: { [key: string]: any }) => {
    setFaqData((pre: any) => {
      pre[idx] = { ...pre[idx], ...newData };
      return [...pre];
    });
  };

  const onCheckAllChange = (checked: any) => {
    const obj = { isChecked: false };
    if (checked) {
      obj.isChecked = true;
    }
    setFaqData(faqData.map((i: any) => Object.assign({}, i, { ...obj })));
  };

  const docKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      refreshList();
    }
  };

  const cancleCreate = () => {
    setOpenDrawer(false);
  };

  const onPageSizeChange = (pageNo: number, pageSize: number) => {
    setPage({
      pageNo,
      pageSize
    });
  };

  const clearPollingInterval = () => {
    setShowSpin(false);
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  };

  const startPolling = () => {
    clearPollingInterval();
    setShowSpin(true);
    pollingInterval = setInterval(async () => {
      try {
        const sta = await getFaqExtractStatusById(Number(faqInfo.id));
        switch (sta) {
          case ANALYSIS_STATUS.DELETE:
            message.warning("文件已删除");
            clearPollingInterval();
            break;
          case ANALYSIS_STATUS.NORMAL:
            clearPollingInterval();
            break;
          case ANALYSIS_STATUS.ANALYSISING:
          case ANALYSIS_STATUS.RE_ANALYSISING:
          case ANALYSIS_STATUS.PENDING:
          case ANALYSIS_STATUS.RETRY:
            break;

          case ANALYSIS_STATUS.SUCCESS:
            message.success("文件解析成功");
            clearPollingInterval();
            setPage((pre) => {
              return { ...pre, pageNo: 1 };
            });
            break;
          case ANALYSIS_STATUS.FAILURE:
            message.error("文件解析失败");
            clearPollingInterval();
            break;
        }
        console.log("====================================");
        console.log("getFaqExtractStatusById", res);
        console.log("====================================");
      } catch (error) {
        console.log("====================================");
        console.log(error);
        console.log("====================================");
      }
    }, pollingTime);
  };

  const changeBatch = async () => {
    try {
      const _params = {
        isExtract: true,
        knowledge_base_id: knowledgeBaseId,
        files: [
          {
            file_id: faqInfo.id,
            file_path: faqInfo.convertedFilePath.replace(
              /^http:\/\/[^/]+\//,
              ""
            ),
            file_size: faqInfo.fileSize,
            parent_file_name: faqInfo.parentFileName
          }
        ]
      };
      const res = await reExtractFAQ(_params);
      if (res) {
        setFaqData([]);
        startPolling();
      }
    } catch (error) {
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  const addNewQuestion = () => {
    cancleEditSimilarQuestion();
    setType("add");
    setCurItem(null);
    setOpenDrawer(true);
    // setIsAddNew(true);
    // const _el = document.querySelector(".list-content-wrap");
    // if (_el && _el.scrollTop) {
    //   _el.scrollTop = 0;
    // }
  };

  const isAll = (idx?: number) => {
    return idx && idx === allBatchIdx;
  };

  const getTIds = (checkedData: any[]) => {
    const fileIds = checkedData
      .filter((item: any) => {
        return item.dataType === 2;
      })
      .map((item: any) => item.fileId);
    const folderIds = checkedData
      .filter((item: any) => {
        return item.dataType === 1;
      })
      .map((item: any) => item.folderId);
    const relatedPks = checkedData
      .filter((item: any) => {
        return item.dataType === 3;
      })
      .map((item: any) => item.relatedPk);
    const pks = checkedData
      .filter((item: any) => {
        return item.dataType === 3;
      })
      .map((item: any) => item.pk);
    return { fileIds, folderIds, relatedPks, pks };
  };

  const changeFaqStatus = (
    checked: boolean,
    checkedData: Array<any>,
    idx?: number
  ) => {
    const txt = checked ? "启用" : "禁用";
    const status = checked ? 1 : 0;
    if (checkedData.length === 0) {
      message.warning("所选问答对已" + txt);
      return;
    }
    try {
      setConfirmLoading(true);

      const { fileIds, folderIds, relatedPks } = getTIds(checkedData);

      let params = {
        kbId: knowledgeBaseId,
        status
      } as any;

      if (isAll(idx)) {
        params = { kbId: knowledgeBaseId, status };
      } else {
        if (fileIds.length) {
          params.fileIds = fileIds;
        }
        if (folderIds.length) {
          params.folderIds = folderIds;
        }
        if (relatedPks.length) {
          params.relatedpks = relatedPks;
        }
      }

      changeStatus({ ...params }).then((res: any) => {
        const { data, success } = res;
        if (success) {
          if (data && data.length) {
            // message.error(`修改状态失败，有重复问题存在！`);
            // setIsRepeatShow(true);
            const _list = data || [];
            setRepeatList([..._list]);
            setTimeout(() => {
              setIsCheckRepeatShow(true);
            }, 500);
          } else {
            if (isAll(idx)) {
              setTimeout(() => {
                afterStatusChange(
                  faqData.map((f: any) => f.relatedPk),
                  status
                );
              }, 0);
            } else {
              if (relatedPks.length === 1) {
                if (idx || idx === 0) {
                  // 单数据开关切换状态
                  faqUpdateOnChange(idx, {
                    status
                  });
                } else {
                  // 单数据批量下拉切换状态
                  afterStatusChange(relatedPks, status);
                }
              } else {
                if (relatedPks.length > 1) {
                  // 多数据批量下拉切换状态
                  afterStatusChange(relatedPks, status);
                }
              }
            }
            message.success(`问答对${txt}成功！`);
          }
        } else {
          message.error(`问答对${txt}失败！`);
        }
        setConfirmLoading(false);
      });
    } catch (error) {
      setConfirmLoading(false);
      console.log("error", error);

      message.error(`问答对${txt}失败！`);
    }
  };

  const afterStatusChange = (relatedPks: Array<any>, status: number) => {
    const _list = (faqData || []).map((item: any) =>
      Object.assign({}, item, {
        status: relatedPks.includes(item.relatedPk) ? status : item.status
      })
    );
    setFaqData([..._list]);
  };

  const createQA = () => {
    try {
      const params: any = {
        kbId: knowledgeBaseId,
        faqs: [{ question: editQuestion, answer: editAnswer }]
      };
      if (!folder) {
        return message.warning("请选择文件夹");
      }
      setConfirmLoading(true);
      if (folder.dataType === 1) {
        params.folderId = folder.folderId;
      } else {
        params.fileId = folder.fileId;
      }
      createFaq(params).then((res: any) => {
        if (res) {
          cancleCreate();
          setPage((pre) => {
            return { ...pre, pageNo: 1 };
          });
          afterAddQA("新建问答对成功！");
        } else {
          message.error("新建问答对失败！");
          setConfirmLoading(false);
        }
      });
    } catch (error) {
      setConfirmLoading(false);
      message.error("新建问答对失败！");
    }
  };

  const afterAddQA = (txt: string) => {
    refreshList();
    const _el = document.querySelector(".list-content-wrap");
    if (_el && _el.scrollTop) {
      _el.scrollTop = 0;
    }
    setConfirmLoading(false);
    message.success(txt);
  };

  const submitEditQA = (row: any) => {
    const { status, pk, relatedPk, editAnswer, editQuestion } = row;
    try {
      setConfirmLoading(true);
      updateFaq({
        fileId: isFaqManage ? undefined : fileId,
        kbId: knowledgeBaseId,
        faqs: [
          { status, question: editQuestion, answer: editAnswer, pk, relatedPk }
        ]
      }).then((res: any) => {
        if (res) {
          setPage((pre) => {
            return {
              ...pre,
              pageNo: 1
            };
          });
          setEditQaPk(undefined);
          setOpenDrawer(false);
          message.success("编辑问答对成功！");
        } else {
          message.error("编辑问答对失败！");
        }
        setConfirmLoading(false);
      });
    } catch (error) {
      setConfirmLoading(false);
      message.error("编辑问答对失败！");
    }
  };

  const deleteFolder = (p: any) => {
    try {
      setSimilarLoading("del");
      const params = {
        kbId: knowledgeBaseId,
        ...p
      } as any;

      deleteFaqFolder({ ...params })
        .then((res: any) => {
          if (res) {
            fetchFaqList();
            message.success("删除成功!");
          } else {
            message.error("删除失败!");
          }
        })
        .finally(() => {
          setSimilarLoading("");
        });
    } catch (error) {
      setSimilarLoading("");
      message.error("删除失败!");
    }
  };

  const deleteQA = (
    batch: boolean,
    param: any,
    idx?: number,
    type?: DelType
  ) => {
    const _type = type || DelType.QA;
    try {
      setSimilarLoading("del");

      let p = {
        kbId: knowledgeBaseId
      } as any;

      if (batch) {
        const { fileIds, folderIds, relatedPks, pks }: any = getTIds(
          faqData.filter((f: any) => f.isChecked)
        );
        if (!isAll(idx)) {
          if (fileIds?.length) p.fileIds = fileIds;
          if (folderIds?.length) p.folderIds = folderIds;
          if (relatedPks?.length) p.relatedPks = relatedPks;
        }
      } else {
        p = {
          ...p,
          ...param
        };
      }

      deleteFaq({ ...p })
        .then((res: any) => {
          if (res) {
            if (isAll(idx)) {
              setFaqData([]);
              setTotal(0);
            }
            fetchFaqList();
            message.success("删除成功!");
          } else {
          }
        })
        .finally(() => {
          setSimilarLoading("");
        });
    } catch (error) {
      setSimilarLoading("");
    }
  };

  const afterDelQA = (relatedPks: Array<number>, type: DelType) => {
    const _list = [] as any;
    const { pageSize, pageNo } = page;

    switch (type) {
      case DelType.QA:
        // (faqData || []).forEach((item: any) => {
        //   if (!pks.includes(item.pk)) {
        //     _list.push({ ...item });
        //   }
        // });
        if (pageSize * (pageNo - 1) >= total - relatedPks.length) {
          setPage({
            pageSize,
            pageNo: pageNo > 1 ? pageNo - 1 : 1
          });
        } else {
          fetchFaqList();
        }

        break;
      case DelType.SIMILAR:
        // (faqData || []).forEach((item: any) => {
        //   const { similarQuestions } = item;
        //   const _similarQuestions = [] as any;

        //   (similarQuestions || []).forEach((i: any) => {
        //     if (!relatedPks.includes(i.relatedPk)) {
        //       _similarQuestions.push({ ...i });
        //     }
        //   });

        //   if (!relatedPks.includes(item.relatedPk)) {
        //     _list.push({
        //       ...Object.assign({}, item, {
        //         similarQuestions: [..._similarQuestions]
        //       })
        //     });
        //   }
        // });
        break;
    }
    setFaqData([..._list]);
  };

  const createSimilar = (row: any, cb?: () => void) => {
    const { relatedPk, pk, similarQuestion } = row;

    try {
      setSimilarLoading("save");
      addSimilarQuestion({
        fileId: isFaqManage ? undefined : fileId,
        kbId: knowledgeBaseId,
        relatedPk,
        pk,
        similarQuestion
      }).then((res: any) => {
        setSimilarLoading("");
        if (res) {
          setPage((pre) => {
            return { ...pre, pageNo: 1 };
          });
          cb && cb();
          setAddSimilarQaPk(undefined);
          afterAddQA("新建相似问成功！");
        } else {
          message.error("新建相似问失败！");
        }
      });
    } catch (error) {
      setSimilarLoading("");
      message.error("新建相似问失败！");
    }
  };

  const deleteSimilarConfirm = (pks: any, cb?: () => void) => {
    const p = pks.filter((item: any) => {
      return item.indexOf("add_") === -1;
    });
    rowActionHandler(
      rowActionType.DELETE_SIMILAR,
      {
        pks: p,
        idx: 0,
        type: DelType.SIMILAR
      },
      cb
    );
  };

  const repeatFaqCheck = () => {
    setIsCheckRepeatShow(true);
  };

  const uploadDone = (isRefresh: boolean) => {
    setShowUploadModal(false);
    isRefresh && refreshList();
  };

  const repeatFaqCheckDone = (refresh?: boolean) => {
    if (refresh === true) {
      setTimeout(refreshList, 1000);
    }
    setRepeatList([]);
    setIsBatchEnable(false);
    setIsCheckRepeatShow(false);
  };

  const cancleEditSimilarQuestion = () => {
    setEditQaPk(undefined);
    setEditSimilarPk(undefined);
    setAddSimilarQaPk(undefined);
  };

  const submitUpdateSimilar = (row: any, cb?: () => void) => {
    const { pk, similarQuestion } = row;
    const { relatedPk } = curItem;
    const params: any = {
      kbId: knowledgeBaseId,
      faqs: [
        {
          question: similarQuestion,
          answer: curItem.answer,
          pk,
          relatedPk
        }
      ]
    };
    fileId && fileId !== "all" && (params.fileId = fileId);

    try {
      setSimilarLoading("save");
      similarQuestionEdit({ ...params })
        .then((res: any) => {
          if (res) {
            cb && cb();
            fetchFaqList();
            cancleEditSimilarQuestion();
            message.success("编辑相似问成功！");
          } else {
            message.error("编辑相似问失败！");
          }
        })
        .finally(() => {
          cancleEditSimilarQuestion();
          setSimilarLoading("");
        });
    } catch (error) {
      setSimilarLoading("");
      message.error("编辑相似问失败！");
    }
  };

  const refreshList = () => {
    setPage({
      ...page,
      pageNo: 1
    });
  };
  const [openDraw, setOpenDraw] = useState(false);
  const [btnLoading, setBtnLoading] = useState(false);
  const [bizLabelList, setBizLabelList] = useState<any>([]);
  const [drawConfig, setDrawConfig] = useState<TypeDrawConfig>({
    type: "tag"
  });
  const getBizLabelListFn = async () => {
    const res = await getBizLabelList(params);
    if (res) {
      setBizLabelList(res || []);
    }
  };
  const saveBizLabelFn = async (data: any) => {
    try {
      setBtnLoading(true);
      const res: any = await saveBizLabel(data);
      setBtnLoading(false);
      if (res) {
        getBizLabelListFn();
        fetchFaqList();
        message.success("保存成功！");
        setOpenDraw(false);
      }
    } catch (error) {
      setBtnLoading(false);
      console.log(error);
    }
  };

  const rowActionHandler = (
    actionType: rowActionType,
    data: any,
    cb?: () => void
  ) => {
    console.log("data11111", data);

    const {
      pks,
      idx,
      type,
      pk,
      isChecked,
      relatedPks,
      folderName,
      fileName,
      dataType
    } = data;
    switch (actionType) {
      case rowActionType.FOLDER_RENAME:
        setEditFolder(data);
        setNewFolderName(dataType === 1 ? folderName : fileName);
        setIsCreateFolderShow(true);
        break;
      case rowActionType.CLICK_FOLDER:
        // 请求接口
        enterFolder(data);
        break;
      case rowActionType.PERMISSION:
        setDrawConfig({
          type: "permission",
          bizType: data.dataType === 1 ? 8 : 10,
          data: {
            ...data,
            id: data.dataType === 1 ? data.folderId : data.fileId
          }
        });
        setOpenDraw(true);
        break;
      case rowActionType.TRANSFER:
        setDrawConfig({
          type: "transfer",
          data: data
        });
        setOpenDraw(true);
        break;
      case rowActionType.OPEN_TAGS:
        setDrawConfig({
          type: "tag",
          data
        });
        setOpenDraw(true);
        break;
      case rowActionType.SAVE_TAGS:
        saveBizLabelFn({
          targetId:
            drawConfig.data.dataType === 1
              ? drawConfig.data.folderId
              : drawConfig.data.dataType === 2
              ? drawConfig.data.fileId
              : drawConfig.data.pk,
          label: data,
          bizType:
            drawConfig.data.dataType === 1
              ? 8
              : drawConfig.data.dataType === 2
              ? 10
              : 7,
          kbName: kbInfo.primitiveName
        });
        break;
      case rowActionType.OPEN_SIMILAR:
        setCurSimilarParentList(data);
        setCurSimilarList(
          (data.similarQuestions || []).map((item: any) => {
            return { similarQuestion: item.question, key: item.pk };
          }) || []
        );
        setCurItem(data);
        setType("similar");
        setOpenDrawer(true);
        break;
      case rowActionType.FAQ_POLISH:
        toFaqPolish();
        break;
      case rowActionType.CHECK_QA:
        faqUpdateOnChange(idx, {
          isChecked
        });
        break;
      case rowActionType.DELETE_QA:
        deleteQA(false, { relatedPks }, idx, type);
        break;
      case rowActionType.DELETE_FOLDER:
        deleteQA(
          false,
          data.dataType === 1
            ? { folderIds: [data.folderId] }
            : { fileIds: [data.fileId] },
          idx,
          type
        );

        break;
      case rowActionType.EDIT_QA:
        setCurItem(data);
        setAddSimilarQaPk(undefined);
        setEditQaPk(pk);
        break;
      case rowActionType.CANCLE_EDIT_QA:
        setOpenDrawer(false);
        setEditQaPk(undefined);
        break;
      case rowActionType.SUBMIT_EDIT_QA:
        submitEditQA(data);
        break;
      case rowActionType.CHANGE_STATUS_QA:
        changeFaqStatus(isChecked, relatedPks, idx);
        break;

      case rowActionType.EXPAND_SIMILAR:
        if (isChecked) {
          setExpandSimilarQaPk(pk);
        } else {
          setExpandSimilarQaPk(undefined);
        }
        break;
      case rowActionType.ADD_SIMILAR:
        cancleCreate();
        setEditQaPk(undefined);
        setAddSimilarQaPk(pk);
        setEditSimilarPk(undefined);
        break;
      case rowActionType.CANCLE_ADD_SIMILAR:
        setAddSimilarQaPk(undefined);
        break;
      case rowActionType.SUBMIT_ADD_SIMILAR:
        createSimilar(data, cb);
        break;
      case rowActionType.EDIT_SIMILAR:
        setEditSimilarPk(pk);
        break;
      case rowActionType.SUBMIT_EDIT_SIMILAR:
        submitUpdateSimilar(data);
        break;
      case rowActionType.DELETE_SIMILAR:
        deleteFaqSimilarByPksFn({ pks });
        break;
    }
  };

  const submitAddSimilar = (addSimilar: string, cb: () => void) => {
    const { relatedPk, pk } = curItem;
    rowActionHandler(
      rowActionType.SUBMIT_ADD_SIMILAR,
      {
        pk,
        relatedPk,
        similarQuestion: addSimilar
      },
      cb
    );
  };

  const cancleEditQa = () => {
    rowActionHandler(rowActionType.CANCLE_EDIT_QA, {});
  };

  const submitEditQa = () => {
    const { pk, relatedPk, idx, status } = curItem;
    rowActionHandler(rowActionType.SUBMIT_EDIT_QA, {
      idx,
      pk,
      relatedPk,
      editQuestion,
      editAnswer,
      status
    });
  };

  const submitQa = () => {
    type === "add" ? createQA() : submitEditQa();
  };

  const editQuestionOnChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setEditQuestion(e.target.value.trim());
  };

  const editAnswerOnChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setEditAnswer(e.target.value.trim());
  };

  const handlerPolish = (type: string, data: any) => {
    stopPolish = false;
    switch (type) {
      case "stop":
        stopPolish = true;
        setPolishLoading(false);
        setPolishBtnLoading(false);
        clearInterval(polishContentTimer);
        break;
      case "getPolish":
      case "reGenerate":
        toFaqPolish();
        break;
      case "polishPageChange":
        onPolishPageSizeChange(data);
        break;
      case "remove":
        setCurPolishContent("");
        setPolishContentList([]);
        setPolishContentPage({ pageNo: 1 });
        break;
      case "replace":
        setEditAnswer(curPolishContent);
        setCurPolishContent("");
        setPolishContentList([]);
        break;
      case "insert":
        setEditAnswer((pre) => {
          return pre + curPolishContent;
        });
        setCurPolishContent("");
        setPolishContentList([]);
        break;
    }
  };

  useEffect(() => {
    fetchFaqList();
  }, [page]);

  useEffect(() => {
    getBizLabelListFn();
    if (fileId) {
      isFaqManage ? fetchKBDetail() : getFileById();
    }
    return () => {
      clearPollingInterval();
      if (polishContentTimer) {
        clearInterval(polishContentTimer);
        polishContentTimer = null;
      }
    };
  }, []);

  const isCreatFolder = useMemo(() => {
    if (crumbs?.length) {
      const cur = crumbs[crumbs.length - 1];
      return cur.dataType === 1;
    }
    return true;
  }, [crumbs]);

  return {
    isCreatFolder,
    bizLabelList,
    drawConfig,
    btnLoading,
    drawerStyles,
    showSpin,
    isFaqManage,
    batchValue,
    confirmLoading,
    batch_operations,
    fuzzy,
    setCheckAll,
    faqData,
    editQaPk,
    editSimilarPk,
    expandSimilarQaPk,
    type,
    editQuestion,
    editAnswer,
    page,
    total,
    isBatchEnable,
    isCheckRepeatShow,
    repeatList,
    setPolishContentList,
    curSimilarList,
    similarLoading,
    curItem,
    polishLoading,
    curPolishContent,
    polishContentList,
    polishContentPage,
    polishBtnLoading,
    checkAll,
    showUploadModal,
    openDrawer,
    faqInfo,
    addSimilarQaPk,
    openDraw,
    setOpenDraw,
    setShowUploadModal,
    addNewQuestion,
    refreshList,
    changeBatch,
    repeatFaqCheck,
    handleBatchMenu,
    rowActionHandler,
    onCheckAllChange,
    setOpenDrawer,
    setType,
    setEditQuestion,
    setEditAnswer,
    onPageSizeChange,
    uploadDone,
    handleEvent,
    repeatFaqCheckDone,
    cancleEditQa,
    setCurPolishContent,
    setCurSimilarList,
    submitAddSimilar,
    deleteSimilarConfirm,
    submitUpdateSimilar,
    submitQa,
    editAnswerOnChange,
    editQuestionOnChange,
    handlerPolish,
    fuzzyOnChange,
    docKeyDown,
    goBack,
    fetchFaqList,
    crumbs,
    isCreateFolderShow,
    setIsCreateFolderShow,
    returnFolder,
    closeCreateFolder,
    editFolder,
    newFolderName,
    tableLoading,
    newFolderNameOnChange,
    createFolderConfirm,
    setEditFolder,
    setFolder,
    setCurSimilarParentList
  };
};
