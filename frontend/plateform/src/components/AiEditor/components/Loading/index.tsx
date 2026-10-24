import { Flex } from "antd";
import loadingGif from "@/components/AiEditor/assets/img/loading.gif";
export const Loading = () => {
  return (
    <Flex align="center" justify="center" className="w-full h-full">
      <img src={loadingGif} width={64} height={64} />
    </Flex>
  );
};
