import { Button, Divider, message, Space, Tooltip, Typography } from "antd";
import CaretUp from "../../assets/img/caretUp.svg";
import CaretDown from "../../assets/img/caretDown.svg";
import CaretUpClick from "../../assets/img/CaretUpClick.svg";
import CaretDownClick from "../../assets/img/CaretDownClick.svg";
import Refresh from "../../assets/img/refresh.svg";
import Copy from "../../assets/img/copy.svg";
import ArrowUp from "../../assets/img/arrowUp.svg";
import audioGif from "../../assets/img/nlp_chat_audio.png";
import audioPreview from "../../assets/img/audioPreview.png";
import audioPause from "../../assets/img/audioPause.png";
import Genera from "../../assets/img/genera.gif";
import { useMemo, useState } from "react";

import { uid } from "uid";
const FILEIMG: any = {
  docx: doc,
  doc: doc,
  pdf: pdf,
  xls: xls,
  xlsx: xls,
  ppt: ppt,
  pptx: ppt,
  pub: ppt,
  txt: txt
};
import xls from "../../assets/img/xls.png";
import txt from "../../assets/img/txt.png";
import doc from "../../assets/img/doc.png";
import pdf from "../../assets/img/pdf.png";
import ppt from "../../assets/img/ppt.png";
import loading from "../../assets/img/loading.gif";
import { QAChatItem, StatusType } from "../../@types/props";
import { IConversation } from "../../@types/sys";
import { useStateStore } from "../../core/useStateStore";
import FileViewModal from "../FileViewModal";
import ImageGroupView from "@root/src/components/ImageGroupView";
import { WithPlate } from "@root/src/components/CommonEditor/ChatViewEditor";
import copy from "copy-to-clipboard";

interface IChatDisplayItem {
  chatDataLen: number;
  curIndex: number;
  data: QAChatItem;
  clickIndexes: (arg: any) => void;
  stopStream: (id: string) => void;
  reGenerate: () => void;
  handleFeed: (
    type: "thumbsUp" | "thumbsDown",
    queryId: string | undefined,
    restult: number | undefined
  ) => void;
  currentConversation: IConversation | undefined;
  handleEvent?: (type: string, data?: any) => void;
}

const ChatView = (props: IChatDisplayItem) => {
  // console.log(props.data, '打印下ChatView');
  const { appData } = useStateStore();
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [curFileInfo, setCurFileInfo] = useState<string | null>(null);
  const {
    data,
    clickIndexes,
    stopStream,
    reGenerate,
    handleFeed,
    chatDataLen,
    curIndex,
    handleEvent
  } = props;

  const [showContent, setShowContent] = useState(false);
  const [chatListAudioPlay, setChatListAudioPlay] = useState<any>({
    play: false,
    id: ""
  });
  const toCopy = (content: string) => {
    copy(content)
    message.success('复制成功!')
  };
  const hanldePlayDisplayAudio = (chat: any) => {
    // if (!loading && status != StatusType.Process) {
    //   // trigger refresh list to get all audioUrl
    //   props.eventEmitter && props.eventEmitter('audio:refresh', chat.id);
    // } else {
    //   message.info('助手生成中，暂时无法播放，请稍候', 2);
    // }
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

  const assist_name = useMemo(() => {
    if (data?.id && appData.assist_list?.length) {
      const [sessionId, assist_id] = (data.id + "").split("_");
      return (
        appData.assist_list.find((item) => item.value == assist_id)?.label || ""
      );
    }
    return "";
  }, [appData, data]);

  const downLoadFile = async (content: string) => {
    if (handleEvent) {
      handleEvent("fileView", content);
      return;
    }
    setShowPreviewModal(true);
    setCurFileInfo(content);
    // try {
    //   const fileFullPath = content.file_source;
    //   const a = document.createElement('a');
    //   a.download = content.title;
    //   a.href = fileFullPath;
    //   a.style.display = 'none';
    //   document.body.appendChild(a);
    //   a.click();
    //   document.body.removeChild(a);
    // } catch (e) {
    //   message.error('获取引用文件失败，请联系管理员。');
    //   console.log('fetchFullDoc error', e);
    // }
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
      <div className="flex w-full items-start h-fit pt-[16px]">
        {/* <Avatar style={{ width: 32 }} shape="circle" icon={<UserOutlined />} /> */}
        {/* <img src={QuestionAwartar} width={28} height={28} /> */}
        <div className="w-full flex justify-end">
          {
            // if text chat
            props.data.query.type == "text" && (
              <div className="bg-[#F1F6FC] px-[16px] py-[16px] box-border rounded-tr-[2px] rounded-tl-[6px] rounded-br-[6px] rounded-bl-[6px]">
                <div>{props.data.query?.content}</div>
              </div>
            )
          }
        </div>
        {
          // if audio chat
          props.data.query.type == "audio" && (
            <div className="bg-white px-[16px] box-border rounded-tl-[2px] rounded-tr-[6px] rounded-br-[6px] rounded-bl-[6px]">
              <div
                className="w-full"
                style={{
                  width: "312px",
                  height: "50px",
                  border: "1px solid #fff",
                  borderRadius: "8px",
                  padding: "0 12px",
                  background: `url(${audioGif}) no-repeat #F2F6FF 60px center / 240px auto`
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
      <div className="flex w-full items-start gap-3 h-fit pt-[16px] pb-[8px]">
        {/* <img src={AnswerAwartar} width={28} height={28} /> */}
        <div
          style={{
            backgroundColor: "#F8F8F8"
          }}
          className="rounded-tl-[2px] rounded-tr-[6px] rounded-br-[6px] rounded-bl-[6px] flex-col w-full px-[16px] py-[16px]"
        >
          <div className="flex bg-[#F2F6FF] rounded-[4px] h-[32px] items-center px-[8px] text-[12px] text-[#555555]">
            <div className="w-full text-ellipsis break-words line-clamp-1">
              {props.data?.status === StatusType.Process &&
              chatDataLen === curIndex + 1 ? (
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
          <div className="w-full">
            {props?.data?.status === 0 && <img src={loading} width={36} />}
            <WithPlate
              id={uid(32)}
              className="px-0 py-0 text-[14px] text-[#2a2a2a] bg-[#F8F8F8] overflow-x-hidden"
              clickIndexes={clickIndexes}
              data={props.data.answer}
              status={props.data.status}
              imgClassName="!w-[472px] mt-[10px]"
            />
            {!!pic_url_list.length && (
              <div className="flex flex-wrap mt-[10px]">
                <ImageGroupView imageList={pic_url_list} />
              </div>
            )}
          </div>

          <div className="reference flex-col py-2">
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
                  props.data.answer.reference.map((i: any, index) => (
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
                          (i.contents || []).map((item: any, index: number) => {
                            return (
                              <div
                                key={(item as any).id}
                                id={(item as any).id}
                                className="w-[14px] h-[14px] bg-[#E1EBFF] text-[#055AFF] rounded-full text-[10px] flex justify-center items-center ml-[4px] cursor-pointer"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  const p: any = {
                                    ...i,
                                    curMark: (item as any).mark
                                  };
                                  clickIndexes(p);
                                }}
                              >
                                {(item as any).mark}
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
          </div>
          <div className="w-full py-[6px]  flex items-center justify-between">
            {(props.data?.status === 2 || props.data?.status === undefined) &&
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

            {(props.data?.status === 2 || props.data?.status === undefined) && (
              <Space>
                <Button
                  size="small"
                  type="text"
                  icon={
                    <img
                      src={
                        props?.data?.answer?.feedbackResult === 1
                          ? CaretUpClick
                          : CaretUp
                      }
                      className="cursor-pointer"
                    />
                  }
                  onClick={() =>
                    handleFeed(
                      "thumbsUp",
                      props?.data?.query?.queryId,
                      props?.data?.answer?.feedbackResult
                    )
                  }
                ></Button>
                <Divider type="vertical" className="mx-[0] border-[#D8D8D8]" />
                <Button
                  size="small"
                  type="text"
                  icon={
                    <img
                      src={
                        props?.data?.answer?.feedbackResult === 0
                          ? CaretDownClick
                          : CaretDown
                      }
                      className="cursor-pointer"
                    />
                  }
                  onClick={() =>
                    handleFeed(
                      "thumbsDown",
                      props?.data?.query?.queryId,
                      props?.data?.answer?.feedbackResult
                    )
                  }
                ></Button>
                <Divider type="vertical" className="mx-[0] border-[#D8D8D8]" />
                <Button
                  size="small"
                  type="text"
                  icon={<img src={Copy} className="cursor-pointer" />}
                  onClick={() => toCopy(props.data.answer?.content || "")}
                ></Button>
              </Space>
            )}
          </div>
        </div>
      </div>
      <div className="ml-[10px]">
        {props.data?.status === StatusType.Process &&
        chatDataLen === curIndex + 1 ? (
          <Button
            type="link"
            className="w-[56px] text-[14px] text-[#055AFF] cursor-pointer"
            onClick={() => stopStream(props.data?.query?.queryId || "")}
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
  );
};

export default ChatView;
