import { Button, Input } from "antd";
import IconArrowLeft from "@/assets/svg/icon-arrow-left.svg";
import { CloseOutlined } from "@ant-design/icons";
import { IChapterDetail } from "./";
const { TextArea } = Input;
interface Iprops {
  detail: IChapterDetail;
  closeViewChapter: () => void;
}

export const ChapterDetail = (props: Iprops) => {
  const { detail, closeViewChapter } = props;

  return (
    <div className="absolute top-0 right-0 left-0 bottom-0 z-50 pr-4 pt-4 bg-[#f1f5fc] overflow-y-auto text-gray-2a text-sm select-none">
      <div className="flex justify-between h-6 mb-3">
        <div className="relative pl-7">
          <img
            className="absolute left-0 cursor-pointer hover:opacity-75"
            src={IconArrowLeft}
            onClick={closeViewChapter}
          />
          <b className="pb-2 text-base">{detail.sectionTitle}</b>
        </div>
        <Button
          type="link"
          title="关闭"
          className="absolute z-50 right-3 top-3 p-0"
          icon={
            <CloseOutlined className="text-[#666] scale-x-75 scale-y-75 hover:opacity-80" />
          }
          onClick={closeViewChapter}
        ></Button>
      </div>
      <div className="mb-2">
        <b>描述</b>
      </div>
      <div className="mb-5">
        <Input
          className="!text-[#aaa] !border-[#d9d9d9] !bg-white"
          value={detail.description || ""}
          disabled
        />
      </div>
      <div className="mb-2">
        <b>内容要求</b>
      </div>
      <div className="mb-5">
        <TextArea
          className="!text-[#aaa] !border-[#d9d9d9] !bg-white"
          rows={8}
          value={detail.sectionPrompt || ""}
          style={{ resize: "none" }}
          disabled
        />
      </div>
      <div className="mb-2">
        <b>参考示例</b>
      </div>
      <div className="mb-5">
        <TextArea
          className="!text-[#aaa] !border-[#d9d9d9] !bg-white"
          rows={8}
          value={detail.sectionContentExample || ""}
          style={{ resize: "none" }}
          disabled
        />
      </div>
    </div>
  );
};

export default ChapterDetail;
