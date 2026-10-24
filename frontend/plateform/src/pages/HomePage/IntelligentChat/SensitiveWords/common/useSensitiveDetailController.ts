import { ChangeEventHandler, useEffect, useMemo, useState } from "react";
import { EXTRACT_STATUS } from "@/const/knowledgebase";
import {
  createLibrary,
  deleteLibrary,
  getLibraryList,
  getLibraryListById,
  updateLibrary
} from "./sensiveService";
import { message } from "antd";
import { useNavigate, useParams } from "react-router-dom";
const initialPage = {
  pageNo: 1,
  pageSize: 10
};

export let sensitiveDetailControllerType: any = {};
export const useSensitiveDetailController = () => {
  const { id: sensitiveId } = useParams();
  const navigator = useNavigate();
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [fuzzyNameOrId, setFuzzyNameOrId] = useState("");
  const [tags, setTags]: any = useState([]);
  const [loading, setLoading] = useState(false);
  const [detailData, setDetailData]: any = useState({});
  const [filter, setFilter] = useState("");

  const isAdd = useMemo(() => {
    return location.pathname.indexOf("chats/sensitiveWords/add") > -1;
  }, [location]);

  const fuzzyNameOrIdOnChange: ChangeEventHandler<HTMLInputElement> = (e) => {
    const inputElement = e.target as HTMLInputElement;
    setFuzzyNameOrId(inputElement.value.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      setFilter(fuzzyNameOrId);
    }
  };
  //getLibraryListById
  const fetchDetail = async () => {
    try {
      setLoading(true);

      const res = await getLibraryListById({ id: sensitiveId });
      setLoading(false);
      if (res) {
        setTags(res.words || []);
        setDetailData(res);
      }
    } catch (e) {
      setLoading(false);
    }
  };

  const fetchEdit = async () => {
    if (!sensitiveId) {
      return message.warning("缺少敏感词库ID!");
    }
    try {
      setLoading(true);
      const res = await updateLibrary({
        ...detailData,
        words: tags
      });
      setLoading(false);
      if (res) {
        message.success(`${isAdd ? "新增" : "修改"}敏感词成功!`);

        navigator(-1);
      } else {
        message.error("修改敏感词失败!");
      }
    } catch (error) {
      setLoading(false);
      message.error("修改敏感词失败!");
    }
  };

  const handleEvent = (type: string, data: any) => {
    switch (type) {
      case "uploaded":
        fetchDetail();
        break;
      case "upload":
        setShowUploadModal(true);
        break;
      case "update":
        fetchEdit();
        break;
      case "clickForSearch":
        setFilter(fuzzyNameOrId);
        break;
    }
  };

  useEffect(() => {
    if (!sensitiveId) return;
    fetchDetail();
  }, [sensitiveId]);

  const res = {
    fuzzyNameOrId,
    fuzzyNameOrIdOnChange,
    handleKeyDown,
    handleEvent,
    tags,
    setTags,
    sensitiveId,
    detailData,
    loading,
    filter,
    isAdd,
    showUploadModal,
    setShowUploadModal
  };

  sensitiveDetailControllerType = res;

  return res;
};
