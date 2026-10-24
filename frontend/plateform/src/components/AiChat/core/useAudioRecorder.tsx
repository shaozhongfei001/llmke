import { useState, useCallback, useRef } from "react";
import { uid } from "uid";

type RecorderState = "inactive" | "recording" | "paused";
interface AudioRecording {
  audioUrl: string;
  id: string;
  name?: string;
}
enum SupportEnum {
  UNKNOWN = "unknown",
  SUPPORTED = "supported",
  UNSUPPORTED = "unsupported"
}

export function useAudioRecorder() {
  const [recordings, setRecordings] = useState<AudioRecording[]>([]);
  const [recorder, setRecorder] = useState<MediaRecorder | null>(null);
  const [recordingState, setRecordingState] =
    useState<RecorderState>("inactive");
  const [isDeviceSupported, setIsDeviceSupported] = useState<SupportEnum>(
    SupportEnum.UNKNOWN
  );
  const [audioChunks, setAudioChunks] = useState<any>([]);

  const handleDataAvailable = useCallback((event: BlobEvent) => {
    if (event.data.size > 0) {
      setAudioChunks((prev: any) => [...prev, event.data]);
    }
  }, []);

  const stopRecording = async (immediate: boolean = false) => {
    return new Promise((resolve, reject) => {
      if (!recorder) {
        console.error("Recorder not initialized.");
        reject();
        return;
      }

      recorder.onstop = async () => {
        if (audioChunks.length === 0) {
          console.error("No data received before stopping the recorder");
          reject();
          return;
        }

        const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
        const audioUrl = URL.createObjectURL(audioBlob);
        const newRecording = {
          audioUrl,
          id: uid(32),
          name: "未命名录音" + new Date().getTime()
        };

        setAudioChunks([]); // 清空 chunks

        if (immediate) {
          setRecordingState("inactive");
          resolve(newRecording);
        } else {
          setRecordings((prevRecordings) => [...prevRecordings, newRecording]);
          setRecordingState("inactive");
          resolve(newRecording.id);
        }
      };

      recorder.stop();
      // recorder.stream
      //   .getTracks() // get all tracks from the MediaStream
      //   .forEach((track) => track.stop()); // stop each of them
    });
  };
  const checkDeviceSupport = useCallback(async () => {
    if (!navigator.mediaDevices || !MediaRecorder) {
      setIsDeviceSupported(SupportEnum.UNSUPPORTED);
      console.error("Audio recording not supported by this browser");
      return null;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const newRecorder = new MediaRecorder(stream);
      setIsDeviceSupported(SupportEnum.SUPPORTED);
      return newRecorder; // 返回创建的新Recorder
    } catch (error) {
      setIsDeviceSupported(SupportEnum.UNSUPPORTED);
      console.error("Error accessing microphone:", error);
      return null;
    }
  }, []);

  const startRecording = async () => {
    if (isDeviceSupported === SupportEnum.UNSUPPORTED) return;

    let activeRecorder = recorder; // 使用一个局部变量来持有recorder

    // 检查并可能初始化recorder
    if (!activeRecorder) {
      activeRecorder = await checkDeviceSupport();
      if (!activeRecorder) return; // 如果设备不支持或初始化失败，直接返回
      setRecorder(activeRecorder); // 更新状态，但此次不依赖它
    }

    activeRecorder.start(1000);
    activeRecorder.ondataavailable = handleDataAvailable;
    setRecordingState("recording");
    console.log("开始录音了");
  };

  const pauseRecording = () => {
    recorder?.pause();
    setRecordingState("paused");
  };

  const resumeRecording = () => {
    recorder?.resume();
    setRecordingState("recording");
  };

  const download = ({ id, form }: { id: string; form: "wav" | "mp3" }) => {
    // 查找对应 ID 的录音
    const recording = recordings.find((rec) => rec.id === id);
    if (!recording) {
      console.error("Recording not found");
      return;
    }

    // 创建一个下载链接并模拟点击以下载文件
    const link = document.createElement("a");
    link.href = recording.audioUrl;
    link.download = `${recording.name || "download"}.${form}`; // 使用提供的格式作为文件后缀
    document.body.appendChild(link); // 这是必须的，因为 Firefox 要求链接在文档中
    link.click();
    document.body.removeChild(link); // 下载后移除元素
  };
  return {
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    recordingState,
    recordings,
    isDeviceSupported,
    download
  };
}
