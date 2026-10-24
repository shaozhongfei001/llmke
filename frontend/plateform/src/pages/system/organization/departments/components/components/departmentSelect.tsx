import { CaretDownOutlined, SearchOutlined } from "@ant-design/icons";
import { ELEMENT_TYPE } from "@root/src/const/permission";
import IconHeader from "@root/src/pages/Components/IconHeader";
import { Input, Tree } from "antd";

const DepartmentSelect = ({
  searchInput,
  onSearchChange,
  treeData,
  checkedKey,
  onTreeCheck,
  mode
}: {
  searchInput: string;
  onSearchChange: (arg: any) => void;
  treeData: any[];
  checkedKey: any;
  onTreeCheck: (arg: any, e: any) => void;
  mode?: "multiple" | "single";
}) => {
  return (
    <div className="box-border border-solid border-[1px] border-[#D9D9D9] h-full overflow-y-auto rounded-[4px] p-[16px]">
      <Input
        placeholder="搜索部门名"
        suffix={<SearchOutlined onClick={() => {}} />}
        value={searchInput}
        onChange={(e: any) => onSearchChange(e)}
        className="mb-[10px]"
      />
      <Tree
        treeData={treeData || []}
        blockNode
        checkable
        checkStrictly
        scrollWidth={100}
        className="custom-tree"
        defaultExpandAll
        titleRender={(nodeData: any) => {
          const storey = nodeData.layer;
          let w = 380 - storey * 24;
          w = w < 30 ? 30 : w;
          return (
            <div className="flex items-center">
              <IconHeader
                type={ELEMENT_TYPE.DEPARTMENT}
                className="mr-[8px]"
                size={28}
                text={""}
                rounded="rounded-full"
                bg={` linear-gradient(
              99.9deg,
              #2b69ff -4.18%,
              #8f91ff 106.52%
            )`}
              />
              <div
                style={{ width: `${w}px` }}
                className="text-ellipsis line-clamp-1 block"
              >
                {nodeData.name}
              </div>
            </div>
          );
        }}
        fieldNames={{ key: "id" }}
        switcherIcon={
          <CaretDownOutlined className="text-[#888888] mr-[-5px]" />
        }
        checkedKeys={mode === "multiple" ? checkedKey : [checkedKey]}
        onCheck={(checkedKeys: any, e: any) => {
          onTreeCheck(checkedKeys, e);
        }}
      />
    </div>
  );
};

export default DepartmentSelect;
