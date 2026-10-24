import { Input, Tree } from "antd";
import { useMemo, useRef, useState } from "react";
import { getFileIcon } from "../../../../components/SelectMaterialModal";
import { PrimaryBtn } from "@root/src/pages/HomePage/Writing/common/components/PrimaryBtn";
import { SearchOutlined, UploadOutlined } from "@ant-design/icons";

type Iprops = {
  handleSelectItem: (item: any) => any;
  materialTreeData: any;
  activeFile?: any;
};

export enum elementTypes {
  KB = 1,
  FOLDER = 2,
  FILE = 3
}

const getFileSuffix = (fileName: string) => {
  const list = fileName.split(".");
  return list.length > 1 ? list[list.length - 1] : "";
};

export const getIcon = (item: any) => {
  const { elementType, fileName, name } = item;
  const _fileName = fileName || name || "";
  const type =
    _fileName && elementType === elementTypes.FILE
      ? getFileSuffix(_fileName)
      : elementType === elementTypes.FOLDER
        ? "folder"
        : "kb";
  return <span className="relative top-[2px]">{getFileIcon(type)}</span>;
};

const fixFolderStatistics = (list: any[], arr: any[] = []) => {
  list.forEach((item: any) => {
    const { children, name, elementType } = item;
    if (elementType === elementTypes.FILE) {
      arr.push(item);
    } else {
      arr.push({
        ...item,
        children: children.length ? fixFolderStatistics(children) : []
      });
    }
  });

  return arr;
};

const fixTreeData = (originData: any) => {
  let { folders, kbs, files } = originData;
  //   全文引用不区分
  const folderList = [...folders].map((i: any) => ({
    ...i,
    children: files.filter((f: any) => String(f.parentId) === String(i.refId))
  }));

  folderList.forEach((i: any) => {
    const { parentId, kbId } = i;
    if (parentId !== kbId) {
      const parentFolder = folderList.find(
        (f: any) => String(f.refId) === String(parentId)
      );
      if (parentFolder) {
        parentFolder.children.push(i);
      }
    }
  });

  const kbIds = kbs.map((i: any) => String(i.refId));

  const _folderList = (fixFolderStatistics(folderList) || []).filter(
    (i) => i.parentId === i.kbId
  );
  const _files = files.filter((f: any) => kbIds.includes(String(f.parentId)));
  const _treeData = [...kbs].map((k: any) => {
    const { refId } = k;
    const childFolders = _folderList.filter(
      (f: any) => String(f.parentId) === String(refId)
    );
    const childFiles = _files.filter(
      (f: any) => String(f.parentId) === String(refId)
    );

    return {
      ...k,
      children: [...childFiles, ...childFolders]
    };
  });
  const _data: any[] = _treeData;
  return [...(_data || []).filter((i: any) => i.children.length)];
};

const SelectMaterialExtract: React.FC<Iprops> = ({
  handleSelectItem,
  materialTreeData,
  activeFile
}: Iprops) => {
  const curMaterialTree = useMemo(() => {
    return fixTreeData(materialTreeData);
  }, [materialTreeData]);

  const goToUpload = () => {
    window.open(location.origin + "/docWriting/resource");
  };

  // 搜索结果
  const [filterList, setFilterList] = useState<any>([]);
  const [searchValue, setSearchValue] = useState<string>("");
  const handleSearch = () => {
    if (!searchValue) {
      setFilterList([]);
      return;
    }
    const searchList = (materialTreeData?.files || []).filter((item: any) =>
      (item?.name || "").includes(searchValue)
    );
    setFilterList(searchList);
  };
  const searchChange = (e: any) => {
    setSearchValue(e.target.value);
  };

  const getKbName = (kbId: number) => {
    const kb = (materialTreeData.kbs || []).find((i) => i.refId === kbId);
    return kb?.name || "--";
  };

  return (
    <div>
      <div className="flex mb-3 justify-between">
        <PrimaryBtn
          type="primary"
          icon={<UploadOutlined />}
          onClick={goToUpload}
        >
          上传
        </PrimaryBtn>
        <div className="w-[350px]">
          <Input
            placeholder="搜索素材名称"
            value={searchValue}
            disabled={!curMaterialTree.length}
            onPressEnter={handleSearch}
            onChange={searchChange}
            suffix={<SearchOutlined onClick={handleSearch} />}
          />
        </div>
      </div>
      {filterList.length ? (
        filterList.map((i: any, idx: number) => {
          return (
            <div
              className="flex items-center py-3 border-solid border-0 border-b-[1px] border-[#eee] cursor-pointer"
              key={`filter-list-${idx}`}
              style={{
                background: activeFile?.key === i.key ? "#F1F5FF" : ""
              }}
              onClick={() => handleSelectItem(i)}
            >
              <div className="ml-4 mr-3">{getIcon(i)}</div>
              <div className="flex-1 w-[740px] truncate" title={i.title}>
                {i.name}
              </div>
              <div className="text-[#888] text-xs ml-14 px-1">
                {getKbName(i.kbId)}
              </div>
            </div>
          );
        })
      ) : (
        <Tree
          treeData={curMaterialTree}
          selectable={false}
          titleRender={(node: any) => {
            return (
              <span
                className="flex w-[650px] pr-10"
                onClick={() => handleSelectItem(node)}
                style={{
                  background: activeFile?.key === node.key ? "#F1F5FF" : ""
                }}
              >
                {getIcon(node)}
                <span className="truncate" title={node.name}>
                  {node.name}
                </span>
              </span>
            );
          }}
        />
      )}
    </div>
  );
};
export default SelectMaterialExtract;
