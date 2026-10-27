import { getObjectKeyFromSource, isOfficePreviewType } from "./index";

/**
 * R14-D-FIX-01：打开原文的统一出口。
 *
 * 背景（实测，2026-10-27）：
 * - R13 撤销 MinIO 匿名读后，任何 `/minio/<对象键>` 直链一律 403；
 * - 更关键的是 stream/previewStream 两个接口**不接受 `/minio/` 前缀**：
 *   `convertedFilePath=/minio/r12-rag/kb_9/x.pdf/V0/x.pdf` → 500 `getInputStreamByUrl failed`
 *   `convertedFilePath=r12-rag/kb_9/x.pdf/V0/x.pdf`   → 200 正常字节流；
 * - Office 若传 `/preview/convert?key=...`（键被 URL 编码进 query）→ 403/30016，
 *   因为服务端 assertStreamAllowed 是按 `/` 切段找 `kb_xxx`，编码后找不到；
 *   传裸对象键 → 200 转换后 PDF 流。
 *
 * 结论：凡是"取流"的入口，一律传**裸对象键**；需要浏览器直接渲染的（图片）走服务端
 * 短时效预签名地址，绝不把对象存储地址直接暴露给浏览器。
 */
export const STREAM_API = "/proxy/index/knowledgeBase/file/stream";
export const PREVIEW_STREAM_API = "/proxy/index/knowledgeBase/file/previewStream";
export const PRESIGN_API = "/proxy/index/knowledgeBase/file/presign";

const IMAGE_TYPES = ["png", "jpg", "jpeg", "gif", "bmp", "webp"];

/**
 * 表格类也必须经 previewStream 转 PDF：
 * xlsx 原始字节投给渲染器只会得到「无法解析为表格」（实测 2026-10-27），
 * 而 previewStream 对 xlsx 实测返回 200 + 转换后 PDF（%PDF-1.7）。
 * 注意 xlsx/xls/csv 在 `fileViewTypes` 里是被注释掉的，所以不能只靠那个列表判断。
 */
const SHEET_TYPES = ["xlsx", "xls", "csv"];

export const isSheetType = (type?: string) =>
  !!type && SHEET_TYPES.includes(type.toLowerCase());

export const isImageType = (type?: string) =>
  !!type && IMAGE_TYPES.includes(type.toLowerCase());

/** 服务端签发短时效预签名地址（失败抛出可展示的原因，不静默） */
export const getPresignedObjectUrl = async (
  source: string,
  token: string
): Promise<string> => {
  const key = getObjectKeyFromSource(source);
  if (!key) throw new Error("缺少原文对象键，无法签发地址");
  const res = await fetch(`${PRESIGN_API}?key=${encodeURIComponent(key)}`, {
    method: "GET",
    headers: { Authorization: token || "" }
  });
  if (!res.ok) {
    // R14-D-FIX-05：按服务端口径给出**可区分**的原因，不统一压成"打不开"
    // 30016/401/403 -> 无权限；404/10001 -> 原文不存在或已删除；5xx -> 原文服务异常
    let serverMsg = "";
    let code = "";
    try {
      const body: any = await res.json();
      serverMsg = body?.errorMsg || "";
      code = String(body?.errorCode || "");
    } catch {
      // 非 JSON 响应保留 HTTP 状态
    }
    let msg: string;
    if (res.status === 404 || code === "10001") {
      msg = `原文不存在或已删除${serverMsg ? `（${serverMsg}）` : ""}`;
    } else if (res.status === 401 || res.status === 403 || code === "30016" || code === "30022") {
      msg = `无权访问该原文${serverMsg ? `（${serverMsg}）` : ""}`;
    } else if (res.status >= 500) {
      msg = `原文服务异常（HTTP ${res.status}）${serverMsg ? `：${serverMsg}` : ""}`;
    } else {
      msg = `原文地址签发失败（HTTP ${res.status}）${serverMsg ? `：${serverMsg}` : ""}`;
    }
    throw new Error(msg);
  }
  const body: any = await res.json();
  const url = body?.url || body?.data?.url;
  if (!url) throw new Error("原文地址签发失败：服务端未返回地址");
  return url;
};

/**
 * 解析"打开原文"的目标（filePath 会作为 convertedFilePath 发给对应 stream 接口）：
 * - Office(docx/pptx/…) → 裸对象键 + previewStream（服务端转 PDF 后取流）
 * - 图片 → 预签名直链（浏览器直接渲染）
 * - 其它（pdf/txt/md）→ 裸对象键 + stream
 */
export const resolvePreviewTarget = async ({
  source,
  fileType,
  token
}: {
  source: string;
  fileType: string;
  token: string;
}): Promise<{ filePath: string; streamApiUrl: string }> => {
  const key = getObjectKeyFromSource(source);
  if (!key) throw new Error("缺少原文对象键，无法打开原文");
  // R14-D-FIX-04：**所有类型**先做一次 presign 前置校验。
  // 理由：presign 的错误口径可区分（403/30016 越权、404/10002 文件不存在、
  // 5xx 存储异常），而 stream / previewStream 的失败在第三方渲染器里只会被
  // 压成「PDF请求失败: 4xx」，用户与验收都无法判断是权限还是文件没了。
  // 图片直接复用该预签名地址（浏览器直取）；其余类型丢弃 URL，仍走鉴权取流。
  const presigned = await getPresignedObjectUrl(source, token);
  if (isImageType(fileType)) {
    return { filePath: presigned, streamApiUrl: STREAM_API };
  }
  if (isOfficePreviewType(fileType) || isSheetType(fileType)) {
    return { filePath: key, streamApiUrl: PREVIEW_STREAM_API };
  }
  return { filePath: key, streamApiUrl: STREAM_API };
};
