import { useEffect, useMemo, useRef, useState } from "react";
import { CloseOutlined } from "@ant-design/icons";
import { uid } from "uid";
import { VideoPlayer, VideoPlayerRef } from "@mxmweb/veoviewer";
import "@mxmweb/veoviewer/style.css";

const timeToSeconds = (timeStr: string) => {
  const [h, m, s] = timeStr.split(":");
  return parseInt(h) * 3600 + parseInt(m) * 60 + parseInt(s);
};

const DrawerVideo = ({ curFileInfo, onClose }: any) => {
  const chunk = useMemo(
    () => ({
      id: uid(4),
      start: timeToSeconds(curFileInfo.begin_date),
      end: timeToSeconds(curFileInfo.end_date),
      color: "#ef2345"
    }),
    [curFileInfo]
  );

  const playerRef = useRef<VideoPlayerRef>(null);

  useEffect(() => {
    if (curFileInfo.displayType == "retrive" && chunk) {
      setTimeout(() => {
        playerRef.current?.segments.play(chunk, { autostop: true });
      }, 1000);
    }
  }, [chunk]);

  const playerConfig = {
    aspectRatio: "1:1", // 宽高比: '16:9' | '4:3' | '1:1' | '21:9'
    theme: "default" as const, // 主题: 'default' | 'dark' | 'minimal'
    showControls: true, // 显示控制条
    showTimeline: false, // 显示时间轴
    showTimelineSegments: true, // 显示时间轴上的段落标记
    showSegments: false, // 显示段落列表
    showDebugInfo: false, // 显示调试信息
    showPlayerState: false, // 显示播放器状态
    useLocalVideo: false // 使用本地视频
  };

  return (
    <div>
      <div className="h-[52px] flex justify-between leading-[52px] font-bold text-[16px] px-[15px] overflow-hidden border-t-none border-l-none border-b-[1px] border-solid border-[rgb(222,226,230)]">
        {curFileInfo?.source_name || "-"}
        <div onClick={onClose}>
          <CloseOutlined />
        </div>
      </div>
      <div className="h-[calc(100vh-60px)] p-[20px] flex items-center justify-center">
        <div
          style={{
            background: "white",
            borderRadius: "8px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
            overflow: "hidden",
            position: "relative",
            width: "100%",
            height: "400px", // 固定高度，播放器会根据宽高比自适应
            // maxWidth: "800px", // 最大宽度限制
            margin: "auto" // 居中显示
          }}
        >
          <VideoPlayer
            ref={playerRef}
            src={curFileInfo.link}
            segments={[chunk]}
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
      </div>
    </div>
  );
};
export default DrawerVideo;
