const TableHeader = () => {
  return (
    <div className="w-full bg-[#FAFAFA] h-[48px] box-border flex px-[15px] items-center text-[#2a2a2a] font-[14px] border-0 border-b-[1px] border-[#E4E8F6] border-solid">
      <div className="flex-1">项目名称</div>
      <div className="w-[250px] text-right">期初</div>
      <div className="w-[250px] text-right">期末</div>
    </div>
  );
};

export default TableHeader;
