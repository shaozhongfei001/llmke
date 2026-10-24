import { useMemo, useRef, useState } from "react";
import { useServices } from "./useServices";
import { useNavigate } from "react-router-dom";
import type { MenuProps } from "antd";
import { message } from "antd";
import { v4 as uuidv4 } from "uuid";
import dayjs from "dayjs";
import doc from "@/assets/writing/doc.png";
import { ReactComponent as NoticeIcon } from "@/assets/svg/notice.svg";

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
  const {
    getDocList,
    getTemplateList,
    queryArticleTypeUsingGet,
    deleteTemplate,
    getSceneClass
  } = useServices();
  const navigate = useNavigate();
  const [listDropDownShow, setListDropDownShow] = useState(false);

  const sceneClass = useMemo(() => {
    if (getSceneClass.data) {
      return getSceneClass.data.data.details || [];
    }
    return [];
  }, [getSceneClass.data]);

  //将模版数据按照class分类
  const convertTempList = (inputArray: any[]) => {
    const res = sceneClass.map((s) => {
      const list: any[] = [];
      inputArray.forEach((item: any) => {
        const { className: itemClass } = item;
        if (s == itemClass) {
          list.push({ icon: <NoticeIcon />, ...item });
        }
      });
      return {
        class: s,
        list: list
      };
    });
    return res;
  };

  const convertDocList = (inputArray: any[]) => {
    return inputArray.map((item: any) => {
      return {
        key: item.id,
        label: (
          <div
            className="flex flex-row align-baseline py-3"
            style={{
              borderBottom: "1px solid #EEEEEE"
            }}
            onClick={() => {
              handleAction("docDetail", item);
            }}
          >
            <img
              src={doc}
              alt="ellipse"
              className="w-[16px] h-[16px] bg-[#FFFFFF] mt-[4px] mr-2"
            />
            <div>
              <div className="text-[#2A2A2A] text-sm whitespace-nowrap overflow-hidden overflow-ellipsis max-w-[220px] mb-2">
                {item.title}
              </div>
              <div className="text-[#888888] text-xs">
                {item.gmtModified &&
                  dayjs(item.gmtModified).format("YYYY-MM-DD HH:mm:ss")}
              </div>
            </div>
          </div>
        )
      };
    });
  };

  const docList: MenuProps["items"] = useMemo(() => {
    const originData = getDocList?.data?.data?.details || [];
    return convertDocList(originData) || [];
  }, [getDocList.data]);

  const tempClassList = useMemo(() => {
    const data: any = getTemplateList?.data?.data;
    const originList = data?.details;

    if (originList) {
      const notEditList = originList.filter((d) => d?.state !== 0);
      return convertTempList(notEditList);
    }
    return [];
  }, [getTemplateList.data]);

  const goToWriting = (articleType: string) => {
    const tempId = `temp_${uuidv4()}`;
    navigate(`/docWriting/docs/${tempId}?articleType=${articleType}`);
  };

  const [fileRefresh, setFileRefresh] = useState(0);
  const handleFileChange = (event: { target: { files: any[] } }) => {
    const file = event.target.files[0];
    // const maxFileSize = 2 * 1024 * 1024; //最大上传2M文件
    // if (file.size > maxFileSize) {
    //   message.warning("文件大小不能超过2M");
    //   return;
    // }
    // navigate(`/docWriting/docs/temp_${uuidv4()}?articleTypeKey=normal`, {
    //   state: {
    //     file,
    //   },
    // });
    navigate(`/docWriting/docs/temp_${uuidv4()}?articleType=-3`, {
      state: {
        file
      }
    });
    setFileRefresh((fileRefresh) => fileRefresh + 1);
  };

  // ================场景预览相关=======================
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
  const handleTempPreview = async (tempData: any) => {
    const res: any = await queryArticleTypeUsingGet.mutateAsync(tempData.id);
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
  // ================场景预览相关结束=======================

  // ================场景删除相关=======================
  const deleteItems: any = useRef({});
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const confirmModal = async () => {
    if (!deleteItems.current?.id) {
      message.warning("删除文档为空");
      return;
    }
    try {
      const res = await deleteTemplate.mutateAsync(deleteItems.current.id);
      setShowDeleteModal(false);
      if (res) {
        getTemplateList.refetch();
      }
    } catch (e) {
      console.log("e", e);
    }
  };
  const showWarning = (item: any) => {
    deleteItems.current = item;
    setShowDeleteModal(true);
  };
  const closeDeleteModal = () => {
    setShowDeleteModal(false);
  };
  // ================场景删除相关结束=======================

  const handleAction = async (action: string, data: any) => {
    switch (action) {
      case "article_create":
        {
          const tempId = `temp_${uuidv4()}`;
          // navigate(`/docWriting/docs/${tempId}?articleTypeKey=${data}`);
          navigate(`/docWriting/docs/${tempId}?articleType=${-3}`);
        }
        break;
      case "toWrite":
        goToWriting(data.id);
        break;
      case "docDetail":
        if (data?.id) {
          navigate(`/docWriting/docs/${data.id}`);
        } else {
          message.warning("该文档为空");
        }
        break;
      case "preview":
        await handleTempPreview(data);
        break;
      case "delete":
        showWarning(data);
        break;
      default:
        return;
    }
  };

  const onDocListOpenChange = (open: boolean) => {
    setListDropDownShow(open);
  };

  return {
    docList,
    tempClassList,
    listDropDownShow,
    setListDropDownShow,
    handleAction,
    handleFileChange,
    fileRefresh,
    tempPreview,
    tempPreviewClose,
    tempPreviewInfo,
    showDeleteModal,
    confirmModal,
    deleteTemplate,
    closeDeleteModal,
    onDocListOpenChange
  };
};

export default useController;
