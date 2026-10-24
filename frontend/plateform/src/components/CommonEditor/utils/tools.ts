import { getMarkExcludeType } from "@root/src/core/helps";
import { modelRegex } from "../constant";
import { IReference } from "./props";

const sortAndDeduplicateByMark = (array: any) => {
  const map = new Map();

  array.forEach((item: any) => {
    const mark = parseInt(item.mark, 10);
    if (!map.has(mark)) {
      map.set(mark, item);
    }
  });

  const uniqueArray = Array.from(map.values());
  uniqueArray.sort((a, b) => {
    return parseInt(a.mark, 10) - parseInt(b.mark, 10);
  });

  return uniqueArray;
};

export const getA = (htmlString: string) => {
  if (!htmlString) return [];
  const matches = [...htmlString.matchAll(modelRegex)];
  const result = matches.map((match) => {
    const id = match[1];
    let imageUrl: any = match[2];
    let mark = match[3];
    mark && (mark = mark.replace("[", "").replace("]", ""));
    imageUrl && (imageUrl = imageUrl.split(";"));
    return { id, mark, imageUrl };
  });
  const duplicateRemoval: any[] = [];
  return result
    .filter(({ id }) => {
      const res = duplicateRemoval.includes(id);
      duplicateRemoval.push(id);
      return !res;
    })
    .map((item, index) => {
      return {
        id: item.id,
        mark: index + 1 + "",
        imageUrl: item.imageUrl
      };
    });
};

export const getA0 = (htmlString: string) => {
  if (!htmlString) return [];
  const matches = [...htmlString.matchAll(modelRegex)];
  const result = matches.map((match) => {
    const id = match[1];
    let imageUrl: any = match[2];
    let fromType = match[3];
    fromType && (fromType = fromType.replace("[", "").replace("]", ""));
    imageUrl && (imageUrl = imageUrl.split(";"));
    return { id, fromType, imageUrl };
  });
  const duplicateRemoval: any[] = [];
  return result
    .filter(({ id, fromType }) => {
      const res = duplicateRemoval.includes(id);
      duplicateRemoval.push(id);
      return !res && fromType === "0";
    })
    .map((item, index) => {
      return {
        id: item.id,
        mark: index + 1 + "",
        imageUrl: item.imageUrl
      };
    });
};

export const getA1 = (htmlString: string) => {
  if (!htmlString) return [];
  const matches = [...htmlString.matchAll(modelRegex)];
  const result = matches.map((match) => {
    const id = match[1];
    let imageUrl: any = match[2];
    let fromType = match[3];
    fromType && (fromType = fromType.replace("[", "").replace("]", ""));
    imageUrl && (imageUrl = imageUrl.split(";"));
    return { id, fromType, imageUrl };
  });
  const duplicateRemoval: any[] = [];
  return result
    .filter(({ id, fromType }) => {
      const res = duplicateRemoval.includes(id);
      duplicateRemoval.push(id);
      return !res && fromType === "1";
    })
    .map((item, index) => {
      return {
        id: item.id,
        mark: index + 1 + "",
        imageUrl: item.imageUrl
      };
    });
};

//对后端数据进行结构重整
export const reference_data_transformData = (
  data: any[],
  rawAnswer: string,
  llmType?: number
): IReference[] => {
  if (!Array.isArray(data)) {
    return [];
  }
  const result: IReference[] = [];
  const seenIds = new Map<string, boolean>(); // 用于存储已处理的 ID
  const referenceMark = llmType === 2 ? [] : getA(rawAnswer);
  const referenceMarkId = referenceMark.map((item) => item.id);
  const pic_url_list = referenceMark.reduce((pre, cur: any) => {
    return pre.concat(cur.imageUrl || []);
  }, []);
  (data || []).forEach((item) => {
    if (
      item?.metadata?.source &&
      (llmType === 2 || referenceMarkId.includes(item.order_num))
    ) {
      const id = item.id || item.order_num || "Unknown ID";
      // 解析 source 字段
      const sourceParts = item.metadata.source.split("/");
      const fileName = sourceParts[sourceParts.length - 1] || "";
      const fileParts = fileName.split(".");
      const label = fileParts.slice(0, -1).join(".") || "Unknown Label";
      const file_type = fileParts[fileParts.length - 1] || "Unknown Type";
      // 检查并处理 search_type 和 page_content
      const search_type =
        Array.isArray(item.search_type) && item.search_type.length > 0
          ? item.search_type[0]
          : "Unknown Search Type";
      const page_content = item.page_content || "No Content Available";
      const type = item.type || "Unknown Type";
      // 构建 IReference 对象
      const reference: IReference = {
        id,
        title: label,
        file_name: fileName,
        file_type: file_type,
        file_source: getMarkExcludeType(file_type)
          ? `http://10.15.12.13:9000/${item.metadata.source}`
          : item.parsedFilePath,
        metadata: item.metadata,
        pdfPages: item.pdfPages,
        contents: referenceMark
          .filter((r) => r.id === item.order_num)
          .map((p) => {
            return {
              metadata: item.metadata,
              search_type: search_type,
              content: page_content,
              type: type,
              ...p
            };
          })
      };

      if (seenIds.has(item.metadata.source)) {
        const referenceFile = result.find((file) => {
          return file.metadata.source === item.metadata.source;
        });
        if (referenceFile?.contents) {
          referenceFile.contents.push(...reference.contents);
          referenceFile.contents = sortAndDeduplicateByMark(
            referenceFile.contents
          );
        }
      } else {
        result.push(reference);
        seenIds.set(item.metadata.source, true);
      }
    }
  });
  let n = 1;
  result.forEach((item) => {
    item.contents.forEach((c: any) => {
      c.mark = n++ + "";
    });
  });
  if (result.length) {
    result[0].pic_url_list = pic_url_list;
  }
  return result;
};
