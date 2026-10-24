import { getFileIcon } from "@/components/AiEditor/components/WritingConfig/components/SelectMaterialModal";
import { useMemo } from "react";

interface Iprops {
  item: any;
  fontSize?: string;
}

export const ItemName = ({ item, fontSize = "14px" }: Iprops) => {
  const fileType = useMemo(() => {
    if (item.refEntityType === "kb") return "kb";
    if (item.refEntityType === "folder") return "folder";
    const arr = item.refName.split(".");
    return arr[arr.length - 1];
  }, [item]);

  return (
    <div className="h-full w-full flex items-center">
      {getFileIcon(fileType)}
      <div
        title={item.refName}
        style={{
          flex: 1,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          fontSize
        }}
      >
        {item.refName}
      </div>{" "}
    </div>
  );
};

export default ItemName;
