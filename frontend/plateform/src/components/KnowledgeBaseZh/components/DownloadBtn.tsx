import { Button } from "antd";
import "@/assets/styles/knowledgebase.less";
import { downloadByStream } from "@root/src/core/helps";

interface IEmpty {
  disabled: boolean;
  file: {
    filePath: string;
    fileName: string;
  };
  text?: string;
}

const DownloadBtn = (props: IEmpty) => {
  const { disabled, file, text } = props;
  const { filePath, fileName } = file;
  return (
    <Button
      type="link"
      title="文件下载"
      disabled={!disabled}
      size={"small"}
      onClick={() => downloadByStream({ filePath, fileName })}
    >
      {text || "下载"}
    </Button>
  );
};

export default DownloadBtn;
