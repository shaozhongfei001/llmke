import { useEffect, useMemo, useState } from "react";
import type { ComponentProps } from "react";
import { GientechStreamReader as RawStreamReader } from "@gientech/modual/streamFilesReader";
import { getObjectKeyFromSource } from "@root/src/core/helps";
import {
  PREVIEW_STREAM_API,
  STREAM_API,
  resolvePreviewTarget
} from "@root/src/core/helps/fileAccess";

/**
 * R14-D-FIX-01（统一入口版）：`GientechStreamReader` 的包装器。
 *
 * 为什么要包一层：仓库里有 10+ 个地方各自拼 `convertedFilePath` 再配一个 `streamApiUrl`，
 * 历史写法不统一，实测会造成三类失败（2026-10-27，服务端对照见 D-JOURNEYS.md §1）：
 *   1) Office 传 `/preview/convert?key=<urlencoded>` 却投给 `/file/stream`
 *      → 服务端 assertStreamAllowed 按 `/` 切段找 `kb_xxx`，编码后找不到 → 403/30016；
 *   2) 任何带 `/minio/` 前缀的键投给 stream → 服务端不剥前缀 → 500 getInputStreamByUrl failed；
 *   3) 图片直接给对象存储地址 → R13 撤匿名读后 403。
 *
 * 包装后统一规则（与 TL 定稿口径一致）：
 *   - `/preview/convert?key=…` 或 Office 类型 → 裸对象键 + `previewStream`，按 pdf 渲染
 *   - 图片 → 服务端预签名直链
 *   - 其它 → 裸对象键 + 调用方给的 stream 接口（默认 `/file/stream`）
 * 失败时显示可见原因 + 重试，不静默。
 */
type StreamReaderProps = ComponentProps<typeof RawStreamReader>;

export const GientechStreamReader = (props: StreamReaderProps) => {
  const {
    convertedFilePath = "",
    fileType,
    authorization,
    streamApiUrl,
    ...rest
  } = props;
  const [resolved, setResolved] = useState<any>(null);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  const markerKey = useMemo(() => {
    const m = /\/preview\/convert\?key=([^&]+)/.exec(String(convertedFilePath));
    return m ? decodeURIComponent(m[1]) : "";
  }, [convertedFilePath]);

  useEffect(() => {
    let cancelled = false;
    setError("");
    setResolved(null);
    const run = async () => {
      // 统一走 fileAccess 的口径（含 presign 前置校验），避免两套解析逻辑漂移
      const source = markerKey || convertedFilePath;
      const key = getObjectKeyFromSource(source);
      if (!key) {
        setResolved({
          filePath: convertedFilePath,
          streamApiUrl: streamApiUrl || STREAM_API,
          fileType
        });
        return;
      }
      const target = await resolvePreviewTarget({
        source,
        fileType,
        token: authorization || ""
      });
      if (cancelled) return;
      setResolved({
        filePath: target.filePath,
        streamApiUrl: target.streamApiUrl,
        // office/表格走 previewStream 时服务端返回的是转换后的 PDF，按 pdf 渲染
        fileType:
          target.streamApiUrl === PREVIEW_STREAM_API ? "pdf" : fileType
      });
    };
    run().catch((e: any) => {
      if (!cancelled) setError(e?.message || "打开原文失败");
    });
    return () => {
      cancelled = true;
    };
  }, [convertedFilePath, fileType, authorization, markerKey, streamApiUrl, reloadKey]);

  if (error) {
    return (
      <div style={{ padding: 16, fontSize: 13, color: "#666" }}>
        <div>加载失败：{error}</div>
        <button
          type="button"
          style={{ marginTop: 8, fontSize: 12, cursor: "pointer" }}
          onClick={() => setReloadKey(k => k + 1)}
        >
          重试
        </button>
      </div>
    );
  }
  if (!resolved) {
    return <div style={{ padding: 16, fontSize: 13, color: "#999" }}>正在打开原文…</div>;
  }
  return (
    <RawStreamReader
      {...rest}
      convertedFilePath={resolved.filePath}
      streamApiUrl={resolved.streamApiUrl}
      fileType={resolved.fileType}
      authorization={authorization}
    />
  );
};

export default GientechStreamReader;
