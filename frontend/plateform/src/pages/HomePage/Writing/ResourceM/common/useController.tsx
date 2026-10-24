import { useEffect, useRef, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { message, Button, Badge, Typography, Tooltip } from "antd";
import { v4 as uuidv4 } from "uuid";
import doc from "@/assets/writing/doc.png";
import { useHServices } from "./useRServices";
import { sceneTagMap, styleTagMap, FILEIMG } from "./constans";
enum STATUS {
  NORMAL = 1,
  PARSING,
  SUCCESS,
  FAIL
}

const useController = () => {
  const navigate = useNavigate();
  const [activeTabKey, setActiveTabKey] = useState("commonLib");
  const [listPostData, setListPostData] = useState<{
    pageNo: number;
    pageSize: number;
    search: undefined | string;
    bizType: string;
    scene: string;
    articleStyle: string;
    totalCount: number;
  }>({
    pageNo: 1,
    pageSize: 10,
    search: undefined,
    bizType: "commonLib",
    scene: "",
    articleStyle: "",
    totalCount: 0
  });
  const [taskIds, setTaskIds] = useState<string>("");
  const {
    getMaterialList,
    deleteMaterial,
    getAnalysisIdsProcess,
    retryParseMaterial
  }: any = useHServices({
    taskIds,
    ...listPostData
  });
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const deleteItems: any = useRef({});

  const [curFileInfo, setCurFileInfo] = useState({
    file_source: "",
    fileName: "",
    fileSuffix: "",
    htmlUrl: ""
  });

  const disablePreview = (
    state: number,
    fileSuffix: string,
    htmlUrl?: string
  ) => {
    return (
      state == STATUS.PARSING ||
      (!["pdf", "txt", "html", "csv", "img"].includes(fileSuffix) &&
        (!htmlUrl || JSON.parse(htmlUrl).length == 0))
    );
  };

  const disableGoWrite = (
    state: number,
    fileSuffix: string,
    htmlUrl?: string
  ) => {
    return (
      state !== STATUS.SUCCESS ||
      !["doc", "docx"].includes(fileSuffix) ||
      !htmlUrl ||
      JSON.parse(htmlUrl).length == 0
    );
  };

  const defaultColumns = useMemo(
    () => [
      {
        title: "",
        dataIndex: "fileSuffix",
        width: "50px",
        render: (fileSuffix: string) => (
          <img
            src={FILEIMG[fileSuffix] || doc}
            alt="ellipse"
            className="w-[16px] h-[16px] bg-[#FFFFFF] mt-[4px] mr-[10px]"
          />
        )
      },
      {
        title: "名称",
        dataIndex: "fileName",
        ellipsis: true
      },
      {
        title: "状态",
        dataIndex: "state",
        width: "100px",
        render: (state: number) => {
          if (!state) return "-";
          switch (state) {
            case STATUS.PARSING:
              return <Badge color="#055AFF" text="解析中" />;
            case STATUS.SUCCESS:
              return <Badge color="#52C41A" text="解析成功" />;
            case STATUS.FAIL:
              return <Badge color="#FF4D4F" text="解析失败" />;
            default:
              break;
          }
        }
      },
      {
        title: "上传时间",
        dataIndex: "gmtCreate",
        width: "180px"
      },
      {
        title: "操作",
        dataIndex: "",
        width: "220px",
        render: (_: any, record: any) => {
          const { state, htmlUrl, fileSuffix } = record;
          return (
            <div className="flex flex-row">
              {state == STATUS.FAIL ? (
                <Typography.Link
                  className="w-full text-center"
                  onClick={() => {
                    handleEvent("retryParse", record);
                  }}
                >
                  解析
                </Typography.Link>
              ) : disablePreview(state, fileSuffix, htmlUrl) ? (
                <Tooltip
                  title="后端解析失败，当前文档不能预览"
                  color="#fff"
                  overlayInnerStyle={{
                    backgroundColor: "#fff",
                    color: "#2A2A2A"
                  }}
                >
                  <Typography.Link
                    className="w-full text-center"
                    disabled={
                      state == STATUS.PARSING ||
                      (!["pdf", "txt", "html", "csv", "img"].includes(
                        fileSuffix
                      ) &&
                        (!htmlUrl || JSON.parse(htmlUrl).length == 0))
                    }
                    onClick={() => handleEvent("detail", record)}
                  >
                    预览
                  </Typography.Link>
                </Tooltip>
              ) : (
                <Typography.Link
                  className="w-full text-center"
                  disabled={
                    state == STATUS.PARSING ||
                    (!["pdf", "txt", "html", "csv", "img"].includes(
                      fileSuffix
                    ) &&
                      (!htmlUrl || JSON.parse(htmlUrl).length == 0))
                  }
                  onClick={() => handleEvent("detail", record)}
                >
                  预览
                </Typography.Link>
              )}
              {activeTabKey !== "lawLib" && (
                <Typography.Link
                  className="w-full text-center"
                  disabled={disableGoWrite(state, fileSuffix, htmlUrl)}
                  onClick={() => handleEvent("toWrite", record)}
                >
                  去写作
                </Typography.Link>
              )}
              <Typography.Link
                className="w-full text-center"
                onClick={() => handleEvent("delete", record)}
              >
                删除
              </Typography.Link>
            </div>
          );
        }
      }
    ],
    [activeTabKey]
  );

  const columns = useMemo(() => {
    switch (activeTabKey) {
      case "commonLib":
        return defaultColumns;
      case "demoLib": {
        defaultColumns.splice(
          2,
          0,
          {
            title: "文体",
            dataIndex: "articleStyle",
            width: "80px",
            render: (record: any) => {
              const tag = styleTagMap.filter((s: any) => s.key == record);
              return tag && tag?.length > 0 ? <span>{tag[0].label}</span> : "-";
            }
          },
          {
            title: "场景",
            dataIndex: "scene",
            width: "80px",
            render: (record: any) => {
              const tag = sceneTagMap.filter((s: any) => s.key == record);
              return tag && tag?.length > 0 ? <span>{tag[0].label}</span> : "-";
            }
          }
        );
        return defaultColumns;
      }
      case "lawLib": {
        defaultColumns.splice(2, 0, {
          title: "场景",
          dataIndex: "scene",
          width: "80px",
          render: (record: any) => {
            const tag = sceneTagMap.filter((s: any) => s.key == record);
            return tag && tag?.length > 0 ? <span>{tag[0].label}</span> : "-";
          }
        });
        return defaultColumns;
      }
    }
    return defaultColumns;
  }, [activeTabKey, defaultColumns]);

  const [selectedSenceTags, setSelectedSenceTags] = useState<string[]>([]);
  const handleSenceTagChange = (tag: string, checked: boolean) => {
    const nextSelectedTags = checked
      ? [...selectedSenceTags, tag]
      : selectedSenceTags.filter((t) => t !== tag);
    setSelectedSenceTags(nextSelectedTags);
  };

  const [selectedStyleTags, setSelectedStyleTags] = useState<string[]>([]);
  const handleStyleTagChange = (tag: string, checked: boolean) => {
    const nextSelectedTags = checked
      ? [...selectedStyleTags, tag]
      : selectedStyleTags.filter((t) => t !== tag);
    setSelectedStyleTags(nextSelectedTags);
  };

  const showWarning = (item: any) => {
    deleteItems.current = item;
    setShowDeleteModal(true);
  };

  const confirmModal = async () => {
    if (!deleteItems.current?.id) {
      message.warning("删除文档为空");
      return;
    }
    setDeleteLoading(true);
    try {
      const res = await deleteMaterial.mutateAsync(deleteItems.current.id);
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

  const refreshList = () => {
    console.log("-------------2");

    setListData([]);
    // setSelectedSenceTags([]);
    // setSelectedStyleTags([]);
    // setListPostData({
    //   ...listPostData,
    //   pageNo: 1,
    //   scene: "",
    //   articleStyle: ""
    // });
    getMaterialList.refetch();
  };

  const showDoc = (data: any) => {
    if (data && data?.state !== STATUS.SUCCESS) {
      message.warning("请解析成功后查看");
      return;
    }
    if (data?.id) {
      setShowPreviewModal(true);
      const { fileName, fileUrl, htmlUrl, fileSuffix } = data;
      let url =
        ["pdf", "txt", "html", "csv", "img"].indexOf(fileSuffix) > -1
          ? fileUrl
          : JSON.parse(htmlUrl);
      url = Array.isArray(url) ? url.map((u: any) => u.url) : url;
      url = Array.isArray(url) && url?.length == 1 ? url[0] : url;
      setCurFileInfo({
        file_source: url,
        fileName: fileName,
        fileSuffix: fileSuffix,
        htmlUrl: htmlUrl
      });
    } else {
      message.warning("该文档为空");
    }
  };

  /** 列表分页请求 */
  const [listData, setListData] = useState<any[]>([]);

  useEffect(() => {
    if (!getMaterialList?.data) return;
    const { details: list, totalCount, pageNo } = getMaterialList.data.data;
    if (list.length <= 0) {
      setListPostData((pre) => {
        return {
          ...pre,
          pageNo: pageNo > 1 ? pageNo - 1 : 0,
          totalCount: totalCount
        };
      });
      setListData([]);
    } else {
      setListData(list);

      setListPostData((pre) => {
        return {
          ...pre,
          totalCount: totalCount
        };
      });
    }
  }, [getMaterialList.data]);

  /** 解析进度 */
  useEffect(() => {
    if (listData) {
      const taskIds = listData
        ?.filter((i: any) => i.state === 2)
        .map((i) => i.id)
        .join(",");
      setTaskIds(taskIds || "");
    }
  }, [listData]);

  useEffect(() => {
    if (getAnalysisIdsProcess.data) {
      const taskProcessList = getAnalysisIdsProcess.data.data.details;
      const newTaskIdsArr = taskIds.split(",");

      let isRefreshList = false;
      for (const item of taskProcessList) {
        if (item) {
          // 构建进度100%或者构建失败，都将进度任务踢出并刷新列表
          if (item.state !== 2) {
            const index = newTaskIdsArr.findIndex((i) => i === String(item.id));
            if (index !== -1) {
              isRefreshList = true;
              newTaskIdsArr.splice(index, 1);
            }
          }
        }
      }
      isRefreshList && getMaterialList.refetch();
      setTaskIds(newTaskIdsArr?.join(","));
    }
  }, [getAnalysisIdsProcess.data]);

  useEffect(() => {
    const sence: string[] = [];
    const articleStyle: string[] = [];
    sceneTagMap.forEach((se) => {
      if (selectedSenceTags.includes("全部")) return;
      if (selectedSenceTags.includes(se.label)) {
        sence.push(se.key);
      }
    });
    styleTagMap.forEach((se) => {
      if (selectedStyleTags.includes("全部")) return;
      if (selectedStyleTags.includes(se.label)) {
        articleStyle.push(se.key);
      }
    });
    setListPostData({
      ...listPostData,
      bizType: activeTabKey,
      pageNo: 1,
      scene: sence.join(","),
      articleStyle: articleStyle.join(",")
    });
  }, [activeTabKey, selectedSenceTags, selectedStyleTags]);

  const onPageSizeChange = (page: number) => {
    setListPostData({
      ...listPostData,
      pageNo: page
    });
  };

  const onSearch = (val: string) => {
    setListPostData({
      ...listPostData,
      pageNo: 1,
      search: val
    });
  };

  const previewGoWrite = (d: any) => {
    let fileUrl = "";
    try {
      fileUrl = JSON.parse(d.htmlUrl)[0].url;
    } catch (e) {
      message.warning("未找到文件地址");
      return;
    }
    // navigate(`/docWriting/docs/temp_${uuidv4()}?articleTypeKey=normal`, {
    //   state: {
    //     fileInfo: {
    //       fileName: d.fileName,
    //       fileUrl,
    //       suffix: d.fileSuffix
    //     }
    //   }
    // });
    navigate(`/docWriting/docs/temp_${uuidv4()}?articleType=-3`, {
      state: {
        fileInfo: {
          fileName: d.fileName,
          fileUrl,
          suffix: d.fileSuffix
        }
      }
    });
  };

  const handleEvent = async (action: string, data?: any) => {
    switch (action) {
      case "material_refresh":
        refreshList();
        break;
      case "detail":
        showDoc(data);
        break;
      case "delete":
        showWarning(data);
        break;
      case "retryParse":
        {
          await retryParseMaterial.mutateAsync(data.id);
          console.log("-------------1");
          refreshList();
        }
        break;
      case "tabChange":
        {
          setActiveTabKey(data);
          setSelectedSenceTags([]);
          setSelectedStyleTags([]);
        }
        break;
      case "openUploadModal":
        setShowUploadModal(true);
        break;
      case "closeUploadModal":
        setShowUploadModal(false);
        break;
      case "closeDeleteModal":
        setShowDeleteModal(false);
        break;
      case "closePreviewModal":
        setCurFileInfo({
          file_source: "",
          fileName: "",
          fileSuffix: "",
          htmlUrl: ""
        });
        setShowPreviewModal(false);
        break;
      case "toWrite":
        previewGoWrite(data);
        break;
      default:
        return;
    }
  };

  const tabChange = (key: string) => {
    setActiveTabKey(key);
    setSelectedSenceTags([]);
    setSelectedStyleTags([]);
  };

  const searchValueRef = useRef("");

  return {
    columns,
    getMaterialList,
    showUploadModal,
    handleEvent,
    showWarning,
    showDeleteModal,
    confirmModal,
    deleteLoading,
    showPreviewModal,
    setShowPreviewModal,
    curFileInfo,
    setCurFileInfo,
    listData,
    listPostData,
    onSearch,
    activeTabKey,
    tabChange,
    selectedSenceTags,
    handleSenceTagChange,
    selectedStyleTags,
    handleStyleTagChange,
    onPageSizeChange,
    previewGoWrite,
    STATUS,
    searchValueRef
  };
};

export default useController;
