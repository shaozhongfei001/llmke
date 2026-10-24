import DataExtract from "@root/src/components/KnowledgeBaseZh/DataExtract";
import { CommonLayout } from "../../common/components/CommonLayout";
import { BackIcon } from "@root/src/components/Icon";
import { useNavigate } from "react-router-dom";

const ExtractRes = () => {
  const navigator = useNavigate();
  return (
    <CommonLayout
      widthReset={true}
      name={
        <div className="text-gray-2a text-base">
          <BackIcon
            className="cursor-pointer mr-4 hover:opacity-85"
            onClick={() => {
              navigator(-1);
            }}
          />
          <b>文件名</b>
        </div>
      }
    >
      <div className="px-[20px] pt-[5px] pb-[20px] w-full h-full box-border">
        <DataExtract />
      </div>
    </CommonLayout>
  );
};

export default ExtractRes;
