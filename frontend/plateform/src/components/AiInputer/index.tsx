/* eslint-disable react-hooks/exhaustive-deps */
import { Plate, usePlateEditor } from "@udecode/plate-common/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Button,
  Col,
  Flex,
  message,
  Popover,
  Image,
  Space,
  Upload,
  UploadProps,
  UploadFile
} from "antd";
import { string } from "slate";
import { ChatEditor } from "@/components/CommonEditor/ChatEditor.tsx";
import { useAudioRecorder } from "./common/useAudioRecorder.tsx";
import cleanAll from "@/assets/img/cleanAll.png";
import chat_audio_default from "@/assets/img/chat_audio_default.png";
import chat_audio_stop from "@/assets/svg/nlp_chat_audio_stop.svg";
import chat_disabled from "@/assets/img/chat_disabled.png";
import chat_audio_disabled from "@/assets/img/chat_audio_disabled.png";
import chat_send from "@/assets/img/chat_send.png";
import audio_gif from "@/assets/img/nlp_chat_audio.gif";
import audioPause from "@/assets/img/audioPause.png";
import audioPreview from "@/assets/img/audioPreview.png";
import chat_audio_remove from "@/assets/svg/nlp_chat_audio_remove.svg";
import inputer_upload_default from "@/assets/img/inputer_upload_default.png";
import inputer_upload_hover from "@/assets/img/inputer_upload_hover.png";
import { Node } from "slate";
import inputer_upload_disable from "@/assets/img/inputer_upload_disable.png";
import { useAppPassport } from "@root/src/core/helps/appPassport.tsx";
import { FileItem } from "../FileItem/index.tsx";
import {
  api_getFileExist,
  api_getFileStatusByUid,
  api_uploadFiles
} from "./common/services/servers.ts";
import _ from "lodash";
import { getUrlPrefix } from "@root/src/core/helps/index.ts";
export const baseURL = getUrlPrefix();
interface ChatInputerProps {
  sessionId?: string | undefined;
  onSend: (
    editor: any,
    audioText?: string,
    audioConfig?: { audioUrl?: string },
    docs?: any[]
  ) => void;
  btnLoading: boolean;
  inputer: any;
  conversationData: any;
  clearInputer: any;
  uploadAudio: any;
  className?: string;
  handleEvent?: (type: string, data?: any) => void;
  hideBtn?: boolean;
  showFileUpload?: boolean;
}

const BUTTON_SIZE = "32px";
const BUTTON_RADIUS = 0;
const btnClass = `h-${BUTTON_SIZE} !border-none w-${BUTTON_SIZE} bg-transparent border-[1px] border-solid border-transparent mr-[12px] hover:!border-transparent hover:bg-transparent`;
let intervalIdTimer: any = null;
let fileStatusTimer: any = null;
const AiInputer: React.FC<ChatInputerProps> = ({
  onSend,
  btnLoading,
  inputer,
  conversationData,
  clearInputer,
  uploadAudio,
  className,
  handleEvent,
  hideBtn,
  showFileUpload,
  sessionId
}) => {
  const { startRecording, stopRecording, recordingState } = useAudioRecorder();
  const { getToken }: any = useAppPassport();
  const token: any = getToken();
  const chatInputEditor = usePlateEditor({ id: "inputer" });
  const [audioStatus, setAudioStatus] = useState("init"); // init & stop
  const [audioLocal, setAudioLocal] = useState<any>({});
  const [audioDuration, setAudioDuration] = useState(0);
  const [showSTTContent, setShowSTTContent] = useState(false);
  const [isUploadFile, setIsUploadFile] = useState(false);
  const [sttContent, setSTTContent] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [fileList, setFileList] = useState<any>([]);

  useEffect(() => {
    console.log("====================================");
    console.log("fileList", fileList);
    console.log("====================================");
  }, [fileList]);

  const handleSendClick = () => {
    if (disableSend || btnLoading || !inputer.current) return; // Add this check to ensure inputer.current is defined
    const inputContent = string(inputer.current as any, [0]);
    if ((audioUrl && !sttContent) || (!audioUrl && !inputContent)) {
      message.warning("请输入您的问题!");
      return;
    }

    const audioConfig = {
      audioUrl
    };

    onSend(inputContent, sttContent, audioConfig, fileList);
    setFileList([]);
  };

  // TODO detect input change

  useEffect(() => {
    clearInputer(chatInputEditor);
    setFileList([]);
  }, [conversationData.id]);

  useEffect(() => {
    removeLocalAudio();
  }, []);

  const handleAudioUpload = async () => {
    const sttRes = await uploadAudio(audioLocal);
    setSTTContent(sttRes?.content || "");

    setAudioUrl(sttRes?.audioUrl);
  };

  useEffect(() => {
    if (audioLocal && audioLocal?.audioUrl && audioStatus == "stop") {
      // if audio updated, trigger upload and STT
      handleAudioUpload();
    }
  }, [audioLocal]);
  const [chatListAudioPlay, setChatListAudioPlay] = useState<any>({
    play: false,
    id: ""
  });
  const previewLocalAudio = () => {
    const audioEl = document.getElementById(
      "nlp-chat-audio-preview"
    ) as HTMLAudioElement;
    if (audioEl) {
      const id = new Date().getTime();
      audioEl.onplay = () => {
        console.log("audio start playing");
        setChatListAudioPlay({
          play: true,
          id
        });
      };
      audioEl.onended = () => {
        console.log("audio start ended");
        setChatListAudioPlay({
          play: false,
          id
        });
      };
      audioEl?.play();
    }
  };

  const removeLocalAudio = () => {
    setAudioLocal({});
    setAudioStatus("init");
    setAudioDuration(0);
    setShowSTTContent(false);
    setAudioUrl("");
    intervalIdTimer = null;
    clearInterval(intervalIdTimer);
    inputer?.current?.insertText("");
  };

  const handleAudioSend = () => {
    if (inputer?.current) {
      inputer.current.insertText(sttContent);
    }

    // const data = Node.string(inputer.current as any);

    // reset audio status
    setAudioLocal({});
    setAudioUrl("");
    setAudioStatus("init");
    setAudioDuration(0);
    setShowSTTContent(false);

    handleSendClick();
  };

  const handleClick = () => {
    // 录音状态 禁用发送
    if (recordingState !== "inactive") return;

    if (audioStatus === "init") {
      handleSendClick();
    } else if (audioStatus === "stop") {
      handleAudioSend();
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (!event.shiftKey && event.key === "Enter") {
      event.preventDefault();

      handleSendClick();
    }
  };

  const handleAudioRecord = async () => {
    let action: string = "";
    if (recordingState === "inactive" && audioStatus === "init") {
      action = "init";
    } else if (recordingState !== "inactive") {
      action = "stop";
    } else {
      return;
    }

    try {
      if (recordingState === "inactive") {
        await startRecording();

        // active timer
        const start = Date.now();
        intervalIdTimer = setInterval(() => {
          const delta = Date.now() - start; // milliseconds elapsed since start
          setAudioDuration(Math.floor(delta / 1000));
        }, 1000);
      } else if (recordingState === "recording") {
        const record_value = await stopRecording(true);
        intervalIdTimer = null;
        clearInterval(intervalIdTimer);
        setAudioLocal(record_value);
      }

      if (action == "stop") {
        setAudioStatus(action);
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  const getAudioDisabled = useMemo(() => {
    return (
      (recordingState === "inactive" && audioStatus !== "init") ||
      btnLoading ||
      isUploadFile
    );
  }, [recordingState, audioStatus, isUploadFile, btnLoading]);

  const disableSend = useMemo(() => {
    return !(recordingState === "inactive" && !isUploadFile);
  }, [recordingState, isUploadFile]);

  const getUploadDisabled = useMemo(() => {
    return !(recordingState === "inactive" && !btnLoading);
  }, [recordingState, audioStatus, btnLoading]);

  const getUploadImg = useMemo(() => {
    if (getUploadDisabled) {
      return inputer_upload_disable;
    } else {
      return inputer_upload_default;
    }
  }, [getUploadDisabled]);

  const getAudioImg = useMemo(() => {
    if (getAudioDisabled) {
      return chat_audio_disabled;
    } else if (recordingState === "inactive") {
      return chat_audio_default;
    } else {
      return chat_audio_stop;
    }
  }, [recordingState, getAudioDisabled]);

  const getSendImg = useMemo(() => {
    if (disableSend) {
      return chat_disabled;
    } else {
      return chat_send;
    }
  }, [disableSend]);

  const uploadWarning = useCallback(
    _.throttle(
      (msg: string) => {
        message.warning(msg);
      },
      200,
      { leading: false }
    ),
    []
  );

  const handleDeleteFile = (type: string, uid: string) => {
    setFileList((pre: any) => {
      return [...pre.filter((item: any) => item.uid !== uid)];
    });
  };

  const props: UploadProps = {
    name: "file",
    multiple: true,
    accept:
      ".ppt,.pptx,.pdf,.docx,.txt,.xlsx,.xls,.csv,.jpeg,.md,.json,.jpg,.png,.doc",
    onRemove: (file) => {
      setFileList((fileList: any) => {
        return [...fileList.filter((item: any) => item.uid !== file.uid)];
      });
    },
    beforeUpload: async (file, _fileList) => {
      const hasUid = _fileList.some((item) => !item.uid);
      if (hasUid) return false;

      const _rest = _fileList.map((item: any) => {
        item.status = "loading";
        return item;
      });

      const { name, size } = file;

      if (size === 0) {
        uploadWarning(`《${name}》是空文件,请勿添加`);
        return false;
      }

      if (size > 52428800) {
        uploadWarning(`《${name}》文件大于50MB,请勿添加`);
        return false;
      }

      if (fileList.find((f: UploadFile) => f.name === name)) {
        uploadWarning(`文件《${name}》已存在上传队列中,请勿重复添加`);
        return false;
      }

      const allFileList = [...fileList, ..._rest];

      const sizeSum: number = allFileList.reduce(
        (sum, item) => sum + item.size,
        0
      );
      if (sizeSum > 104857600) {
        uploadWarning(`文件总大小超过100MB,请勿添加`);
        return false;
      }

      if (allFileList.length > 10) {
        uploadWarning("支持上传文件最多10个");
        return false;
      }

      const res = await getFileExist(file.name);
      if (res) {
        uploadWarning(`文件《${name}》已上传,请勿重复添加`);
        return false;
      }

      setFileList(allFileList);
      uploadFileFn(_fileList);

      return false;
    },
    onChange(info) {
      console.log(info, 456465);

      if (info.file.status === "done") {
        message.success(`${info.file.name} file uploaded successfully`);
      } else if (info.file.status === "error") {
        message.error(`${info.file.name} file upload failed.`);
      }
    }
  };

  const setFilesStatus = (data: any[]) => {
    const map = new Map();
    data.forEach((item: any) => {
      map.set(item.uid, item);
    });

    setFileList((pre: any[]) => {
      return pre.map((item: any) => {
        const cur = map.get(item.uid);
        if (cur) {
          return {
            id: cur.id,
            uid: item.uid,
            name: item.name,
            status:
              cur?.status === 3
                ? "done"
                : cur?.status === 4
                  ? "fail"
                  : "analysis",
            filePath: cur?.filePath || item.filePath,
            convertedFilePath: cur?.convertedFilePath || item.convertedFilePath,
            size: cur?.size || item.size,
            type: item.type
          };
        }
        return item;
      });
    });
  };

  const getFileExist = async (fileName: string) => {
    try {
      const res = await api_getFileExist({
        data: { kbName: sessionId, fileName },
        config: {
          url: baseURL,
          token,
          enableMock: false
        }
      });
      return res;
    } catch (error) {
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  const getStatus = async (analysisFiles: any[]) => {
    try {
      const uids = analysisFiles.map((item) => {
        return item.uid;
      });
      const res: any[] = await api_getFileStatusByUid({
        data: { uids: uids.join(",") },
        config: {
          url: baseURL,
          token,
          enableMock: false
        }
      });
      setFilesStatus(res);
    } catch (error) {
      clearFileStatus();
      console.log(error);
    }
  };

  const getInterStatus = (analysisFiles: any[]) => {
    clearInterval(fileStatusTimer);
    fileStatusTimer = null;
    fileStatusTimer = setInterval(() => {
      getStatus(analysisFiles);
    }, 5000);
  };

  const uploadFileFn = async (fileList: any) => {
    const formData = new FormData();
    const _uids: any = [];
    fileList.forEach((file: any) => {
      console.log("file", file);
      formData.append("files", file);
      _uids.push(file.uid);
    });
    sessionId && formData.append("sessionId", sessionId);
    formData.append("uids", _uids);
    try {
      setIsUploadFile(true);
      const res = await api_uploadFiles({
        data: formData,
        config: {
          url: baseURL,
          token,
          enableMock: false
        }
      });
      setFilesStatus(res);
    } catch (error) {
      console.log(error);
    }
  };

  useEffect(() => {
    const analysisFiles: any = [];
    const loadingFiles: any = [];
    const failFiles: any = [];
    if (
      fileList.length &&
      inputer.current &&
      !Node.string(inputer.current as any)
    ) {
      console.log("inputer.current", inputer.current);
      inputer.current.tf.setValue([
        {
          type: "p",
          children: [{ text: "总结主要内容" }]
        }
      ]);
      //inputer.current.insertText("总结主要内容");
    }
    fileList.forEach((item: any) => {
      item.status === "analysis" && analysisFiles.push(item);
      item.status === "loading" && loadingFiles.push(item);
      item.status === "fail" && failFiles.push(item);
    });
    if (!analysisFiles.length && !loadingFiles.length && !failFiles.length) {
      setIsUploadFile(false);
    }
    if (analysisFiles.length) {
      getInterStatus(analysisFiles);
    } else {
      clearFileStatus();
    }
  }, [fileList]);

  const clearFileStatus = () => {
    clearInterval(fileStatusTimer);
    fileStatusTimer = null;
  };

  useEffect(() => {
    return () => {
      clearInterval(intervalIdTimer);
      intervalIdTimer = null;
      clearFileStatus();
    };
  }, []);

  return (
    <Plate editor={chatInputEditor}>
      <div
        className={`${className || ""} editor-input backdrop-blur-[1px] pt-[3px] left-0`}
      >
        {!(
          recordingState !== "inactive" ||
          (recordingState === "inactive" && audioStatus === "stop")
        ) &&
          !hideBtn && (
            <Button
              className="border-[#EEEEEE] text-text-color2 mb-[8px]"
              size="small"
              icon={<img src={cleanAll} />}
              onClick={() => handleEvent && handleEvent("cleanAll")}
              disabled={btnLoading}
            >
              清空对话
            </Button>
          )}
        {
          // recording
          recordingState !== "inactive" && (
            <div
              style={{
                marginBottom: "5px",
                border: "2px solid #fff",
                height: "52px",
                background: `url(${audio_gif}) #fff no-repeat center center`,
                backgroundSize: "auto 50px",
                borderRadius: "8px",
                display: "flex",
                justifyContent: "flex-end"
              }}
            >
              <div
                style={{
                  height: "50px",
                  width: "50px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center"
                }}
              >
                {audioDuration}"
              </div>
            </div>
          )
        }
        {recordingState === "inactive" && audioStatus === "stop" && (
          <div
            style={{
              marginBottom: "5px",
              border: "2px solid #fff",
              borderRadius: "8px",
              backgroundColor: "#fff"
            }}
          >
            {showSTTContent ? (
              <div
                style={{
                  borderRadius: "8px 8px 0 0 ",
                  fontSize: "12px",
                  borderBottom: "1px solid #E4E8F5",
                  height: "100%",
                  maxHeight: "60px",
                  minHeight: "50px",
                  overflowY: "auto",
                  padding: "15px"
                }}
              >
                {sttContent}
              </div>
            ) : (
              <div
                style={{
                  height: "35px",
                  borderBottom: "1px solid #E4E8F5",
                  lineHeight: "30px",
                  fontSize: "12px",
                  borderRadius: "8px 8px 0 0 ",
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  cursor: "pointer",
                  position: "relative"
                }}
                onClick={() => setShowSTTContent(true)}
              >
                语音转文字
              </div>
            )}
            <div
              style={{
                width: "100%",
                height: "52px",
                background: `url(${audio_gif}) #fff no-repeat center center`,
                backgroundSize: "auto 50px",
                borderRadius: "0 0 8px 8px",
                display: "flex",
                justifyContent: "space-between"
              }}
            >
              <div
                style={{
                  height: 50,
                  width: 50,
                  background: chatListAudioPlay.play
                    ? `url(${audioPause}) no-repeat center center / 30px 30px`
                    : `url(${audioPreview}) no-repeat center center / 30px 30px`,
                  cursor: "pointer"
                }}
                onClick={previewLocalAudio}
              ></div>
              <Flex>
                <label
                  style={{
                    lineHeight: "50px"
                  }}
                >
                  {audioDuration}"
                </label>
                <div
                  className="nlp-chat-audio-remove"
                  style={{
                    height: 50,
                    width: 50,
                    background: `url(${chat_audio_remove}) no-repeat center center`,
                    cursor: "pointer"
                  }}
                  onClick={removeLocalAudio}
                ></div>
              </Flex>
              <audio
                id="nlp-chat-audio-preview"
                src={audioLocal.audioUrl}
                preload="metadata"
              ></audio>
            </div>
          </div>
        )}

        <div className="relative min-h-[56px] bg-white rounded-[4px] border-[1px] border-solid border-[#D9D9D9]">
          {!!fileList.length && (
            <div className="px-[8px] mb-[16px] mt-[8px] max-h-[150px] overflow-auto">
              <FileItem
                fileList={fileList}
                handleDeleteFile={handleDeleteFile}
                idx={1}
              />
            </div>
          )}
          <div className="flex items-center">
            <ChatEditor
              onKeyDown={handleKeyDown}
              className="!border-none rounded-[4px] outline-none !leading-[38px] mr-[10px]"
              inputer={inputer}
            />
            <div className="flex mx-[12px] items-center">
              {showFileUpload && (
                <Upload
                  {...props}
                  showUploadList={false}
                  className="mt-[6px]"
                  disabled={getUploadDisabled}
                >
                  <Popover
                    placement="top"
                    color="linear-gradient(90deg,#2B69FF,#8F91FF)"
                    content={
                      <div className="w-[225px] text-white">
                        最多上传10个文件(每个最大 50
                        MB)支持单次或批量上传ppt(x)、doc(x)、xlsx、csv、pdf、text、html、md、json、jp(e)g、png
                      </div>
                    }
                  >
                    <Button
                      icon={
                        <img
                          src={getUploadImg}
                          style={{
                            height: BUTTON_SIZE,
                            width: BUTTON_SIZE,
                            borderRadius: BUTTON_RADIUS,
                            cursor: getUploadDisabled
                              ? "not-allowed"
                              : "pointer"
                          }}
                        ></img>
                      }
                      className={btnClass}
                    ></Button>
                  </Popover>
                </Upload>
              )}

              <Button
                onClick={() => {
                  !getAudioDisabled && handleAudioRecord();
                }}
                icon={
                  <img
                    src={getAudioImg}
                    style={{
                      height: BUTTON_SIZE,
                      width: BUTTON_SIZE,
                      borderRadius: BUTTON_RADIUS,
                      cursor: getAudioDisabled ? "not-allowed" : "pointer"
                    }}
                  ></img>
                }
                className={btnClass}
              ></Button>
              <Button
                icon={
                  <img
                    src={getSendImg}
                    style={{
                      height: BUTTON_SIZE,
                      width: BUTTON_SIZE,
                      borderRadius: BUTTON_RADIUS,
                      cursor: disableSend ? "not-allowed" : "pointer"
                    }}
                  ></img>
                }
                className={`!mr-0 ${btnClass} !border-none`}
                loading={btnLoading}
                onClick={handleClick}
                disabled={disableSend}
              ></Button>
            </div>
          </div>
        </div>
      </div>
    </Plate>
  );
};

export default AiInputer;
