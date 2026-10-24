import { ReactNode } from "react";
import { Flex } from "antd";
import { CloseOutlined } from "@ant-design/icons";
import Right from "@/components/AiEditor/assets/img/right.png";
import "./style.less";
interface Item {
  key: number;
  value: string;
}
interface Iprops {
  list: Item[];
  curItemKey: number;
  renderFooter: any;
  children?: ReactNode;
  subTitle?: string;
  onClose: () => void;
}

const ProcessDrawer = (props: Iprops) => {
  const { list, curItemKey, renderFooter, subTitle, onClose } = props;
  return (
    <div className="mx-5 bg-transparent">
      <div className="h-8 my-3 flex justify-between leading-8">
        <span className="text-gray-2a font-bold">{subTitle}</span>
        <CloseOutlined className="mr-3" onClick={onClose} />
      </div>
      <div className="bg-white rounded-lg overflow-hidden">
        <div className="flex justify-between px-5 py-3 border-0 border-b border-solid border-b-[#eee] h-14 leading-8">
          <Flex align="start">
            {list.map((item, index) => (
              <Flex align="center" key={`crumbs-step-${item.key}`}>
                <span
                  className="w-6 h-6 inline-block leading-6 text-center rounded-full mr-3 text-xs select-none"
                  style={{
                    background:
                      curItemKey > index
                        ? "linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%) "
                        : "#f2f2f2",
                    color: curItemKey > index ? "white" : "#888"
                  }}
                >
                  {index + 1}
                </span>
                <span
                  className="mr-8 select-none"
                  style={{
                    fontWeight: item.key === curItemKey ? "700" : "400"
                  }}
                >
                  {item.value}
                </span>
                {item.key < list.length && (
                  <img src={Right} width={16} height={16} className="mr-8" />
                )}
              </Flex>
            ))}
          </Flex>
          <div>{renderFooter}</div>
        </div>
        <div className="pl-5">
          <div className="h-[calc(100vh-200px)] overflow-y-auto overflow-x-hidden">
            {props.children}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProcessDrawer;
