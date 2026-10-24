/* eslint-disable no-unsafe-optional-chaining */
import { useEffect, useMemo, useRef, useState } from "react";
import { useServices } from "./useServices";
import { useNavigate } from "react-router-dom";
import { message } from "antd";
import { v4 as uuidv4 } from "uuid";
import dayjs from "dayjs";
import axios$ from "@root/src/apis";
import { useTServices } from "../../EditTemplate/common/useTServices";
import { TypeDrawConfig } from "@root/src/pages/Components/PermissionConfig";
const BaseCount = 9999;

const inseretValeToTemp = ({
  htmlString,
  allValue
}: {
  htmlString: string;
  allValue: any[];
}): string => {
  let newString = htmlString;
  allValue.forEach((item: any) => {
    if (newString.includes(`{${item.dataIndex}}`)) {
      newString = newString.replace(
        new RegExp(`{${item.dataIndex}}`, "g"),
        item.type === "date"
          ? dayjs().format("YYYY[年]MM[月]DD[日]")
          : item.defaultValue
            ? typeof item.defaultValue === "string"
              ? item.defaultValue
              : item.defaultValue[0]
            : `{${item.title}}`
      );
    }
  });
  return newString;
};

const useController = () => {
  const [messageApi] = message.useMessage();
  const navigate = useNavigate();
  const { updateArticleType } = useTServices({});
  const [showModal, setShowModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [editItem, setEditItem] = useState({});
  const deleteItems: any = useRef({});
  const [modalType, setModalType] = useState<"add" | "edit">("add");
  const [activeTabKey, setActiveTabKey] = useState("");
  const [tempPreview, setTempPreview] = useState<boolean>(false);
  const [tempPreviewInfo, setTempPreviewInfo] = useState<{
    htmlTemp: string;
    cssTemp: any;
    name: string;
    itemData: any;
  }>({
    htmlTemp: "",
    cssTemp: {},
    name: "",
    itemData: ""
  });
  const [sceneId, setSceneId] = useState<any>(null);
  const [sceneVersionList, setSceneVersionList] = useState<any[]>([]);
  const [versionLoading, setVersionLoading] = useState<boolean>(false);

  const [isShowSceneChooseModal, setIsShowSceneChooseModal] =
    useState<boolean>(false);

  const [listPostData, setListPostData] = useState<{
    pageNo: number;
    pageSize: number;
    search: undefined | string;
    isFirstSearch: boolean;
    className: undefined | string;
    forceRequest: number;
    tempType: "own" | "share";
  }>({
    pageNo: 1,
    pageSize: BaseCount,
    search: undefined,
    isFirstSearch: true,
    className: "",
    forceRequest: 0,
    tempType: "share"
  });
  const {
    queryTemplateList,
    deleteTemplate,
    queryTemplateById,
    queryArticleTypeUsingGet,
    getSceneClass,
    getScecnVersionsById
  }: any = useServices({
    ...listPostData
  });

  const listLoading = useMemo(() => {
    if (!listPostData.pageNo || !listPostData.className) {
      return false; // 如果请求未启用，listLoading 应为 false
    }
    return queryTemplateList?.isLoading || false;
  }, [
    queryTemplateList.isLoading,
    listPostData.pageNo,
    listPostData.className
  ]);

  const sceneClass = useMemo(() => {
    if (getSceneClass.data) {
      const list = getSceneClass.data.data.details.map((d: any) => {
        return {
          key: d,
          label: d
        };
      });
      setActiveTabKey((list[0] || {})?.key);
      return list;
    }
    return [];
  }, [getSceneClass.data]);

  /** 列表分页请求 */
  const [listData, setListData] = useState<{ list: any[]; total: number }>({
    list: [],
    total: 0
  });

  const [searchValue, setSearchValue] = useState<string>("");

  const toAddNextList = () => {
    const totalCount = Math.ceil(listData.total / BaseCount);
    const { pageNo }: any = queryTemplateList?.data?.data;
    if (pageNo < totalCount) {
      setListPostData((p) => ({
        ...p,
        pageNo: pageNo + 1,
        pageSize: BaseCount,
        search: searchValue,
        isFirstSearch: false,
        className: activeTabKey,
        forceRequest: listPostData.forceRequest
      }));
    }
  };

  useEffect(() => {
    if (!queryTemplateList?.data) return;
    const {
      details: list,
      totalCount: total,
      pageNo: pageNum
    } = queryTemplateList.data.data;

    const { isFirstSearch } = listPostData;
    if (isFirstSearch) {
      setListData({
        list: list || [],
        total: total || 0
      });
    } else {
      const { list: oldList } = listData;
      console.log("-----old-", oldList);
      if (
        oldList.length < (pageNum || 0) * BaseCount &&
        oldList.length < (total || 0)
      ) {
        setListData({
          list: oldList.concat(list || []),
          total: total || 0
        });
      }
    }
  }, [queryTemplateList.data]);

  useEffect(() => {
    if (!activeTabKey) return;
    if (
      listPostData.search === searchValue &&
      listPostData.className === activeTabKey
    )
      return;
    setListPostData((p) => ({
      ...p,
      pageNo: 1,
      pageSize: BaseCount,
      search: searchValue,
      className: activeTabKey,
      isFirstSearch: true
    }));
  }, [searchValue, activeTabKey, listPostData.tempType]);

  const refreshList = () => {
    setListData({
      list: [],
      total: 0
    });
    setListPostData((p) => ({
      ...p,
      pageNo: 1,
      pageSize: BaseCount,
      search: searchValue,
      className: activeTabKey,
      isFirstSearch: false,
      forceRequest: new Date().getTime()
    }));
  };

  const confirmModal = async () => {
    if (!deleteItems.current?.id) {
      message.warning("删除文档为空");
      return;
    }
    setDeleteLoading(true);
    try {
      const res = await deleteTemplate.mutateAsync(deleteItems.current.id);
      setDeleteLoading(false);
      setShowDeleteModal(false);
      if (res) {
        refreshList();
      }
    } catch (e) {
      console.log("e", e);
      setDeleteLoading(false);
    }
  };

  const closeModal = () => {
    setEditItem({});
    setShowModal(false);
  };

  const closeDeleteModal = () => {
    setShowDeleteModal(false);
  };

  const handleOpenCreateModal = () => {
    setModalType("add");
    setShowModal(true);
  };
  const handleOpenEditModal = async (item: any) => {
    if (!item?.id) return;
    try {
      const res = await queryTemplateById.mutateAsync(item.id);
      if (res) {
        setEditItem(res);
        setModalType("edit");
        setShowModal(true);
      }
    } catch (e) {
      console.log("e", e);
    }
  };
  const showWarning = (item: any) => {
    deleteItems.current = item;
    setShowDeleteModal(true);
  };

  const onSearch = (val: string) => {
    setSearchValue(val);
  };

  const goToWriting = (articleType: string) => {
    const tempId = `temp_${uuidv4()}`;
    navigate(`/docWriting/docs/${tempId}?articleType=${articleType}`);
  };

  const handleTempPreview = async (tempData: any) => {
    const res = await queryArticleTypeUsingGet.mutateAsync(tempData.id);
    if (!res) return;
    try {
      const formatTemplate = JSON.parse(res.formatTemplate);
      let htmlTemp = formatTemplate.htmlSchema;
      const cssTemp = JSON.parse(formatTemplate.cssSchema);
      const name = tempData.name;
      const uiSchema = JSON.parse(res.paramsSchema).uiSchema;
      htmlTemp = inseretValeToTemp({
        htmlString: htmlTemp,
        allValue: uiSchema
      });
      setTempPreviewInfo({ htmlTemp, cssTemp, name, itemData: tempData });
      setTempPreview(true);
    } catch (e) {
      console.log(e);
      message.error("模板解析出错");
    }
  };

  const tempPreviewClose = () => {
    setTempPreview(false);
    setTempPreviewInfo({ htmlTemp: "", cssTemp: {}, name: "", itemData: "" });
  };

  const handleCopy = async (item: any) => {
    const { id } = item;
    if (!id) message.error("不存在场景id");
    messageApi.open({
      type: "loading",
      content: "复制中",
      duration: 0
    });
    try {
      const res = await axios$.post(`/cecProxy/dw/articleType/${id}/copy`);
      if (res) {
        messageApi.destroy();
        message.success("复制完成");
        refreshList();
      }
    } catch (e) {
      messageApi.destroy();
      console.log(e);
    }
  };

  const handleEvent = async (type: string, d: any) => {
    console.log("======ddds=", d);
    switch (type) {
      case "toWrite":
        goToWriting(d.id);
        break;
      case "delete":
        showWarning(d);
        break;
      case "edit":
        if (d?.generateType == 1) {
          navigate(`/docWriting/template/segment/${d.id}`);
        } else {
          navigate(`/docWriting/template/${d.id}`);
        }

        break;
      case "add":
        {
          const tempId = `temp_${uuidv4()}`;
          navigate(`/docWriting/template/${tempId}`);
        }
        break;
      case "preview":
        await handleTempPreview(d);
        break;
      case "fullWriting":
        {
          const tempId = `temp_${uuidv4()}`;
          navigate(`/docWriting/template/${tempId}`);
        }
        break;
      case "segmentedWriting":
        {
          const tempId = `temp_${uuidv4()}`;
          navigate(`/docWriting/template/segment/${tempId}`);
        }
        break;
      case "copy":
        handleCopy(d);
        break;
      case "vision":
        setSceneId(d.id);
        break;
      case "auth":
        setDrawConfig((p) => ({
          ...p,
          data: {
            id: d.id
          }
        }));
        setOpenPermission(true);
        break;
      default:
        break;
    }
  };

  const tabChange = (key: string) => {
    setActiveTabKey(key);
  };

  const fetchSceneVisions = async () => {
    setVersionLoading(true);
    const details = await getScecnVersionsById(sceneId);
    if (details) {
      setSceneVersionList([...(details || [])]);
    }
    setVersionLoading(false);
  };

  const searchValueRef = useRef("");

  const closeVersionModal = () => {
    setSceneId(null);
  };

  const gotoVersionDetail = (row: any) => () => {
    const { versionId, version, generateType, id } = row;
    console.log(versionId);
    closeVersionModal();
    const path = `${versionId}-${version}/${id}`;
    let segmentStr = "segment/";
    if (Number(generateType) === 0) {
      segmentStr = "";
    }
    navigate(`/docWriting/template/version/${segmentStr}${path}`);
  };

  const rollBackVersion = async (params: any) => {
    setVersionLoading(true);
    const res: any = await updateArticleType.mutateAsync(params);
    console.log(params);

    const { data, success } = res;
    if (success) {
      const { currentVersionId } = data;
      const _sceneVersionList = sceneVersionList.map((i: any) => ({
        ...i,
        currentVersionId
      }));
      setSceneVersionList([..._sceneVersionList]);
    }
    setVersionLoading(false);
  };

  useEffect(() => {
    if (sceneId) {
      fetchSceneVisions();
    }
  }, [sceneId]);

  // 权限相关
  const [openPermission, setOpenPermission] = useState(false);
  const [drawConfig, setDrawConfig] = useState<TypeDrawConfig>({
    type: "edit"
  });

  return {
    listData,
    showModal,
    closeModal,
    handleOpenCreateModal,
    showWarning,
    showDeleteModal,
    closeDeleteModal,
    confirmModal,
    deleteLoading,
    searchValue,
    modalType,
    handleOpenEditModal,
    editItem,
    queryTemplateList,
    toAddNextList,
    listLoading,
    onSearch,
    refreshList,
    activeTabKey,
    tabChange,
    handleEvent,
    tempPreview,
    tempPreviewClose,
    tempPreviewInfo,
    sceneClass,
    isShowSceneChooseModal,
    setIsShowSceneChooseModal,
    searchValueRef,
    sceneId,
    sceneVersionList,
    versionLoading,
    closeVersionModal,
    gotoVersionDetail,
    rollBackVersion,
    listPostData,
    setListPostData,
    setListData,
    openPermission,
    setOpenPermission,
    drawConfig
  };
};

export default useController;
