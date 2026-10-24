import { useSearchParams } from "react-router-dom";
import { useAiEditor } from "@/components/AiEditor";
import { useEffect } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import { AiWriterProvider } from "@/components/AiEditor/core/states/useStateStore";
import { useState } from "react";
import { useAppPassport } from "@root/src/core/helps";

const articleTypeObj: any = {
  Announcement: "1",
  OfficialDocument: "0"
};

function DocWriting() {
  const Writing = () => {
    const location = useLocation();
    const navigator = useNavigate();
    const [searchParams] = useSearchParams(location.search);

    const { getToken } = useAppPassport();
    const token: any = getToken();
    // 文章id
    const { id, editorType } = useParams();

    const [articleInfo, setArticleInfo] = useState({});

    useEffect(() => {
      const articleType = searchParams.get("articleType");
      const articleTypeKey = searchParams.get("articleTypeKey");
      const { file, fileInfo } = location.state || {};
      const articleInfoObj: any = { editorType };
      if (articleType) {
        articleInfoObj.articleType = articleTypeObj[articleType] || "2";
        articleInfoObj.articleTypeId =
          articleTypeObj[articleType] || articleType;
      }
      if (articleTypeKey) {
        articleInfoObj.articleTypeKey = articleTypeKey;
      }
      if (fileInfo) {
        articleInfoObj.fileInfo = fileInfo;
      }
      if (file) {
        articleInfoObj.file = file;
      }
      setArticleInfo(articleInfoObj);
    }, [location, id, editorType, searchParams]);

    const { Element, refreshApp } = useAiEditor({
      url: "/cecProxy",
      token,
      enableMock: false,
      articleId: id?.includes("temp") ? "" : id,
      handleBack: () => {
        navigator("/docWriting/main");
        refreshApp();
      },
      ...articleInfo
    });

    useEffect(() => {
      return () => {
        refreshApp();
      };
    }, []);
    return <div className="w-full h-full">{Element}</div>;
  };

  return (
    <AiWriterProvider>
      <Writing />
    </AiWriterProvider>
  );
}

export default DocWriting;
