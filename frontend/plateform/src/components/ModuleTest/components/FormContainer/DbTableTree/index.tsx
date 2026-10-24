import { Empty, Tree } from "antd";

function DbTableTree({ tree = [] }: any) {
  return (
    <div className="w-full h-full">
      {tree.length ? (
        <Tree
          className="w-full h-full"
          treeData={tree}
          fieldNames={{
            title: "name",
            children: "tables"
          }}
          showIcon={true}
        />
      ) : (
        <Empty />
      )}
    </div>
  );
}

export default DbTableTree;
