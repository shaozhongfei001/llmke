import { useEffect, useMemo, useState } from "react";
import { Button, message } from "antd";
import {
  dealMinioUrl,
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
 * R14-D-FIX-01：引用"打开原文"。
 * 修复前：convertedFilePath 直接取 getFilePath()，Office 文件会得到
 * "/preview/convert?key=..." 却仍投给 /file/stream，服务端在
 * assertStreamAllowed 里认不出 kb_xxx（键被 URL 编码在 query 里）→ 403，
 * 抽屉只显示"加载失败 PDF请求失败: 403"。
 * 修复后：Office 走 previewStream（已鉴权转 PDF 流），图片走服务端预签名直链，
 * 其它走鉴权 stream；任何失败都给出可见原因 + 重试，不静默。
 */
const DrawerPreview = ({
  curFileInfo,
  onClose
}: {
  curFileInfo: any;
  onClose: any;
}) => {
  const { getToken } = useAppPassport();
  const [target, setTarget] = useState<any>(null);
  const [error, setError] = useState<string>("");
  const [reloadKey, setReloadKey] = useState(0);

  const meta = useMemo(() => {
    const token: any = getToken();
    const content = {
      file_source:
        curFileInfo?.parse_url || curFileInfo?.parsedFilePath || curFileInfo?.url,
      file_type: curFileInfo?.file_type,
      metadata: {
        source:
          curFileInfo?.metadata?.source || curFileInfo?.filePath || curFileInfo?.url || ""
      },
      pdfPages: curFileInfo?.pdfPages
    };
    const source = content.metadata.source || content.file_source || "";
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
      totalPages: content.pdfPages || 0
    };
  }, [curFileInfo]);

  useEffect(() => {
    let cancelled = false;
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
  }, [meta, reloadKey]);

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
    <div id="pdfBox" className="h-full overflow-y-auto">
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
        eventsEmit={(type: string) => {
          switch (type) {
            case "viewer:close":
              onClose();
              break;
          }
        }}
        tools={{
          close: true
        }}
      />
    </div>
  );
};

export default DrawerPreview;
