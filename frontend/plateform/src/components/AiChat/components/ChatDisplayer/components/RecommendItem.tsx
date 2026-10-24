import { RightOutlined } from "@ant-design/icons";

const RecommendItem = ({ data, handleEvent }: any) => {
  return (
    <div
      onClick={() => handleEvent && handleEvent(data)}
      style={{ width: "fit-content" }}
      className="mr-[20px] h-min-[40px] py-[8px] bg-white border-solid border-[1px] border-[#D9D9D9] hover:border-primary-color rounded-[4px] flex items-center text-text-color1 text-[14px] px-[16px] my-[8px] cursor-pointer hover:text-primary-color"
    >
      <div className="break-words">{data}</div>
      <RightOutlined className="shrink-0 ml-[12px]" />
    </div>
  );
};

export default RecommendItem;
