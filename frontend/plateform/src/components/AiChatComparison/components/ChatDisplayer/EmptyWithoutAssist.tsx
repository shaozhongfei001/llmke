import { Button } from 'antd';
import Main from '../../assets/main.svg';
import chooseAssiatant from '../../assets/img/chooseAssiatant.png';
const EmptyWithoutAssist = ({ handleEvent }) => {
  return (
    <div className="chat-displater w-full  mx-auto ">
      <div className="h-fullw-full pb-[60px] pt-[12px] px-[20px]overflow-y-hidden">
        <img src={chooseAssiatant} width={92} height={111} className="items-start ml-[120px]" />
        <div className="flex flex-col items-center">
          <img src={Main} width={82} height={100} className="" />
          <div className="mt-[12px] text-[14px] text-[#888888]">您还没有选择助手，快去选择吧</div>
          {/* <Button
            type="primary"
            className=" text-white mt-[20px] h-[40px] text-[14px] border-none rounded-[4px]"
            style={{ background: 'linear-gradient(#BD9CFF,#0359FF)' }}
            onClick={() => handleEvent && handleEvent('configureAssistant')}
          >
            配置个人助手
          </Button> */}
        </div>
      </div>
    </div>
  );
};
export default EmptyWithoutAssist;
