const Empty = () => {
  return (
    <div className="chat-displater w-full  mx-auto ">
      <div className="flex h-full items-center gap-y-3 w-full pb-[60px] pt-[30px] px-[20px] flex-col overflow-y-hidden">
        <div className="mt-[110px] flex flex-col items-center">
          <div className="text-[28px] font-bold text-[#2a2a2a]">
            Hi，欢迎使用鲸问大模型知识库问答系统~
          </div>
          {/* <div className="mt-[12px] text-[14px] text-[#888888]">
            模型信息：
          </div> */}
          {/* <img src={Main} width={82} height={100} className="mt-[60px]" /> */}
          <div className="mt-[12px]">开始聊天吧</div>
        </div>
      </div>
    </div>
  );
};
export default Empty;
