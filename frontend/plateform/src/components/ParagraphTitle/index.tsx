const ParagraphTitle = ({ title }: { title: string }) => {
  return (
    <div className="flex items-center">
      <div className="w-1 h-3 bg-gradient-to-br from-[#A98D62] to-[#D8BD89] rounded-sm mr-2 "></div>
      <div className="font-bold">{title}</div>
    </div>
  );
};

export default ParagraphTitle;
