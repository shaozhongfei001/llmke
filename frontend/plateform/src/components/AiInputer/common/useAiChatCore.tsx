import { differenceInDays } from "date-fns";
import dayjs from "dayjs";
import { useMemo } from "react";
import { uid } from "uid";
import {
  api_createDialogue,
  api_getDialogueList,
  api_uploadAudio
} from "./services/servers";
import { removeNodes } from "@udecode/plate-common";
import { Node } from "slate";
import { PlateEditor } from "@udecode/plate-common/react";
import { IAppData, IConversation } from "../@types/sys";
import { ListItemType, SortRule } from "../@types/props";

export const useAiChatCore = ({
  inputer,
  appData,
  setAppData,
  serverInfo,
  conversationData
}: {
  inputer: React.MutableRefObject<null | PlateEditor>;
  appData: IAppData;
  setAppData: React.Dispatch<React.SetStateAction<IAppData>>;
  conversationData: IConversation;
  serverInfo: { token: string; baseURL: string; mockMode?: boolean };
}) => {
  const setChatList = (data: any, serverInfo: any, cb?: () => void) => {
    if (serverInfo?.baseURL) {
      api_getDialogueList({
        data: data ? data : { page: 1, pageSize: 20 },
        config: {
          url: serverInfo.baseURL,
          token: serverInfo.token,
          enableMock: serverInfo.mockMode
        }
      })
        .then((response) => {
          setAppData((pre) => {
            return {
              ...pre,
              conversations_list:
                data.page === 1
                  ? [...response.records]
                  : [...(pre?.conversations_list || []), ...response.records],
              conversations_list_pagging: {
                pageNo: data.page,
                totalPages: response.pages
              }
            };
          });
        })
        .finally(() => {
          cb && cb();
        });
    }
  };

  const conversationsMap = useMemo(() => {
    if (!appData?.conversations_list?.length) return new Map();
    const map = new Map();
    appData.conversations_list.forEach((item) => {
      map.set(item.sessionId, item);
    });
    return map;
  }, [appData]);

  const currentAssist = useMemo(() => {
    if (appData.assist_list && appData.assist_list.length) {
      return appData.assist_list.find(
        (item) => item.value === conversationData.assist_id
      );
    }
    return null;
  }, [appData.conversations_list, appData.activedConversation]);

  const genTemTopic = () => {
    //点击
    return {
      label: `临时聊天${uid(8)}`,
      sessionId: "temperature",
      gmtModified: new Date().getTime()
    };
  };

  //根据规则进行按照时间分筏数据
  const chunkDataByTimeStamp = (
    data: ListItemType[],
    rules: SortRule[]
  ): Record<string, ListItemType[]> => {
    const now = new Date();
    const sortedList: Record<string, ListItemType[]> = {
      other: []
    };

    data.forEach((item) => {
      const itemDate = new Date(item.gmtModified);
      const daysDifference = differenceInDays(now, itemDate);
      // console.log(
      //   'Item:',
      //   item.label,
      //   'Days Difference:',
      //   daysDifference,
      //   'Item Date:',
      //   itemDate,
      //   'Now:',
      //   now
      // ); // 调试输出

      let found = false;

      for (const rule of rules) {
        if (daysDifference <= rule.dayPeriod) {
          if (!sortedList[rule.label]) {
            sortedList[rule.label] = [];
          }
          sortedList[rule.label].push(item);
          found = true;
          // console.log('Matched Rule:', rule.label); // 调试输出
          break; // 确保每个数据项只分类到一个时间段
        }
      }

      if (!found) {
        sortedList.other.push(item);
        // console.log('Placed in "other" category:', item.label); // 调试输出
      }
    });

    // console.log('Sorted List:', sortedList); // 调试输出
    return sortedList;
  };

  //换并重新按照时间戳进行排序
  const sortDataByData = (data: any[], orderBy: string = "gmtModified") => {
    // 检查数据是否为空数组
    if (!data || !data.length) {
      return "数据为空";
    }
    const processedData = data.map((item) => {
      if (!item[orderBy]) {
        return "[orderBy]字段缺失";
      }
      // 使用day.js解析时间，如果解析失败，则返回错误
      const modifiedTime = dayjs(item[orderBy]);
      if (!modifiedTime.isValid()) {
        return "[orderBy]字段格式错误";
      }

      // 将解析后的时间戳赋值给[orderBy]字段
      return {
        ...item,
        [orderBy]: modifiedTime.valueOf()
      };
    });

    // 过滤掉错误项，并按照[orderBy]字段降序排序
    const validData = processedData
      .filter((item) => typeof item === "object")
      .sort((a, b) => b[orderBy] - a[orderBy]);

    return validData;
  };

  const setActiveChat = (id: string) => {
    const { activedConversation } = appData;
    if (id === activedConversation) return true;
    setAppData((pre) => {
      if (pre.activedConversation != id) {
        return {
          ...pre,
          activedConversation: id
        };
      }
      return pre;
    });
  };

  const createCoversation = async (editor: PlateEditor | null) => {
    if (!inputer) throw new Error("编辑器未初始化");
    const data = Node.string(inputer.current as any);
    const getLabel = (content: string): string => {
      if (!content) {
        throw new Error("输入内容不能为空");
      }
      return content.length > 12 ? content.slice(0, 12) : content;
    };
    console.log(editor);
    const createDialogueResponse = await api_createDialogue({
      data: {
        label: getLabel(data),
        sessionId: uid(32),
        assist_id: conversationData.assist_id!
      },
      config: {
        url: serverInfo.baseURL,
        token: serverInfo.token,
        enableMock: serverInfo.mockMode
      }
    });
    return createDialogueResponse;
  };

  const uploadAudio = async (audioObj: any) => {
    const audioBufferToWav = (buffer: AudioBuffer): ArrayBuffer => {
      const numChannels = buffer.numberOfChannels;
      const sampleRate = buffer.sampleRate;
      const numFrames = buffer.length;

      const bytesPerSample = 2;
      const blockAlign = numChannels * bytesPerSample;
      const byteRate = sampleRate * blockAlign;

      const wavBuffer = new ArrayBuffer(44 + numFrames * blockAlign);
      const dataView = new DataView(wavBuffer);

      dataView.setUint32(0, 0x52494646);
      dataView.setUint32(4, 36 + numFrames * blockAlign, true);
      dataView.setUint32(8, 0x57415645);
      dataView.setUint32(12, 0x666d7420);
      dataView.setUint32(16, 16, true);
      dataView.setUint16(20, 1, true);
      dataView.setUint16(22, numChannels, true);
      dataView.setUint32(24, sampleRate, true);
      dataView.setUint32(28, byteRate, true);
      dataView.setUint16(32, blockAlign, true);
      dataView.setUint16(34, 8 * bytesPerSample, true);
      dataView.setUint32(36, 0x64617461);
      dataView.setUint32(40, numFrames * blockAlign, true);

      const channelData = new Array(numChannels);
      for (let i = 0; i < numChannels; i++) {
        channelData[i] = buffer.getChannelData(i);
      }

      let offset = 44;
      for (let i = 0; i < numFrames; i++) {
        for (let j = 0; j < numChannels; j++) {
          const sample = Math.max(-1, Math.min(1, channelData[j][i]));
          const int16Value = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
          dataView.setInt16(offset, int16Value, true);
          offset += bytesPerSample;
        }
      }

      return wavBuffer;
    };
    if (audioObj && audioObj.audioUrl) {
      const arrayBuffer = await fetch(audioObj.audioUrl).then((r) =>
        r.arrayBuffer()
      );
      const audioContext = new AudioContext();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      const wavBuffer = audioBufferToWav(audioBuffer);
      const blob = new Blob([wavBuffer], { type: "audio/wav" });
      const file = new File([blob], "file.wav");

      const formData = new FormData();
      formData.append("file", file);

      const audioUploadResponse = await api_uploadAudio({
        data: {
          formData
        },
        config: {
          url: serverInfo.baseURL,
          token: serverInfo.token,
          enableMock: serverInfo.mockMode
        }
      });

      return audioUploadResponse;
    }
    return {};
  };

  //清空编辑器的内容
  const clearInputer = (editor: any) => {
    editor.children.forEach((child: any) => {
      removeNodes(editor, { at: [0] });
    });
    editor.children = [
      {
        type: "p",
        children: [{ text: "" }]
      }
    ];
  };
  const freshAndSetChatToCurrent = (inData: {
    sessionId: string;
    [key: string]: any;
  }) => {};

  return {
    genTemTopic,
    chunkDataByTimeStamp,
    sortDataByData,
    clearInputer,
    freshAndSetChatToCurrent,
    setActiveChat,
    setChatList,
    createCoversation,
    currentAssist,
    uploadAudio,
    conversationsMap
  };
};
