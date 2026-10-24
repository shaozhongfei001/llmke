import { dealMinioUrl } from "@root/src/core/helps";
import { message, Skeleton } from "antd";
import axios from "axios";
import { useEffect } from "react";

const findSubstringToNewline = (str: string, substring: string) => {
  const startIndex = str.indexOf(substring); // 找到子字符串的起始位置
  if (startIndex === -1) {
    // 如果没有找到子字符串，返回 -1 或其他表示未找到的值
    return -1;
  } else {
    return { startIndex, endIndex: startIndex + substring.length };
  }

  // // 从子字符串的起始位置开始查找换行符
  // let endIndex = startIndex;
  // while (endIndex < str.length && str[endIndex] !== '\n') {
  //   endIndex++;
  // }

  // // 如果找到了换行符，返回起始和结束下标；否则返回起始下标和字符串长度（表示没有换行符）
  // if (endIndex < str.length) {
  //   return { startIndex, endIndex };
  // } else {
  //   // 如果没有找到换行符，可以返回一个特殊值或仅返回起始下标（根据需要）
  //   // 这里我们返回起始下标和字符串长度，表示范围到字符串末尾
  //   return { startIndex, endIndex: str.length };
  // }
};

const findIndexByParagraphNo = (totalText: string, paragraphNo: number) => {
  if (!totalText || paragraphNo < 0) {
    return -1;
  }
  const strArr = totalText.split("\n");
  if (!strArr[paragraphNo]) return -1;
  const startIndex = totalText.indexOf(strArr[paragraphNo]);
  return {
    startIndex: startIndex,
    endIndex: startIndex + strArr[paragraphNo].length
  };
};

export const DrawerContent = ({
  content,
  open,
  fileContent,
  setFileContent
}: any) => {
  const getData = async () => {
    try {
      let url = content.file_source;
      if (window.location.hostname !== "localhost") {
        url = dealMinioUrl(content.file_source);
      }
      const response: any = await axios.get(url, {});
      if (!response || !response?.data) return;
      const origin_file_str = response.data;
      if (!content) return;

      setFileContent(origin_file_str);
    } catch (e) {
      message.error("获取引用文件失败，请联系管理员。");
      console.log("fetchFullDoc error", e);
    }
  };

  useEffect(() => {
    if (fileContent) {
      setTimeout(() => {
        const box: any = document.querySelector("#show-file-content");
        const totalText = box?.innerHTML || "";
        // const res = findSubstringToNewline(totalText, content.matchText);
        const res = findIndexByParagraphNo(totalText, content.paragraphNo);
        if (res !== -1) {
          const htmlString =
            totalText.substring(0, res.startIndex) +
            `<span id="ai-editor-hight-line" style="background:rgb(225, 235, 255);">${totalText.substring(res.startIndex, res.endIndex)}</span>` +
            totalText.substring(res.endIndex, totalText.length);
          box.innerHTML = htmlString;
          setTimeout(() => {
            const hightLineDom = document.querySelector(
              "#ai-editor-hight-line"
            );
            if (hightLineDom) {
              hightLineDom.scrollIntoView({
                behavior: "smooth",
                block: "start"
              });
            }
          }, 100);
        }
      }, 50);
    }
  }, [fileContent]);

  useEffect(() => {
    if (!open) {
      setFileContent(null);
    } else {
      getData();
    }
  }, [open]);

  return (
    <>
      <span style={{ marginBottom: "10px", display: "flex" }}>
        <label
          style={{
            fontFamily: "Source Han Sans CN",
            fontSize: "12px",
            fontWeight: "500",
            color: "#000"
          }}
        >
          引用来源：
        </label>
        <label
          style={{
            color: "#014DDF",
            fontFamily: "Source Han Sans CN",
            fontSize: "12px",
            fontWeight: "500"
          }}
        >
          {content?.title}
        </label>
      </span>
      <div
        style={{
          fontFamily: "Source Han Sans CN",
          fontSize: "12px",
          wordBreak: "break-word",
          whiteSpace: "pre-wrap"
        }}
      >
        <label
          style={{
            fontWeight: "500",
            color: "#000"
          }}
        >
          溯源内容：
        </label>
        {/* <div dangerouslySetInnerHTML={{ __html: fileContent }} /> */}
        <div id="show-file-content">{fileContent}</div>
        <Skeleton
          active
          className={`${!fileContent ? "" : "hidden"}`}
        ></Skeleton>
      </div>
    </>
  );
};
