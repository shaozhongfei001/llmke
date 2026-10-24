import React, { useRef, useEffect, useState } from "react";
import {
  Mic,
  Send,
  Paperclip,
  X,
  Image as ImageIcon,
  FileText
} from "lucide-react";
import { VoiceInput } from "./VoiceInput";
import { message } from "antd";

interface FilePreview {
  file: File;
  preview?: string;
  type: "image" | "document";
}

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onUpload: (files: FileList) => void;
  onVoice: () => void;
  onClear: () => void;
  uploadedFiles: FilePreview[];
  onRemoveFile: (index: number) => void;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  onUpload,
  onVoice,
  onClear,
  uploadedFiles,
  onRemoveFile
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 自动调整文本框高度
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      // 重置高度以获取正确的 scrollHeight
      textarea.style.height = "auto";

      const lineHeight = 24; // 行高
      const paddingY = 12; // py-3 的上下内边距总和
      const minHeight = 44; // 最小高度
      const maxLines = 5; // 最大行数
      const maxHeight = maxLines * lineHeight + paddingY * 2;

      // 计算实际内容高度
      const contentHeight = textarea.scrollHeight;

      if (contentHeight <= maxHeight) {
        // 如果内容未超过5行，自然增长
        textarea.style.height = `${contentHeight}px`;
        textarea.style.overflowY = "hidden";
      } else {
        // 如果内容超过5行，固定高度并显示滚动条
        textarea.style.height = `${maxHeight}px`;
        textarea.style.overflowY = "auto";
      }
    }
  };

  // 监听输入变化
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
    adjustTextareaHeight();
  };

  // 处理文件选择
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onUpload(e.target.files);
    }
  };

  // 处理按键事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  // 处理语音识别结果
  const handleVoiceResult = (text: string) => {
    onChange(value + text);
  };

  // 处理语音识别错误
  const handleVoiceError = (error: string) => {
    message.error(error);
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [value]);

  return (
    <div className="sticky bottom-0 z-10">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-white/30 to-white/50"></div>
      <div className="absolute inset-0 backdrop-blur-[2px]"></div>
      <div className="relative max-w-[1000px] mx-auto p-4">
        {/* 文件预览区域 */}
        {/* {uploadedFiles.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {uploadedFiles.map((file, index) => (
              <div 
                key={index}
                className="relative group bg-white/80 backdrop-blur-sm rounded-lg p-2 flex items-center gap-2 border border-gray-200/50 shadow-sm"
              >
                {file.type === 'image' ? (
                  <>
                    <div className="w-8 h-8 rounded overflow-hidden">
                      <img src={file.preview} alt="" className="w-full h-full object-cover" />
                    </div>
                    <ImageIcon className="absolute top-2 left-2 w-4 h-4 text-white drop-shadow" />
                  </>
                ) : (
                  <FileText className="w-5 h-5 text-gray-600/85" />
                )}
                <span className="text-xs text-gray-700 max-w-[120px] truncate">{file.file.name}</span>
                <button 
                  onClick={() => onRemoveFile(index)}
                  className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-gray-500/90 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-600"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )} */}

        <div className="relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="我可以阅读知识库的资料并使用自然语言回答你的问题..."
            className="w-full resize-none rounded-md border border-gray-200/50 bg-white/30 pl-4 pr-[200px] py-3 focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/30 outline-none min-h-[44px] leading-[24px] shadow backdrop-blur-sm overflow-hidden"
          />

          <div className="absolute right-3 bottom-[8px] flex items-center">
            <div className="flex items-center bg-white/60 backdrop-blur-sm rounded-lg p-1.5 shadow-[0_2px_8px_-2px_rgba(0,0,0,0.08)] space-x-1.5">
              {value && (
                <div
                  className="relative w-7 h-7 flex items-center justify-center rounded-lg cursor-pointer group"
                  onClick={onClear}
                >
                  <div className="absolute inset-0 bg-black/[0.02] rounded-lg group-hover:bg-black/[0.04] transition-colors duration-200"></div>
                  <X className="w-[17px] h-[17px] text-gray-600/85" />
                </div>
              )}

              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                id="file-upload"
                onChange={handleFileSelect}
              />
              {/* <label 
                htmlFor="file-upload"
                className="relative w-7 h-7 flex items-center justify-center rounded-lg cursor-pointer group"
              >
                <div className="absolute inset-0 bg-black/[0.02] rounded-lg group-hover:bg-black/[0.04] transition-colors duration-200"></div>
                <Paperclip className="w-[17px] h-[17px] text-gray-600/85" />
              </label> */}

              {/* <VoiceInput onResult={handleVoiceResult} onError={handleVoiceError} />
               */}
              <div className="mx-0.5 h-5 w-px bg-black/[0.06]"></div>

              <div
                className="relative w-[68px] h-7 flex items-center justify-center rounded-lg cursor-pointer group overflow-hidden"
                onClick={onSend}
              >
                <div className="absolute inset-0 bg-gradient-to-br bg-[#4e6ef2] opacity-90 group-hover:opacity-100 transition-opacity duration-200 shadow-sm"></div>
                <div className="relative flex items-center gap-x-1 text-white">
                  <Send className="w-[17px] h-[17px]" />
                  <span className="ml-1 text-[12px]">发送</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-2 px-1 flex items-center justify-between text-[10px] text-gray-500/90">
          {/* <span>支持拖拽或点击上传PDF、Word、图片等文件</span>
          <span>按下 Enter 发送，Shift + Enter 换行</span> */}
        </div>
      </div>
    </div>
  );
}
