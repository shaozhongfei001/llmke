import { Button, Drawer, Flex, message, Popover, Progress } from "antd";
import {
  DocState,
  EditorStatus,
  EditorType,
  ModueEnum
} from "../../@types/sys";
import useAiEditorOperators from "../../core/operators/useAiEditorOperators";
import { useStateStore } from "../../core/states/useStateStore";
import Generating from "@/components/AiEditor/assets/img/generating.gif";
import Success from "@/components/AiEditor/assets/icon/ok2.svg";
import UpArrow from "@/components/AiEditor/assets/img/upArrow.png";
import DownArrow from "@/components/AiEditor/assets/img/downArrow.png";
import Go from "@/components/AiEditor/assets/img/go.png";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import FileViewModal, { FILEIMG } from "../FileViewModal";
import { editorEventBus, EDITOR_EVENT_NAME } from "../../editorEventBus";
import { DrawerContent } from "../DrawerContent";
import { CloseOutlined, ExclamationCircleFilled } from "@ant-design/icons";
import { useGlobalOperators } from "../../core/operators/useGlobalOperators";
import RagReCallDrawer from "../RagReCallDrawer";
import { RagFileView } from "../RagFileView";
import { uniqBy } from "lodash";
import { v4 as uuidv4 } from "uuid";
import { FileDocIcon, FilePdfIcon, OdfFileIcon } from "@/components/Icon";

const mockList = [
  {
    metadata: {
      source:
        "dev-rag-data/intelbrain-dw/1243/遂宁知识库/遂宁知识库_历史沿革遂宁睿杰兴/V0/历史沿革-遂宁睿杰兴.xlsx",
      file_path:
        "dev-rag-data/intelbrain-dw/1243/遂宁知识库/遂宁知识库_历史沿革遂宁睿杰兴/V0/历史沿革-遂宁睿杰兴.xlsx",
      id: "ZGV2LXJhZy1kYXRhL2ludGVsYnJhaW4tZHcvMTI0My/pgYLlroHnn6Xor4blupMv6YGC5a6B55+l6K+G5bqTX+WOhuWPsuayv+mdqemBguWugeedv+adsOWFtC9WMC/ljoblj7Lmsr/pnakt6YGC5a6B552/5p2w5YW0Lnhsc3g=",
      search_type: ["es", "es"],
      offset: [
        [1, 0],
        [1, 1],
        [1, 2],
        [1, 3],
        [1, 4],
        [2, 0],
        [2, 1],
        [2, 2],
        [2, 3],
        [2, 4]
      ],
      pic_offset_list: [],
      chunk_type: "table",
      position: [],
      file_id: 65341,
      page_size: [],
      page_number: [],
      chunk_index: -1
    },
    order_num: "4202785257985210054",
    page_content:
      "|序号|变更日期|变更项目|变更前|变更后|\n| :---: | :---: | :---: | :---: | :---: |\n|1|2024-01-25|投资人(股权)变更|方映* 出资 2100万人民币;李建辉 出资 900万人民币;四川睿杰鑫电子股份有限公司 出资 1000万人民币;|四川睿杰鑫电子股份有限公司 出资 4000万人民币;|\n|2|2024-01-25|其他事项备案|李建辉 出资 900万人民币;方映 出资 2100万人民币;四川睿杰鑫电子股份有限公司 出资 1000万人民币;|四川睿杰鑫电子股份有限公司 出资 4000万人民币;|",
    parsedFilePath:
      "http://10.15.12.13:9000/dev-rag-data/intelbrain-dw/1243/遂宁知识库/遂宁知识库_历史沿革遂宁睿杰兴/V0/历史沿革-遂宁睿杰兴.xlsx",
    pdfPages: 0,
    pic_url_list: [],
    score: "0.2777777777777778",
    type: "Document"
  }
];
enum ExportType {
  docx = "docx",
  wps = "wps",
  pdf = "pdf",
  odt = "odt"
}
const exportTypeList: ExportType[] = [
  ExportType.docx,
  ExportType.wps,
  ExportType.pdf,
  ExportType.odt
];
const iconMap = {
  [ExportType.docx]: <FileDocIcon />,
  [ExportType.wps]: <FileDocIcon />,
  [ExportType.pdf]: <FilePdfIcon />,
  [ExportType.odt]: <OdfFileIcon />
};

const finishStatus = [DocState.success, DocState.failure, DocState.stopped];

const getFileName = (url: string): any => {
  const regex = /([^/]+)\.([^/]+)$/;
  const match = url.match(regex);

  if (match) {
    return {
      fileName: match[1],
      fileExtension: match[2],
      url
    };
  }
  return {};
};

export const ArticleLoading = () => {
  const {
    editorManager,
    projectData,
    setProjectData,
    mainEditor,
    setOpen,
    open,
    reqSchedule,
    exportHover,
    setExportHover,
    serverInfo,
    baseInfo,
    editorType
  } = useStateStore();
  const { cancelGenerate, saveBeforeReview } = useAiEditorOperators();
  const { handleDownLoad, getArticleTotalNum } = useGlobalOperators();

  // 当前点击的溯源文档
  const [showDrawer, setShowDrawer] = useState<boolean>(false);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [content, setContent] = useState<{
    title: "";
    file_type: "";
    file_source?: string;
    matchText: string;
    paragraphNo: number;
  } | null>(null);

  const onClose = () => {
    setContent(null);
    setFileContent(null);
    setShowDrawer(false);
    setProjectData((pre) => ({
      ...pre,
      content_review: {
        errors: [],
        document: ""
      }
    }));
  };

  useEffect(() => {
    const handleTagClick = (data: any) => {
      if (data.isRag) {
        if (!data.id) {
          message.error("未找到文件id");
          return;
        }
        data.id && handleRagReCall(data.id);
      } else {
        setShowDrawer(true);
        const curContent = (projectData?.sourceList || []).find(
          (i) => i.id === data.id
        );
        setContent({
          file_type: curContent.fileFormat,
          title: curContent.filename,
          file_source: curContent.url,
          matchText: curContent.text,
          paragraphNo: curContent.paragraphNo
        });
      }
    };
    editorEventBus.on(EDITOR_EVENT_NAME.CLICKRETRIEVE, handleTagClick);
    return () => {
      editorEventBus.off(EDITOR_EVENT_NAME.CLICKRETRIEVE, handleTagClick);
    };
  }, [projectData.sourceList]);

  const handleCancelClick = () => {
    cancelGenerate();
  };
  const getItemInfo = (status: EditorStatus) => {
    switch (status) {
      case EditorStatus.WaitingForGen:
        return "正在理解中......";
      case EditorStatus.GeneratingFullText:
        return "正在生成中......";
      case EditorStatus.GeneratingPartialText:
        return "正在生成中......";
      case EditorStatus.ReviewingFullText:
        return "自动审核中......";
      case EditorStatus.Reviewing:
        return "审核中......";
      case EditorStatus.ReviewingSuccess:
        return "审核完成";
      case EditorStatus.Success:
        return "写作完成";
      default:
        return "";
    }
  };

  const [showFile, setShowFile] = useState<boolean>(false);
  const [curFileInfo, setCurFileInfo] = useState<any>(null);
  const handleFileClick = (item: any) => {
    setShowFile(true);
    setCurFileInfo({
      file_type: "txt",
      title: (item.filename.split(".")[0] || item.filename) + "txt",
      metadata: {
        source: item.url
      }
    });
  };

  useEffect(() => {
    if (editorManager.status === EditorStatus.Success) {
      const editor = mainEditor.current;
      if (!editor) return;
      getArticleTotalNum(editor);
    }
  }, [editorManager.status, mainEditor.current]);

  const handleReview = async () => {
    setProjectData((p) => ({
      ...p,
      currentModule: ModueEnum.Review
    }));
    setOpen(true);
    setTimeout(() => {
      editorEventBus.emit(EDITOR_EVENT_NAME.START_REVIEW);
    }, 50);
  };

  // 参考文档收起展开
  const [fileListShow, setFileListShow] = useState(false);

  // 功能按钮
  const SaveButton = useCallback(
    () => (
      <Button
        style={{
          color: "#2a2a2a",
          border: "1px solid #eee",
          borderRadius: "4px"
        }}
        ghost
        onClick={async () => {
          try {
            const id = await saveBeforeReview();
            id && message.success("保存成功");
          } catch (e) {}
        }}
      >
        保存
      </Button>
    ),
    [
      projectData.id,
      serverInfo,
      projectData?.title,
      projectData.generateType,
      baseInfo,
      projectData.extraParams,
      projectData.sourceList,
      projectData.files
    ]
  );

  // 功能按钮
  const ReviewButton = useCallback(
    () => (
      <Button
        disabled={
          !projectData.id ||
          (open && projectData.currentModule === ModueEnum.Review)
        }
        style={{
          color: "#2a2a2a",
          border: "1px solid #eee",
          borderRadius: "4px"
        }}
        ghost
        onClick={handleReview}
      >
        审核
      </Button>
    ),
    [
      projectData.id,
      projectData.currentModule,
      serverInfo,
      projectData.title,
      projectData.sourceList,
      projectData.generateType,
      projectData.outputFormat,
      baseInfo,
      projectData.extraParams
    ]
  );

  // 控制导出类型弹出pop, true/false控制是否显示，none控制是否是点击继续导出
  const [exportTypeDisplay, setExportTypeDisplay] = useState<boolean>(false);
  const closeTimer = useRef<any>(null);
  const ExportButton = useCallback(
    () => (
      <>
        {exportHover ? (
          <Popover
            placement="top"
            title={
              <>
                <ExclamationCircleFilled className="text-[#FAAD14] mr-2 text-[16px]" />
                <span>建议导出前进行审核</span>
              </>
            }
            content={
              <Flex vertical gap={8} className="w-[176px] ml-6">
                <span>
                  您已修改文章，为确保内容准确无误，建议先进行审核后再导出。
                </span>
                <Flex justify="end" gap={8}>
                  <Button
                    size="small"
                    style={{
                      color: "#2a2a2a",
                      border: "1px solid #eee"
                    }}
                    onClick={() => {
                      setExportHover(false);
                      setExportTypeDisplay(true);
                    }}
                  >
                    继续导出
                  </Button>
                  <Button
                    size="small"
                    style={{
                      background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                      color: "#fff",
                      border: "none",
                      borderRadius: "4px"
                    }}
                    onClick={() => {
                      handleReview();
                      setExportHover(false);
                    }}
                  >
                    立即审核
                  </Button>
                </Flex>
              </Flex>
            }
          >
            <Button
              disabled={!projectData.id}
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                borderRadius: "4px",
                border: "none"
              }}
              ghost
            >
              导出
            </Button>
          </Popover>
        ) : (
          <Popover
            placement="top"
            open={exportTypeDisplay}
            content={
              <div className="py-2">
                {exportTypeList.map((type) => (
                  <div
                    key={uuidv4()}
                    className="cursor-pointer h-[32px] w-[92px] flex items-center gap-3 hover:bg-[#F1F5FF] pl-4"
                    onClick={() => handleDownLoad(type)}
                    onMouseEnter={() => {
                      clearTimeout(closeTimer.current);
                      setExportTypeDisplay(true);
                    }}
                    onMouseLeave={() => {
                      closeTimer.current = setTimeout(
                        () => setExportTypeDisplay(false),
                        200
                      );
                    }}
                  >
                    <span>{iconMap[type]}</span>
                    <span className="text-[#2A2A2A]">{type}</span>
                  </div>
                ))}
              </div>
            }
            arrow={false}
            styles={{
              root: { padding: 0 },
              body: { padding: 0 }
            }}
          >
            <Button
              disabled={!projectData.id}
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                borderRadius: "4px",
                border: "none"
              }}
              ghost
              onMouseEnter={() => {
                clearTimeout(closeTimer.current);
                setExportTypeDisplay(true);
              }}
              onMouseLeave={() => {
                closeTimer.current = setTimeout(
                  () => setExportTypeDisplay(false),
                  200
                );
              }}
            >
              导出
            </Button>
          </Popover>
        )}
      </>
    ),
    [
      projectData.id,
      exportHover,
      serverInfo,
      projectData.files,
      projectData.sourceList,
      projectData.outputFormat,
      projectData.generateType,
      baseInfo,
      projectData.extraParams,
      projectData.customized_style,
      mainEditor.current,
      projectData.coverPage,
      exportTypeDisplay
    ]
  );

  const StopGen = useCallback(
    () => (
      <Button
        disabled={!projectData.id}
        style={{
          background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
          color: "#fff",
          border: "none",
          borderRadius: "4px"
        }}
        ghost
        onClick={() => handleCancelClick()}
      >
        停止生成
      </Button>
    ),
    [
      projectData.id,
      serverInfo,
      projectData.files,
      projectData.sourceList,
      projectData.outputFormat,
      projectData.generateType,
      baseInfo,
      projectData.extraParams
    ]
  );

  // ====================rag召回相关===================
  const [selectFile, setSelectFile] = useState<any>("");
  // 处理rag召回的问题
  const handleRagReCall = (id: any) => {
    const _selectFile = (projectData?.sourceList || []).find(
      (i) => i.order_num === id
    );
    // const _selectFile = mockList.find((i) => i.order_num === id);
    console.log(_selectFile, id, "rag溯源召回");
    if (!_selectFile || !id) {
      message.warning("当前段落生成成功可查看召回文档");
    }
    setSelectFile(_selectFile);
  };
  // 知识库与素材参考文档统一，增加字段
  const displayListData = useMemo(() => {
    if (!projectData?.files || projectData.files.length === 0) return;
    let _cecArr: any = [];
    let _ragArr: any = [];
    projectData.files.forEach((i) => {
      if (i.order_num) {
        _ragArr.push(i);
      } else {
        _cecArr.push(i);
      }
    });
    // 去重
    _ragArr = uniqBy(_ragArr, "parsedFilePath");
    _cecArr = uniqBy(_cecArr, "materialId");
    return [..._cecArr, ..._ragArr].map((item) => {
      const isRag = !item?.filename;
      const { fileName, fileExtension } = getFileName(
        (item.metadata || {})?.source || ""
      );
      const _filename = isRag ? fileName + "." + fileExtension : item.fileName;
      return {
        ...item,
        filename: _filename,
        isRag
      };
    });
  }, [projectData?.files]);

  const [ragFileInfo, setRagFileInfo] = useState<any>();
  // rag的文件预览
  const handleRagFileClick = (item: any) => {
    console.log(item);
    const { fileName, fileExtension } = getFileName(
      (item.metadata || {})?.source || ""
    );
    const _ragFileInfo = {
      display_file_type: fileExtension,
      file_name: fileName,
      file_source: item.parsedFilePath
    };
    setRagFileInfo(_ragFileInfo);
  };

  // 测试按钮
  const handleClick = () => {
    // 测试预览
    // handleRagFileClick(mockList[2]);
    // 测试召回
    handleRagReCall("4202785257985210054");
  };

  return (
    <>
      {/* <button onClick={() => handleClick()}>测试按钮</button> */}
      <RagReCallDrawer
        selectFile={selectFile}
        clearSelect={() => {
          setSelectFile("");
        }}
      />
      <RagFileView curFileInfo={ragFileInfo} />
      <Drawer
        title={
          <div className="flex items-center">
            <img
              src={FILEIMG[content?.file_type || "doc"]}
              width={18}
              height={18}
              className="mr-[6px]"
            />
            <div>{content?.title}</div>
          </div>
        }
        autoFocus={false}
        onClose={onClose}
        open={showDrawer}
        width={600}
        className="overflow-x-hidden "
      >
        <DrawerContent
          content={content}
          open={showDrawer}
          fileContent={fileContent}
          setFileContent={setFileContent}
        />
      </Drawer>
      <FileViewModal
        showPreviewModal={showFile}
        setShowPreviewModal={setShowFile}
        curFileInfo={curFileInfo}
      />
      <Flex
        justify="space-between"
        style={{
          boxShadow: "0px 9px 28px 8px #0000000D",
          transform: "translate(-50%)"
        }}
        className="absolute z-[999] bottom-[0] left-[49.9%] w-[729px] h-[68px] px-[16px] py-[8px] bg-white box-border"
        align="center"
      >
        {fileListShow && (
          <Flex
            className="absolute z-[999] ml-[-16px] bottom-[68px] w-full px-[16px] py-[8px] bg-white box-border max-h-[500px] overflow-y-auto"
            vertical
            gap={8}
          >
            <Flex justify="space-between">
              <span>参考内容({(displayListData || []).length})</span>
              <CloseOutlined
                onClick={() => {
                  setFileListShow(!fileListShow);
                }}
              />
            </Flex>
            {(displayListData || []).map((item, index) => (
              <Flex
                key={index}
                className="bg-[#F7F8FC] py-[5px] px-[8px] cursor-pointer"
                justify="space-between"
                onClick={() => {
                  item.isRag ? handleRagFileClick(item) : handleFileClick(item);
                }}
              >
                <Flex>{item.filename}</Flex>
                <img src={Go} width={16} height={16} className="mr-[10px]" />
              </Flex>
            ))}
          </Flex>
        )}
        <Flex justify="center" align="center" gap={8}>
          {editorManager.status !== EditorStatus.Waiting && (
            <img
              src={
                editorManager.status === EditorStatus.Success ||
                editorManager.status === EditorStatus.ReviewingSuccess
                  ? Success
                  : Generating
              }
              width={20}
            />
          )}
          <span className="text-[#055AFF] mr-2">
            {getItemInfo(editorManager.status)}
          </span>
          <span className="mr-2 text-[#555555]">
            共<span className="px-1">{projectData.total || 0}</span>字
          </span>
          {(projectData?.files || []).length !== 0 && (
            <>
              <span>参考内容</span>
              <img
                src={fileListShow ? DownArrow : UpArrow}
                alt=""
                width={16}
                onClick={() => setFileListShow(!fileListShow)}
              />
            </>
          )}
        </Flex>
        {/* 全文生成中*/}
        {editorManager.status === EditorStatus.GeneratingFullText && (
          <StopGen />
        )}
        {/* 分段生成中 */}
        {editorManager.status === EditorStatus.GeneratingPartialText && (
          <Flex gap={20} align="center">
            {!!reqSchedule.total && (
              // <Progress
              //   type="circle"
              //   percent={(reqSchedule.cur / reqSchedule.total) * 100}
              //   format={(percent) => `${reqSchedule.cur}/${reqSchedule.total}`}
              //   size={35}
              // />
              <div>
                <span className="text-[#888]">章节完成度&nbsp;</span>
                <span className="text-[#055aff]">{reqSchedule.cur}</span>
                <span>/</span>
                <span className="#2a2a2a">{reqSchedule.total}</span>
              </div>
            )}
            <StopGen />
          </Flex>
        )}
        {/* 规范审核中 */}
        {editorManager.status === EditorStatus.ReviewingFullText && (
          <Button
            disabled={!projectData.id}
            style={{
              background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
              color: "#fff",
              border: "none",
              borderRadius: "4px"
            }}
            ghost
            onClick={() => handleCancelClick()}
          >
            跳过审核
          </Button>
        )}
        {/* 生成成功 */}
        {editorManager.status === EditorStatus.Success && (
          <Flex gap={12}>
            <Button
              disabled={!projectData.id}
              style={{
                color: "#2a2a2a",
                border: "1px solid #eee"
              }}
              ghost
              onClick={() => {
                editorEventBus.emit(EDITOR_EVENT_NAME.START_WRITE);
              }}
            >
              重新生成
            </Button>
            <SaveButton />
            <ReviewButton />
            <ExportButton />
          </Flex>
        )}
        {/* 普通状态 */}
        {editorManager.status === EditorStatus.Waiting && (
          <>
            {editorType === EditorType.Preview ? (
              <Flex gap={20} align="center">
                {!finishStatus.includes(projectData.taskState as DocState) && (
                  <div>
                    <span className="text-[#888]">文章完成度&nbsp;</span>
                    <span className="text-[#055aff]">
                      {projectData.generatedSections}
                    </span>
                    <span>/</span>
                    <span className="#2a2a2a">{projectData.totalSections}</span>
                  </div>
                )}
                {!finishStatus.includes(projectData.taskState as DocState) && (
                  <div>
                    <span className="text-[#888]">任务完成度&nbsp;</span>
                    <span className="text-[#055aff]">
                      {projectData.completedTasks}
                    </span>
                    <span>/</span>
                    <span className="#2a2a2a">{projectData.totalTasks}</span>
                  </div>
                )}
                <Flex gap={12}>
                  <ExportButton />
                </Flex>
              </Flex>
            ) : (
              <Flex gap={12}>
                <SaveButton />
                <ReviewButton />
                <ExportButton />
              </Flex>
            )}
          </>
        )}
        {editorManager.status === EditorStatus.Reviewing && (
          <Flex gap={12}>
            <SaveButton />
            <ReviewButton />
            <ExportButton />
          </Flex>
        )}
        {editorManager.status === EditorStatus.ReviewingSuccess && (
          <Flex gap={12}>
            <SaveButton />
            <ReviewButton />
            <ExportButton />
          </Flex>
        )}
      </Flex>
    </>
  );
};
