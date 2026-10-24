import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';

interface VoiceInputProps {
  onResult: (text: string) => void;
  onError: (error: string) => void;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: 'no-speech' | 'audio-capture' | 'not-allowed' | string;
}

interface SpeechRecognitionEvent extends Event {
  results: {
    item(index: number): {
      item(index: number): {
        transcript: string;
      };
    };
    length: number;
  };
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onstart: () => void;
  onend: () => void;
  onerror: (event: SpeechRecognitionErrorEvent) => void;
  onresult: (event: SpeechRecognitionEvent) => void;
  abort: () => void;
  start: () => void;
  stop: () => void;
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognition;
}

// 为了 TypeScript 支持
declare global {
  interface Window {
    SpeechRecognition: SpeechRecognitionConstructor;
    webkitSpeechRecognition: SpeechRecognitionConstructor;
  }
}

export function VoiceInput({ onResult, onError }: VoiceInputProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [shouldRestart, setShouldRestart] = useState(false);
  const silenceTimerRef = useRef<number | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const isComponentMounted = useRef(true);
  const SILENCE_TIMEOUT = 3000; // 3秒无语音自动停止

  // 清除计时器
  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      window.clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  // 重置无语音计时器
  const resetSilenceTimer = useCallback(() => {
    if (!isComponentMounted.current) return;
    
    clearSilenceTimer();
    
    if (!recognitionRef.current) return;
    
    silenceTimerRef.current = window.setTimeout(() => {
      if (!isComponentMounted.current) return;
      setShouldRestart(false);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (error) {
          console.error('停止录音失败:', error);
        }
      }
    }, SILENCE_TIMEOUT);
  }, [clearSilenceTimer]);

  // 停止录音
  const stopRecording = useCallback(() => {
    setShouldRestart(false);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (error) {
        console.error('停止录音失败:', error);
      }
    }
    clearSilenceTimer();
    setIsRecording(false);
  }, [clearSilenceTimer]);

  // 初始化语音识别
  useEffect(() => {
    isComponentMounted.current = true;

    // 如果已经初始化过，就不再重新初始化
    if (recognitionRef.current) {
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      console.warn('浏览器不支持语音识别功能');
      onError('您的浏览器不支持语音识别功能');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'zh-CN';

      // 绑定事件处理器
      recognition.onstart = () => {
        if (!isComponentMounted.current) return;
        console.log('语音识别开始');
        setIsRecording(true);
        resetSilenceTimer();
      };

      recognition.onend = () => {
        if (!isComponentMounted.current) return;
        console.log('语音识别结束', { shouldRestart });
        if (shouldRestart) {
          try {
            recognition.start();
          } catch (error) {
            console.error('重新启动语音识别失败:', error);
            stopRecording();
            if (error instanceof Error) {
              onError(error.message);
            }
          }
        } else {
          setIsRecording(false);
          clearSilenceTimer();
        }
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        if (!isComponentMounted.current) return;
        console.log('收到语音识别结果');
        resetSilenceTimer();
        
        const results = Array.from({ length: event.results.length }, (_, i) => 
          event.results.item(i).item(0).transcript
        );
        const result = results.join('');
        // console.log('识别结果:', result);
        onResult(result);
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        if (!isComponentMounted.current) return;
        console.error('语音识别错误:', event.error);
        
        // 忽略 aborted 错误，因为这通常是由于手动停止导致的
        if (event.error === 'aborted') {
          return;
        }
        
        if (event.error !== 'no-speech') {
          if (event.error === 'audio-capture') {
            onError('无法访问麦克风，请检查权限设置');
          } else if (event.error === 'not-allowed') {
            onError('麦克风权限被拒绝');
          } else {
            onError(`语音识别出错: ${event.error}`);
          }
          stopRecording();
        } else {
          resetSilenceTimer();
        }
      };

      recognitionRef.current = recognition;
      // console.log('语音识别初始化成功');
    } catch (error) {
      console.error('初始化语音识别失败:', error);
      onError('初始化语音识别失败');
    }

    return () => {
      isComponentMounted.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (error) {
          console.error('清理语音识别失败:', error);
        }
        recognitionRef.current = null;
      }
      clearSilenceTimer();
    };
  }, [onResult, onError, resetSilenceTimer, clearSilenceTimer, stopRecording]);

  const toggleRecording = useCallback(() => {
    console.log('切换录音状态', { isRecording, recognition: !!recognitionRef.current });
    
    if (!recognitionRef.current) {
      console.error('语音识别未初始化');
      onError('语音识别未初始化');
      return;
    }

    if (isRecording) {
      console.log('停止录音');
      stopRecording();
    } else {
      console.log('开始录音');
      setShouldRestart(true);
      try {
        recognitionRef.current.start();
      } catch (error) {
        console.error('启动语音识别失败:', error);
        stopRecording();
        if (error instanceof Error) {
          onError(error.message);
        } else {
          onError('启动语音识别失败');
        }
      }
    }
  }, [isRecording, onError, stopRecording]);

  return (
    <div 
      className={`relative w-7 h-7 flex items-center justify-center rounded-lg cursor-pointer group ${
        isRecording ? 'bg-blue-50' : ''
      }`}
      onClick={toggleRecording}
      title={isRecording ? "点击停止录音" : "点击开始录音"}
    >
      <div className={`absolute inset-0 rounded-lg transition-colors duration-200 ${
        isRecording ? 'bg-blue-100' : 'bg-black/[0.02] group-hover:bg-black/[0.04]'
      }`}></div>
      {isRecording ? (
        <>
          <Loader2 className="w-[17px] h-[17px] text-blue-500 animate-spin" />
          <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
        </>
      ) : (
        <Mic className="w-[17px] h-[17px] text-gray-600/85" />
      )}
    </div>
  );
} 