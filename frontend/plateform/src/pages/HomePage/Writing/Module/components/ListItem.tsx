interface Iprops {
  title: string;
  path?: string;
  clickListItem: () => void;
}
const ListItem = ({ title, path, clickListItem }: Iprops) => {
  return (
    <div
      className={`h-[66px] hover:bg-[#F1F5FF] bg-[#FAFAFA] mb-[6px] py-[11px] px-[8px] cursor-pointer`}
      onClick={clickListItem}
    >
      <div className="font-bold">{title}</div>
      <div
        title={path}
        className="text-[#888888] text-[12px] mt-[4px] break-words text-ellipsis  line-clamp-1"
      >
        {path || "-"}
      </div>
    </div>
  );
};

export default ListItem;
