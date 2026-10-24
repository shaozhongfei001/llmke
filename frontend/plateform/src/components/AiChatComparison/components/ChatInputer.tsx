import { Plate, usePlateEditor } from "@udecode/plate-common/react";

import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Col, Flex, message, Row, Space } from "antd";
import { useAiCompareCore } from "../core/operators/useAiCompareCore.tsx";
import { useStateStore } from "../core/useStateStore.tsx";
import chat_audio_preview from "../assets/img/nlp_chat_audio_preview.svg";
import chat_audio_remove from "../assets/img/nlp_chat_audio_remove.svg";
import chat_audio_stop from "../assets/img/nlp_chat_audio_stop.svg";
import chat_send from "../assets/img/chat_send.svg";
import audio_gif from "../assets/img/nlp_chat_audio.gif";
import chat_audio_default from "../assets/chat_audio_default.svg";
import chat_disabled from "../assets/chat_disabled.svg";
import { uid } from "uid";
import { SystemStatus } from "../@types/sys.ts";
import { ChatEditor } from "./editor/ChatEditor.tsx";
import audioPause from "../assets/img/audioPause.png";
import { useAudioRecorder } from "../core/useAudioRecorder.tsx";
import { Node } from "slate";
interface ChatInputerProps {
  onSend?: (data: any) => void;
  btnLoading: number;
}
const BUTTON_SIZE = 40;
const ChatInputer: React.FC<ChatInputerProps> = ({ onSend, btnLoading }) => {
  const { startRecording, stopRecording, recordingState } = useAudioRecorder();
  const chatInputEditor = usePlateEditor({ id: "inputer" });
  const { inputer, appData, setAppData } = useStateStore();
  const { isRetriveSideOpen, clearInputer, uploadAudio } = useAiCompareCore();
  const [audioUrl, setAudioUrl] = useState("");
  const [audioStatus, setAudioStatus] = useState("init"); // init & stop
  const [audioLocal, setAudioLocal] = useState<any>({});
  const [audioDuration, setAudioDuration] = useState(0);
  const [intervalId, setIntervalId] = useState<any>();
  const [showSTTContent, setShowSTTContent] = useState(false);
  const [sttContent, setSTTContent] = useState("");

  const handleSendClick = () => {
    if (!inputer.current) return; // Add this check to ensure inputer.current is defined
    const inputContent = Node.string(inputer.current as any);
    if ((audioUrl && !sttContent) || (!audioUrl && !inputContent)) {
      message.warning("请输入您的问题");
      return;
    }

    const isAssistantIdEmpty = appData.conversations.some((item, index) => {
      !item?.assist_id && message.warning(`对话${index + 1}请选择助手`);
      return !item?.assist_id;
    });
    if (isAssistantIdEmpty) {
      return;
    }
    const updatedConversations = appData.conversations?.map((conv, index) => {
      if (!conv.assist_id) {
        return conv;
      }
      return {
        ...conv,
        status: SystemStatus.Process,
        question: {
          // 使用新的对象结构
          assist_id: conv?.assist_id,
          dialog_id: conv.id + "_" + conv?.assist_id,
          content: sttContent || inputContent || "",
          chat_id: `chat-${uid(32)}`,
          audioConfig: { audioUrl }
        }
      };
    });
    setAppData((prevAppData) => {
      return {
        ...prevAppData,
        status: SystemStatus.Process,
        conversations: updatedConversations
      };
    });
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (!event.shiftKey && event.key === "Enter") {
      event.preventDefault();
      handleSendClick();
    }
  };

  const handleAudioRecord = async (action: string) => {
    console.log("recordingState", recordingState);
    if (recordingState == "inactive") {
      await startRecording();

      // active timer
      const start = Date.now();
      setIntervalId(
        setInterval(() => {
          const delta = Date.now() - start; // milliseconds elapsed since start
          setAudioDuration(Math.floor(delta / 1000));
        }, 1000) // update about every second
      );
    } else if (recordingState == "recording") {
      const record_value = await stopRecording(true);

      clearInterval(intervalId);
      setAudioLocal(record_value);
    }

    if (action == "stop") {
      setAudioStatus(action);
    }
  };

  const handleAudioUpload = async () => {
    const sttRes = await uploadAudio(audioLocal);
    setSTTContent(sttRes?.content || "");
    setAudioUrl(sttRes?.audioUrl);
  };
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
    inputer?.current?.insertText("");
  };

  const handleAudioSend = () => {
    if (inputer && inputer.current) {
      inputer.current.insertText(sttContent);
    }

    // reset audio status
    setAudioLocal({});
    setAudioUrl("");
    setAudioStatus("init");
    setAudioDuration(0);
    setShowSTTContent(false);

    handleSendClick();
  };

  useEffect(() => {
    if (audioLocal && audioLocal?.audioUrl && audioStatus == "stop") {
      // if audio updated, trigger upload and STT
      handleAudioUpload();
    }
  }, [audioLocal]);

  return (
    <Plate editor={chatInputEditor}>
      <div className="editor-input backdrop-blur-[1px] absolute bottom-0  pt-[3px] w-full left-0 flex justify-center items-center">
        <div className="w-full relative">
          <Row>
            <Col
              span={isRetriveSideOpen ? 12 : 16}
              offset={isRetriveSideOpen ? 2 : 4}
            >
              <Row gutter={8} align="middle" wrap={false}>
                {
                  // before recording
                  recordingState == "inactive" && audioStatus == "init" && (
                    <>
                      <Col flex="auto">
                        <ChatEditor
                          onKeyDown={handleKeyDown}
                          className="border-[1px] border-solid border-[#D9D9D9] rounded-[4px] outline-none leading-[32px]"
                        />
                      </Col>
                      <Col flex="120px" className="h-[50px]">
                        <Space className="h-full flex items-center">
                          <Button
                            onClick={() => handleAudioRecord("init")}
                            icon={
                              <img
                                src={chat_audio_default}
                                style={{
                                  height: BUTTON_SIZE,
                                  width: BUTTON_SIZE,
                                  borderRadius: BUTTON_SIZE
                                }}
                              ></img>
                            }
                            style={{
                              height: BUTTON_SIZE + 2,
                              width: BUTTON_SIZE + 2,
                              border: "1px solid transparent",
                              backgroundColor: "transparent"
                            }}
                          ></Button>
                          <Button
                            icon={
                              <img
                                src={chat_send}
                                style={{
                                  height: BUTTON_SIZE,
                                  width: BUTTON_SIZE,
                                  borderRadius: BUTTON_SIZE
                                  // background: "red"
                                }}
                              ></img>
                            }
                            style={{
                              height: BUTTON_SIZE + 2,
                              width: BUTTON_SIZE + 2,

                              // background: 1
                              //   ? `center url(${chat_send}) no-repeat`
                              //   : `center url(${chat_disabled}) no-repeat`,
                              border: "1px solid transparent",
                              backgroundColor: "transparent"
                            }}
                            loading={!!btnLoading}
                            onClick={handleSendClick}
                          ></Button>
                        </Space>
                      </Col>
                    </>
                  )
                }
                {
                  // recording
                  recordingState != "inactive" && (
                    <>
                      <Col flex="auto">
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
                            {/* timer */}
                            {audioDuration}"
                          </div>
                        </div>
                        <ChatEditor className="border-[1px] border-solid border-[#D9D9D9] rounded-[4px] outline-none leading-[32px]" />
                      </Col>
                      <Col flex="120px" className="h-[50px]">
                        <Space className="h-full flex items-center">
                          <Button
                            icon={
                              <img
                                src={chat_audio_stop}
                                style={{
                                  height: BUTTON_SIZE,
                                  width: BUTTON_SIZE,
                                  borderRadius: BUTTON_SIZE
                                }}
                              ></img>
                            }
                            style={{
                              height: BUTTON_SIZE,
                              width: BUTTON_SIZE,
                              borderRadius: BUTTON_SIZE,
                              border: "none",
                              backgroundColor: "transparent"
                            }}
                            onClick={() => handleAudioRecord("stop")}
                          ></Button>
                          <Button
                            icon={
                              <img
                                src={chat_disabled}
                                style={{
                                  height: BUTTON_SIZE,
                                  width: BUTTON_SIZE,
                                  borderRadius: BUTTON_SIZE
                                }}
                              ></img>
                            }
                            style={{
                              height: BUTTON_SIZE,
                              width: BUTTON_SIZE,
                              borderRadius: BUTTON_SIZE,
                              border: "none",
                              backgroundColor: "transparent"
                            }}
                          ></Button>
                        </Space>
                      </Col>
                    </>
                  )
                }
                {
                  // after recording, before sent
                  recordingState == "inactive" && audioStatus == "stop" && (
                    <>
                      <Col flex="auto">
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
                              className="nlp-chat-stt-container"
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
                              className="nlp-chat-audio-preview"
                              style={{
                                height: 50,
                                width: 50,
                                background: chatListAudioPlay.play
                                  ? `url(${audioPause}) no-repeat center center / 30px 30px`
                                  : `url(${chat_audio_preview}) no-repeat center center / 30px 30px`,
                                cursor: "pointer"
                              }}
                              onClick={previewLocalAudio}
                            ></div>
                            <Flex>
                              {/* timer */}
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
                        <ChatEditor
                          onKeyDown={handleKeyDown}
                          className="border-[1px] border-solid border-[#D9D9D9] rounded-[4px] outline-none leading-[32px]"
                        />
                      </Col>
                      <Col flex="120px" className="h-[50px]">
                        <Space className="h-full flex items-center">
                          <Button
                            icon={
                              <img
                                src={chat_audio_default}
                                style={{
                                  height: BUTTON_SIZE,
                                  width: BUTTON_SIZE,
                                  borderRadius: BUTTON_SIZE
                                }}
                              ></img>
                            }
                            style={{
                              height: BUTTON_SIZE,
                              width: BUTTON_SIZE,
                              borderRadius: BUTTON_SIZE,
                              border: "none",
                              backgroundColor: "transparent"
                            }}
                          ></Button>
                          <Button
                            icon={
                              <img
                                src={chat_send}
                                style={{
                                  height: BUTTON_SIZE,
                                  width: BUTTON_SIZE,
                                  borderRadius: BUTTON_SIZE
                                }}
                              ></img>
                            }
                            style={{
                              height: BUTTON_SIZE,
                              width: BUTTON_SIZE,
                              border: "none",
                              backgroundColor: "transparent"
                            }}
                            onClick={handleAudioSend}
                          ></Button>
                        </Space>
                      </Col>
                    </>
                  )
                }
              </Row>
            </Col>
          </Row>
        </div>
      </div>
    </Plate>
  );
};

export default ChatInputer;
