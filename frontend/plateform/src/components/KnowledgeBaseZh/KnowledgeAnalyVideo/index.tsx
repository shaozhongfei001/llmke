import { useEffect, useMemo, useRef, useState } from "react";
import axios$ from "@root/src/apis";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { message, Timeline, Image, Space, Popconfirm } from "antd";
import { VideoPlayer, VideoPlayerRef } from "@mxmweb/veoviewer";
import { getUrlPrefix } from "@root/src/core/helps";

import "@mxmweb/veoviewer/style.css";
import empty from "@/assets/knowledgebase/empty.png";
import loadingGif from "@/assets/knowledgebase/loading_gif.gif";
import Back from "../../../assets/img/back.png";
import "./style.less";
const prefix = `${getUrlPrefix()}/index`;

const KnowledgeAnalyVideo = () => {
  const navigator = useNavigate();
  const { id: knowledgeBaseId, fileId }: any = useParams();
  const { state } = useLocation();
  const [curChunk, setCurChunk]: any = useState();
  const [chunks, setChunks] = useState<any[]>([]);
  const [chunksLoading, setChunksLoading] = useState<boolean>(false);
  const playerRef = useRef<VideoPlayerRef>(null);
  const [videoUrl, setVideoUrl] = useState();

  const videoInfo = useMemo(() => {
    return state?.info;
  }, [state]);

  useEffect(() => {
    if (fileId) {
      fetchChunks(fileId);
    }
  }, []);

  const fetchChunks = async (id: number | string) => {
    try {
      const res: any = await axios$.get(
        `${prefix}/videoIndex/queryVideoChunks?docId=${id}`
      );
      if (res?.success) {
        const segs = (res?.data?.chunks?.data || []).map(
          (chunk: any, index: number) => {
            return {
              ...chunk,
              id: index,
              label: chunk.vision,
              start: timeToSeconds(chunk.startTime),
              end: timeToSeconds(chunk.endTime),
              color: getRandomHexColor()
            };
          }
        );
        setChunks(segs);
        setVideoUrl(res?.data?.videoUrl);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const playerConfig = {
    aspectRatio: "16:9", // 宽高比: '16:9' | '4:3' | '1:1' | '21:9'
    theme: "default" as const, // 主题: 'default' | 'dark' | 'minimal'
    showControls: true, // 显示控制条
    showTimeline: true, // 显示时间轴
    showTimelineSegments: true, // 显示时间轴上的段落标记
    showSegments: false, // 显示段落列表
    showDebugInfo: false, // 显示调试信息
    showPlayerState: false, // 显示播放器状态
    useLocalVideo: false // 使用本地视频
  };

  const fileInfo = useMemo(() => {
    return {};
  }, []);

  const timeToSeconds = (timeStr: string) => {
    const [h, m, s] = timeStr.split(":");
    return parseInt(h) * 3600 + parseInt(m) * 60 + parseInt(s);
  };
  const getRandomHexColor = () => {
    return (
      "#" +
      Math.floor(Math.random() * 16777215)
        .toString(16)
        .padStart(6, "0")
    );
  };

  const items = useMemo(() => {
    return chunks.map((item: any, index: number) => {
      return {
        color: "#888888",
        label: `第${index + 1}块`,
        position: "left",
        children: (
          <div
            id={`chunk${item.id}`}
            className="knowledgeBlock bg-[#F3F6FF] px-[16px] pt-[20px] pb-[16px] w-[calc(100%-0px)] rounded-[8px] cursor-pointer overflow-hidden chatView relative"
            style={{
              border:
                curChunk?.id == item.id
                  ? "1px solid #C1D2FF"
                  : "1px solid #F3F6FF"
            }}
            onClick={() => {
              setCurChunk(item);
              playerRef.current?.segments.play(item, { autostop: true });
            }}
          >
            <div className="text-[12px]">{item.label}</div>
            <div style={{ fontSize: "12px", color: "#6b7280" }}>
              {item.startTime.split(".")[0]} - {item.endTime.split(".")[0]}
            </div>
          </div>
        )
      };
    });
  }, [chunks, curChunk]);

  const Header = ({ fileInfo }: any) => {
    return (
      <div
        className="h-[60px] bg-white flex items-center "
        style={{ borderBottom: "1px solid #EEEEEE" }}
      >
        <img
          src={Back}
          width={14}
          height={14}
          className="ml-[16px] cursor-pointer"
          onClick={() => navigator(-1)}
        />
        <div className="text-[16px] font-bold text-text-color1 ml-[35px]">
          {fileInfo?.fileName || "--"}
        </div>
      </div>
    );
  };

  const EmptyBox = () => {
    const navigator = useNavigate();
    return (
      <div className="flex flex-col justify-center items-center">
        <img src={empty} width={106} />
        <div className="text-center mt-[25px]">
          未完成解析，请
          <span
            className="text-blue-400 cursor-pointer"
            onClick={() => navigator(-1)}
          >
            返回上一级
          </span>
        </div>
      </div>
    );
  };
  return (
    <div className="h-full selfTimeLine">
      <Header fileInfo={videoInfo} />
      <div className="h-[calc(100%-60px)] flex">
        <div id="setRenderWidth" className="w-[50%] flex flex-col">
          <div
            id="box"
            className="h-full px-[16px] pt-[16px] flex items-center"
          >
            {videoUrl && (
              <div
                style={{
                  background: "white",
                  borderRadius: "8px",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
                  overflow: "hidden",
                  position: "relative",
                  width: "100%",
                  height: "600px", // 固定高度，播放器会根据宽高比自适应
                  // maxWidth: "800px", // 最大宽度限制
                  margin: "auto" // 居中显示
                }}
              >
                <VideoPlayer
                  ref={playerRef}
                  src={videoUrl}
                  segments={chunks}
                  showControls={playerConfig.showControls}
                  showTimeline={playerConfig.showTimeline}
                  showTimelineSegments={playerConfig.showTimelineSegments}
                  showSegments={false} // 不在播放器内显示段落列表
                  theme={playerConfig.theme}
                  showDebugInfo={playerConfig.showDebugInfo}
                  showPlayerState={playerConfig.showPlayerState}
                  // 响应式尺寸控制
                  aspectRatio={playerConfig.aspectRatio}
                />
              </div>
            )}
          </div>
        </div>
        <div
          className="w-[50%] bg-white px-[16px] pt-[20px] h-full"
          style={{ borderLeft: "1px solid #EEEEEE" }}
        >
          <div className="text-[16px] font-bold text-text-color1 pb-[20px]">
            视频解析
          </div>
          <div className="h-[calc(100%-49px)] overflow-y-auto overflow-x-hidden">
            {chunksLoading && (
              <div className="h-full flex flex-col items-center justify-center">
                <div className=" text-sky-600 animate-pulse -mt-5 ">
                  努力加载中...
                </div>
              </div>
            )}
            {!chunksLoading && chunks.length === 0 && (
              <div className="h-full flex items-center justify-center">
                <EmptyBox />
              </div>
            )}
            <div className="h-full max-w-[calc(100%-70px)]">
              {chunks.length !== 0 && <Timeline items={items} mode="left" />}
              <div className="w-full flex justify-center items-center h-[50px]">
                {chunksLoading && (
                  <img
                    src={loadingGif}
                    height={50}
                    style={{ height: "50px", marginLeft: "110px" }}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KnowledgeAnalyVideo;
