/* eslint-disable no-case-declarations */
import { ConfigProvider, Modal, message, Button } from "antd";
import { useEffect, useMemo, useState } from "react";
import {
  dealMinioUrl,
  FileModalSize,
  getFileName,
  getFilePath,
  getFileType,
  useAppPassport
} from "@root/src/core/helps";
import {
  PREVIEW_STREAM_API,
  resolvePreviewTarget
} from "@root/src/core/helps/fileAccess";
import { GientechStreamReader } from "@gientech/modual/streamFilesReader";

/**
 * R14-D-FIX-01：与问答抽屉同一出口。
 * 修复前：convertedFilePath 带 `/minio/` 前缀投给 stream（服务端不剥前缀 → 500
 * getInputStreamByUrl failed）；Office 走 `/preview/convert?key=...` 投给 previewStream
 * （键被 URL 编码，服务端按段找 kb_xxx 失败 → 403/30016）。
 * 修复后：office → 裸对象键 + previewStream；图片 → 预签名直链；其它 → 裸对象键 + stream。
 */
const FileViewCom = ({ data, showPreviewModal, setShowPreviewModal }: any) => {
  const { getToken } = useAppPassport();
  const [target, setTarget] = useState<any>(null);
  const [error, setError] = useState<string>("");
  const [reloadKey, setReloadKey] = useState(0);

  const meta = useMemo(() => {
    const token: any = getToken();
    const content = {
      file_source: data?.filePath,
      file_type: data?.file_type,
      metadata: { source: data?.filePath },
      pdfPages: data?.pdfPages
    };
    const source = data?.filePath || "";
    const rawPath = dealMinioUrl(getFilePath(content));
    return {
      token,
      source,
      fileName: getFileName(content),
      // R14-D-FIX-01：优先用“源文件名后缀”判类型。
      // getFileType(content, rawPath) 对 Office 会拿到 /preview/convert?key=… 这类路径，
      // 判定不稳（实测返回空 → 走错 stream 分支 → 500 参数非法）。
      fileType:
        (String(source).split("?")[0].split(".").pop() || "").toLowerCase() ||
        getFileType(content, rawPath),
      totalPages: data?.pdfPages || 0
    };
  }, [data]);

  useEffect(() => {
    let cancelled = false;
    if (!showPreviewModal) return;
    setError("");
    setTarget(null);
    if (!meta.source || !meta.token) {
      setError("缺少原文地址或登录态，无法打开原文");
      return;
    }
    resolvePreviewTarget({
      source: meta.source,
      fileType: meta.fileType,
      token: meta.token
    })
      .then(res => {
        if (!cancelled) setTarget(res);
      })
      .catch((e: any) => {
        if (cancelled) return;
        const msg = e?.message || "打开原文失败";
        setError(msg);
        message.error(msg);
      });
    return () => {
      cancelled = true;
    };
  }, [meta, showPreviewModal, reloadKey]);

  const modalStyles = {
    header: {
      padding: "20px 24px",
      borderBottom: "1px solid #F0F0F0",
      margin: 0
    },
    body: { padding: 0 },
    mask: {},
    footer: { padding: 0, margin: 0 },
    content: { padding: 0 }
  };

  const renderFileCom = () => {
    if (error) {
      return (
        <div className="h-full flex flex-col items-center justify-center gap-3 text-[13px] text-[#666]">
          <div>加载失败：{error}</div>
          <Button size="small" onClick={() => setReloadKey(k => k + 1)}>
            重试
          </Button>
        </div>
      );
    }
    if (!target) {
      return (
        <div className="h-full flex items-center justify-center text-[13px] text-[#999]">
          正在打开原文…
        </div>
      );
    }
    return (
      <GientechStreamReader
        key={`${target.filePath}-${reloadKey}`}
        convertedFilePath={target.filePath}
        fileName={meta.fileName}
        fileType={
          target.streamApiUrl === PREVIEW_STREAM_API ? "pdf" : meta.fileType
        }
        initialPage={1}
        totalPages={meta.totalPages}
        authorization={meta.token}
        streamApiUrl={target.streamApiUrl}
        eventsEmit={(name: string) => {
          switch (name) {
            case "viewer:close":
              setShowPreviewModal(false);
              break;
          }
        }}
        tools={{
          close: true
        }}
      />
    );
  };

  return (
    <ConfigProvider
      modal={{
        styles: modalStyles
      }}
    >
      <Modal
        destroyOnClose={true}
        footer={null}
        open={showPreviewModal}
        onCancel={() => setShowPreviewModal(false)}
        width={FileModalSize.width}
        height={FileModalSize.height}
        closable={false}
      >
        <div className="h-[600px] overflow-y-auto">{renderFileCom()}</div>
      </Modal>
    </ConfigProvider>
  );
};

export default FileViewCom;
