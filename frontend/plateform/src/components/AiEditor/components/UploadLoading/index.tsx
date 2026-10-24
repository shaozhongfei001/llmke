import { Button, Flex, message, Progress } from "antd";
import Generating from "@/components/AiEditor/assets/img/generating.gif";
import { CloseOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import { EDITOR_EVENT_NAME, editorEventBus } from "../../editorEventBus";
import {
  api_getFileContent,
  api_getParseTextByUploadFile
} from "../../core/services/servers";
import { useStateStore } from "../../core/states/useStateStore";
import xls from "@/components/AiEditor/assets/img/xls.png";
import doc from "@/components/AiEditor/assets/img/doc.png";
import pdf from "@/components/AiEditor/assets/img/pdf.png";
import ppt from "@/components/AiEditor/assets/img/ppt.png";
import jpg from "@/components/AiEditor/assets/img/jpg.png";
import png from "@/components/AiEditor/assets/img/png.png";
import other from "@/components/AiEditor/assets/img/default.png";
import Success from "@/components/AiEditor/assets/img/success.png";
import Error from "@/components/AiEditor/assets/img/error.png";
import {
  convertHtmlAndInlineStyles,
  inlineStyleToReactObject
} from "../MainEditor/util";
import { MentionPlugin } from "@udecode/plate";
import { defaultStyle } from "../MainEditor/default_style";
import { useGlobalOperators } from "../../core/operators/useGlobalOperators";

const FILEIMG: any = {
  docx: doc,
  doc: doc,
  pdf: pdf,
  xls: xls,
  xlsx: xls,
  ppt: ppt,
  pptx: ppt,
  pub: ppt,
  jpg: jpg,
  png: png,
  default: other
};

enum UploadStatus {
  pedding = 1,
  success,
  error
}

export const UploadLoading = ({ downloadFile }: any) => {
  const { serverInfo, setEditorManager, mainEditor, setProjectData } =
    useStateStore();
  const { getArticleTotalNum } = useGlobalOperators();
  const [progress, setProgress] = useState<number>(0);
  const [loadingShow, setLoadingShow] = useState<boolean>(false);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>(
    UploadStatus.pedding
  );
  const [curContent, setCurContent] = useState("");
  const [fileInfo, setFileInfo] = useState({
    suffix: "",
    fileName: ""
  });

  const [downLoading, setDownLoading] = useState(false);

  const download = async (fileUrl) => {
    setDownLoading(true);
    try {
      const res: any = await api_getFileContent({
        config: serverInfo,
        data: {
          fileUrl
        }
      });
      if (res.includes("<img") || res.includes("<video")) {
        closeUploadLoading();
        message.warning("文档中含有不支持的内容");
        return;
      }
      const handleFn =
        downloadFile.suffix === "docx"
          ? inlineStyleToReactObject
          : convertHtmlAndInlineStyles;
      const { inlineHtml, reactStyles } = handleFn(res);
      // console.log(inlineHtml, reactStyles);
      const editor: any = mainEditor.current;
      setEditorManager((p) => ({
        ...p,
        parsed_data: inlineHtml,
        styles: { ...defaultStyle, customStyle: reactStyles }
      }));
      setProjectData((p) => ({
        ...p,
        article_content: inlineHtml
      }));
      setTimeout(() => {
        getArticleTotalNum(mainEditor.current);
      }, 500);
      setDownLoading(false);
    } catch (e) {
      setDownLoading(false);
    }
  };

  useEffect(() => {
    if (!downloadFile) return;
    download(downloadFile.fileUrl);
  }, [(downloadFile || {}).fileUrl]);

  useEffect(() => {
    if (progress === 100) {
      setUploadStatus(UploadStatus.success);
    }
  }, [progress]);

  const handleUpload = async (file) => {
    try {
      // const maxFileSize = 2 * 1024 * 1024; //最大上传2M文件
      // if (file.size > maxFileSize) {
      //   message.warning("文件大小不能超过2M");
      //   return;
      // }
      setUploadStatus(UploadStatus.pedding);
      const formData = new FormData();
      formData.append("file", file);
      const arr = file.name.split(".");
      setFileInfo({
        fileName: file.name,
        suffix: arr[arr.length - 1] || ""
      });
      setLoadingShow(true);
      const res = await api_getParseTextByUploadFile({
        data: {
          file: formData,
          onUploadProgress: (progressEvent) => {
            const curProgress = Math.round(
              (progressEvent.loaded / progressEvent.total) * 100
            );
            // 上传进度为100并没有拿到返回
            setProgress(curProgress === 100 ? 99 : curProgress);
          }
        },
        config: serverInfo
      });
      if (res) {
        // 拥有返回结果将进度设置为100
        setProgress(100);
        setCurContent(res);
      }
    } catch (e) {
      console.log(e);
      setUploadStatus(UploadStatus.error);
      setProgress(0);
    }
  };

  useEffect(() => {
    editorEventBus.on(EDITOR_EVENT_NAME.UPLOADFILE, handleUpload);
    return () => {
      editorEventBus.off(EDITOR_EVENT_NAME.UPLOADFILE, handleUpload);
    };
  }, [serverInfo]);

  const closeUploadLoading = () => {
    setDownLoading(false);
    setLoadingShow(false);
    setProgress(0);
    setUploadStatus(UploadStatus.pedding);
    setCurContent("");
    setFileInfo({
      suffix: "",
      fileName: ""
    });
  };

  const handleFileChange = (event) => {
    handleUpload(event.target.files[0]);
  };

  // 插入文章写作
  const handleWrite = () => {
    if (!curContent) return;
    if (curContent.includes("<img") || curContent.includes("<video")) {
      closeUploadLoading();
      message.warning("文档中含有不支持的内容");
      return;
    }
    const editor: any = mainEditor.current;
    const handleFn =
      fileInfo.suffix === "docx"
        ? inlineStyleToReactObject
        : convertHtmlAndInlineStyles;
    const { inlineHtml, reactStyles } = handleFn(curContent);
    // console.log(inlineHtml, reactStyles);
    setEditorManager((p) => ({
      ...p,
      parsed_data: inlineHtml,
      styles: { ...defaultStyle, customStyle: reactStyles }
    }));
    setProjectData((p) => ({
      ...p,
      article_content: inlineHtml
    }));
    setTimeout(() => {
      getArticleTotalNum(mainEditor.current);
    }, 500);
    closeUploadLoading();
  };

  return (
    <>
      {downLoading && (
        <Flex
          vertical
          style={{
            boxShadow: "0px 9px 28px 8px #0000000D",
            transform: "translate(-50%)"
          }}
          gap={24}
          className="absolute z-[999] bottom-[33px] left-1/2 w-[574px] h-[121px] pt-[20px] bg-white rounded-[8px]"
        >
          <Flex justify="space-between" className="px-[22px]">
            {UploadStatus.pedding === uploadStatus && (
              <Flex className="text-[16px] text-[#2a2a2a]">
                <img
                  src={Generating}
                  alt=""
                  width={20}
                  height={20}
                  className="mr-[8px]"
                />
                加载中
              </Flex>
            )}
          </Flex>
          <Flex className="px-[22px]">
            <Flex justify="space-between" className="w-full">
              <Flex align="center" className="text-[#2a2a2a]">
                <img
                  src={FILEIMG[fileInfo.suffix] || FILEIMG["default"]}
                  width={28}
                  height={28}
                  className="mr-[8px]"
                />
                {downloadFile.fileName}
              </Flex>
            </Flex>
          </Flex>
        </Flex>
      )}
      {loadingShow && (
        <Flex
          vertical
          style={{
            boxShadow: "0px 9px 28px 8px #0000000D",
            transform: "translate(-50%)"
          }}
          justify="space-between"
          className="absolute z-[999] bottom-[33px] left-1/2 w-[574px] h-[121px] pt-[20px] bg-white rounded-[8px]"
        >
          <Flex justify="space-between" className="px-[22px]">
            {UploadStatus.pedding === uploadStatus && (
              <Flex className="text-[16px] text-[#2a2a2a]">
                <img
                  src={Generating}
                  alt=""
                  width={20}
                  height={20}
                  className="mr-[8px]"
                />
                上传中
              </Flex>
            )}
            {UploadStatus.success === uploadStatus && (
              <Flex className="text-[16px] text-[#2a2a2a]">
                <img
                  src={Success}
                  alt=""
                  width={20}
                  height={20}
                  className="mr-[8px]"
                />
                上传成功
              </Flex>
            )}
            {UploadStatus.error === uploadStatus && (
              <Flex className="text-[16px] text-[#2a2a2a]">
                <img
                  src={Error}
                  alt=""
                  width={20}
                  height={20}
                  className="mr-[8px]"
                />
                上传失败
              </Flex>
            )}
            <CloseOutlined
              width={16}
              height={16}
              onClick={closeUploadLoading}
            />
          </Flex>
          <Flex className="px-[22px]">
            <Flex justify="space-between" className="w-full">
              <Flex align="center" className="text-[#2a2a2a]">
                <img
                  src={FILEIMG[fileInfo.suffix] || FILEIMG["default"]}
                  width={28}
                  height={28}
                  className="mr-[8px]"
                />
                {fileInfo.fileName}
              </Flex>
              {UploadStatus.pedding === uploadStatus && (
                <div className="text-[#555]">正在导入中&nbsp;{progress}%</div>
              )}
              {UploadStatus.success === uploadStatus && (
                <Flex className="text-[#555]" align="center">
                  <Button type="link" onClick={handleWrite}>
                    立即打开
                  </Button>
                  <img src={Success} width={20} height={20} />
                </Flex>
              )}
              {UploadStatus.error === uploadStatus && (
                <Flex className="text-[#555] relative" align="center">
                  <Button type="link">
                    <input
                      type="file"
                      // accept=".ppt,.doc,.docx,.ppt,.pdf,.txt"
                      className="w-full h-full absolute top-0 left-0 opacity-0"
                      onChange={handleFileChange}
                    />
                    重新上传
                  </Button>
                  <img src={Error} width={20} height={20} />
                </Flex>
              )}
            </Flex>
          </Flex>
          <Flex className="w-full">
            <Progress percent={progress} showInfo={false} size={"small"} />
          </Flex>
        </Flex>
      )}
    </>
  );
};
