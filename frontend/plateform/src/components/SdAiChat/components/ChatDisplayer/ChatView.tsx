/* eslint-disable react-hooks/exhaustive-deps */
import AnswerAwartar from "../../assets/img/answerAwartar.png";
import QuestionAwartar from "../../assets/img/questionAwartar.png";
import Refresh from "../../assets/img/refresh.svg";
import audioGif from "../../assets/img/nlp_chat_audio.png";
import audioPreview from "@/assets/img/audioPreview.png";
import audioPause from "@/assets/img/audioPause.png";
import Genera from "../../assets/img/genera.gif";
import loading from "../../assets/img/loading.gif";
import { useMemo, useState } from "react";
import { uid } from "uid";

export const FILEIMG: any = {
  docx: doc,
  doc: doc,
  pdf: pdf,
  xls: xls,
  xlsx: xls,
  ppt: ppt,
  pptx: ppt,
  pub: ppt,
  txt: txt,
  jpeg: img,
  jpg: img,
  png: img
};
import xls from "../../assets/img/xls.png";
import txt from "../../assets/img/txt.png";
import doc from "../../assets/img/doc.png";
import pdf from "../../assets/img/pdf.png";
import ppt from "../../assets/img/ppt.png";
import img from "../../assets/img/img.png";
import { useStateStore } from "../../core/useStateStore";
import { QAChatItem } from "../../@types/props";
import { Button, Divider, message, Space } from "antd";
import FileViewModal from "../FileViewModal";
import ImageGroupView from "@root/src/components/ImageGroupView";
import { WithPlate } from "@root/src/components/CommonEditor/ChatViewEditor";

interface IChatDisplayItem {
  queryBgColor?: string;
  chatDataLen: number;
  curIndex: number;
  // role: 'user' | 'ai';
  data: QAChatItem;
  clickIndexes: (arg: any) => void;
  stopStream: () => void;
  reGenerate: () => void;
  handleFeed: (
    type: "thumbsUp" | "thumbsDown",
    answerId: number | string | undefined,
    restult: number | undefined
  ) => void;
  handleEvent?: (type: string, data?: any) => void;
  handleSd?: (type: string, data?: any) => void;
}

const ChatView = (props: IChatDisplayItem) => {
  const {
    clickIndexes,
    stopStream,
    reGenerate,
    chatDataLen,
    curIndex,
    handleFeed,
    handleSd,
    queryBgColor
  } = props;
  const { appData } = useStateStore();
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [curFileInfo, setCurFileInfo] = useState(null);
  const [chatListAudioPlay, setChatListAudioPlay] = useState<any>({
    play: false,
    id: ""
  }); // 列表中的音频是否在播放中，默认否

  const assist_name = useMemo(() => {
    const configId = props.data.configId;
    if (configId) {
      return (appData?.assist_list || []).find((item) => {
        return item.value === configId;
      })?.label;
    } else {
      return "";
    }
  }, [props.data.configId]);

  const hanldePlayDisplayAudio = (chat: any) => {
    const audioEl = document.getElementById(
      `nlp-chat-display-${chat.id}`
    ) as HTMLAudioElement;

    if (audioEl) {
      audioEl.onplay = () => {
        console.log("audio start playing");
        setChatListAudioPlay({
          play: true,
          id: chat.id
        });
      };
      audioEl.onended = () => {
        console.log("audio start ended");
        setChatListAudioPlay({
          play: false,
          id: ""
        });
      };
      audioEl.src = chat.query.audioUrl;
      audioEl.play();
    }
  };

  const downLoadFile = async (content: any) => {
    handleSd && handleSd("open", content);
    // if (handleEvent) {
    //   handleEvent("fileView", content);
    //   return;
    // }

    // setShowPreviewModal(true);
    setCurFileInfo(content);
  };

  const pic_url_list = useMemo(() => {
    if (props.data?.answer?.reference?.length) {
      const p = props.data.answer.reference[0];
      return [...new Set(p.pic_url_list || [])];
    } else {
      return [];
    }
  }, [props.data]);

  return (
    <>
      {props.data.query && (
        <div className="flex w-full items-start gap-3 h-fit pt-[16px] px-[16px]">
          {/* <Avatar style={{ width: 32 }} shape="circle" icon={<UserOutlined />} /> */}
          <img src={QuestionAwartar} width={28} height={28} />
          {
            // if text chat
            props.data.query.type == "text" && (
              <div
                className={`${
                  queryBgColor || "bg-white"
                } px-[16px] py-[16px] box-border rounded-tl-[2px] rounded-tr-[6px] rounded-br-[6px] rounded-bl-[6px]`}
              >
                <div>{props.data.query?.content}</div>
              </div>
            )
          }
          {
            // if audio chat
            props.data.query.type == "audio" && (
              <div
                className={`${"bg-white"} px-[16px] py-[16px] box-border rounded-tl-[2px] rounded-tr-[6px] rounded-br-[6px] rounded-bl-[6px]`}
              >
                <div
                  className="w-full"
                  style={{
                    width: "300px",
                    height: "50px",
                    border: "1px solid #fff",
                    borderRadius: "8px",
                    background: `url(${audioGif}) no-repeat #fff 60px center / 240px auto`
                  }}
                >
                  <div
                    style={{
                      height: "50px",
                      width: "30px",
                      background:
                        chatListAudioPlay.play &&
                        chatListAudioPlay.id == props.data.id
                          ? `url(${audioPause}) no-repeat center center / 30px 30px`
                          : `url(${audioPreview}) no-repeat center center / 30px 30px`,
                      cursor: "pointer"
                    }}
                    onClick={() => hanldePlayDisplayAudio(props.data)}
                  ></div>
                  <audio id={`nlp-chat-display-${props.data.id}`}></audio>
                </div>
              </div>
            )
          }
        </div>
      )}
      {props.data.query && (
        <>
          <div className="flex w-full items-start gap-3 h-fit px-[16px] pt-[16px] pb-[8px]">
            <img src={AnswerAwartar} width={28} height={28} />
            <div
              style={{
                backgroundColor: "#fff"
              }}
              className="rounded-tl-[2px] rounded-tr-[6px] rounded-br-[6px] rounded-bl-[6px] flex-col w-[calc(100%-32px)] px-[16px] py-[16px]"
            >
              <div className="flex bg-[#F2F6FF] rounded-[4px] h-[32px] items-center px-[8px] text-[12px] text-[#555555]">
                <div className="w-full text-ellipsis break-words line-clamp-1">
                  {props.data?.status === 1 && chatDataLen === curIndex + 1 ? (
                    <div className="flex items-center">
                      <img
                        src={Genera}
                        width={20}
                        height={20}
                        className="mr-[12px]"
                      />
                      <div className="text-[#0C5FFF] ">生成中</div>
                    </div>
                  ) : (
                    <div>回答来自：{assist_name || "无助手展示"}</div>
                  )}
                </div>
              </div>
              <div className="mt-[16px] w-full">
                {props?.data?.status === 0 && <img src={loading} width={36} />}
                <WithPlate
                  id={uid(32)}
                  className="px-0 py-0 text-[14px] text-[#2a2a2a] overflow-x-hidden"
                  clickIndexes={clickIndexes}
                  data={props.data.answer}
                  status={props.data.status}
                  imgClassName="!w-[616px] mt-[10px]"
                />
                {!!pic_url_list.length && (
                  <div className="flex flex-wrap mt-[10px]">
                    <ImageGroupView imageList={pic_url_list} />
                  </div>
                )}
              </div>

              {/* <div className="reference flex-col py-2">
                {props?.data?.answer?.reference?.length ? (
                  <div className="text-[#999999] text-[12px] flex items-center">
                    <div className="mr-[8px] ">
                      参考内容({props?.data?.answer?.reference?.length})
                    </div>
                    <img
                      src={ArrowUp}
                      width={10}
                      height={10}
                      className="cursor-pointer"
                      onClick={() => setShowContent(!showContent)}
                    />
                  </div>
                ) : (
                  <></>
                )}

                {showContent && (
                  <div className="mt-[12px]">
                    {props.data?.answer?.reference?.length &&
                      props.data.answer.reference.map((i, index) => (
                        <div
                          key={index}
                          className="mt-[8px] rounded-[4px] text-[12px] bg-[#F4F5F7] h-[26px] flex items-center px-[8px] cursor-pointer"
                          onClick={() => downLoadFile(i)}
                        >
                          <img
                            src={FILEIMG[i["file_type"]] || FILEIMG["doc"]}
                            width={16}
                            height={16}
                            className="mr-[6px]"
                          />
                          <Tooltip
                            title={`${i["title"]}.${i["file_type"]}`}
                            placement="topLeft"
                            mouseEnterDelay={0.6}
                          >
                            <div className="flex-1 text-ellipsis line-clamp-1 break-words">
                              {i["title"]}.{i["file_type"]}
                            </div>
                          </Tooltip>
                          <div className="shrink-0 flex">
                            {i?.contents?.length ? (
                              (i.contents || []).map((item, index) => {
                                return (
                                  <div
                                    key={item.id}
                                    id={item.id}
                                    className="w-[14px] h-[14px] bg-[#E1EBFF] text-[#055AFF] rounded-full text-[10px] flex justify-center items-center ml-[4px] cursor-pointer"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      const p: any = {
                                        ...i,
                                        curMark: item.mark
                                      };
                                      clickIndexes(p);
                                    }}
                                  >
                                    {item.mark}
                                  </div>
                                );
                              })
                            ) : (
                              <></>
                            )}
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div> */}
              <div className="w-full py-[6px]  flex items-center justify-between">
                {(props.data?.status === 2 ||
                  props.data?.status === undefined) &&
                chatDataLen === curIndex + 1 ? (
                  <Button
                    size="small"
                    type="link"
                    className="text-[14px] px-0"
                    icon={<img src={Refresh} className="cursor-pointer" />}
                    onClick={reGenerate}
                  >
                    重新生成
                  </Button>
                ) : (
                  <div></div>
                )}
              </div>
            </div>
          </div>
          <div className="ml-[75px]">
            {props.data?.status === 1 && chatDataLen === curIndex + 1 ? (
              <Button
                type="link"
                className="w-[56px] text-[14px] text-[#055AFF] cursor-pointer"
                onClick={stopStream}
              >
                停止输出
              </Button>
            ) : (
              <div></div>
            )}
          </div>
          <FileViewModal
            showPreviewModal={showPreviewModal}
            setShowPreviewModal={setShowPreviewModal}
            curFileInfo={curFileInfo}
          />
        </>
      )}
    </>
  );
};

export default ChatView;
