import { differenceInDays } from 'date-fns';
import dayjs from 'dayjs';

import { useMemo, useRef, useState } from 'react';
import { uid } from 'uid';
import { useStateStore } from '../useStateStore';
import { QAChatItem, StatusType } from '../../@types/props';

import { useDataTransformer } from '../useDataTransformer';
import { api_uploadAudio } from '../services/servers';
import { removeNodes, setNodes, Value } from '@udecode/plate-common';
import { IConversation } from '../../@types/sys';

export const useAiCompareCore = () => {
  const { inputer, appData, setAppData, serverInfo } = useStateStore();
  const { parseHistoryData, stremDataToQAdata, createDialog_to_conversationData } =
    useDataTransformer();
  // const controllerRef = useRef(new AbortController());
  const [currentChat, setCurrentChat] = useState<QAChatItem[]>();
  const [streamingRes, setStreamingRes] = useState<QAChatItem>();

  const isRetriveSideOpen = useMemo(() => {
    if (appData.retriever_info && appData.retriever_info['id']) {
      return true;
    } else {
      return false;
    }
  }, [appData.retriever_info]);

  const genTemTopic = () => {
    //点击
    return {
      label: `临时聊天${uid(8)}`,
      sessionId: 'temperature',
      gmtModified: new Date().getTime(),
    };
  };

  //换并重新按照时间戳进行排序
  const sortDataByData = (data: any[], orderBy: string = 'gmtModified') => {
    // 检查数据是否为空数组
    if (!data || !data.length) {
      return '数据为空';
    }
    const processedData = data.map((item) => {
      if (!item[orderBy]) {
        return '[orderBy]字段缺失';
      }
      // 使用day.js解析时间，如果解析失败，则返回错误
      const modifiedTime = dayjs(item[orderBy]);
      if (!modifiedTime.isValid()) {
        return '[orderBy]字段格式错误';
      }

      // 将解析后的时间戳赋值给[orderBy]字段
      return {
        ...item,
        [orderBy]: modifiedTime.valueOf(),
      };
    });

    // 过滤掉错误项，并按照[orderBy]字段降序排序
    const validData = processedData
      .filter((item) => typeof item === 'object')
      .sort((a, b) => b[orderBy] - a[orderBy]);

    return validData;
  };

  // const createCoversation = async () => {

  //   const createDialogueResponse = await api_createDialogue({

  //   });
  //   return createDialogueResponse;
  // };

  const uploadAudio = async (audioObj) => {
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
      let arrayBuffer = await fetch(audioObj.audioUrl).then((r) => r.arrayBuffer());
      const audioContext = new AudioContext();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      const wavBuffer = audioBufferToWav(audioBuffer);
      const blob = new Blob([wavBuffer], { type: 'audio/wav' });
      let file = new File([blob], 'file.wav');

      let formData = new FormData();
      formData.append('file', file);

      const audioUploadResponse = await api_uploadAudio({
        data: {
          formData,
        },
        config: serverInfo,
      });

      return audioUploadResponse;
    }
    return {};
  };

  // 添加对比聊天实例
  const addComparisonChat = () => {
    const newConversation: IConversation = {
      id: uid(32),
      name: 'untitled',
      status: StatusType.Pending,
      modify_timeStamp: new Date().getTime(),
      sseController: new AbortController(),
    };

    setAppData({
      ...appData,
      conversations: [...(appData.conversations || []), newConversation],
    });
  };
  // 根据id删除对比聊天实例
  const removeComparisonChat = (conversationId: string) => {
    setAppData({
      ...appData,
      conversations: (appData.conversations || []).filter(
        (conversation) => conversation.id !== conversationId
      ),
    });
  };

  // 根据id更新对比聊天实例
  const updateComparisonChat = (updatedConversation: IConversation) => {
    setAppData({
      ...appData,
      conversations: (appData.conversations || []).map((conversation) =>
        conversation.id === updatedConversation.id ? updatedConversation : conversation
      ),
    });
  };

  // 根据id获取对比聊天实例
  const getComparisonChatById = (conversationId: string): IConversation | undefined => {
    return (appData.conversations || []).find((conversation) => conversation.id === conversationId);
  };

  //清空编辑器的内容
  const clearInputer = (editor) => {
    editor.children.forEach((child) => {
      removeNodes(editor, { at: [0] });
    });
    editor.children = [
      {
        type: 'p',
        children: [{ text: '' }],
      },
    ];
  };
  const freshAndSetChatToCurrent = (inData: { sessionId: string; [key: string]: any }) => {};
  return {
    genTemTopic,
    clearInputer,
    freshAndSetChatToCurrent,
    isRetriveSideOpen,
    // createCoversation,
    currentChat,
    streamingRes,
    uploadAudio,
    addComparisonChat,
    removeComparisonChat,
    updateComparisonChat,
    getComparisonChatById,
  };
};
