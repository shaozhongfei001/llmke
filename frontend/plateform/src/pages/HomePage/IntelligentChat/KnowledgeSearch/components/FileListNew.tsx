import React, { useState, useMemo, useEffect } from "react";
import { uid } from "uid";
import xls from "@/components/AiChatComparison/assets/img/xls.png";
import txt from "@/components/AiChatComparison/assets/img/txt.png";
import doc from "@/components/AiChatComparison/assets/img/doc.png";
import pdf from "@/components/AiChatComparison/assets/img/pdf.png";
import ppt from "@/components/AiChatComparison/assets/img/ppt.png";
import { CaretRightOutlined, CaretDownOutlined } from "@ant-design/icons";
import { createPlateEditor, Plate } from "@udecode/plate-common/react";
import { displayerEditor } from "@/components/AiChat/components/editor/plugins/displayer";
import { deserializeMd } from "@udecode/plate-markdown";
import { validateAndFixNodes } from "@/components/CommonEditor/ChatViewEditor";
import {
  isMarkdownTableData,
  tableValue
} from "@/components/CommonEditor/ui/tableValue";
import { Editor } from "@/components/AiChat/components/editor";
import { Image, Checkbox, Pagination } from "antd";
import ImageGroupView from "@root/src/components/ImageGroupView";
import "./new-style.less";
import { getNameBySource, getTypeBySource } from "@root/src/core/helps";

export const FILEIMG: any = {
  docx: doc,
  doc: doc,
  pdf: pdf,
  xls: xls,
  xlsx: xls,
  ppt: ppt,
  pptx: ppt,
  pub: ppt,
  txt: txt
};
interface FileListProps {
  selectFile: string;
  selectBlock: string;
  fileList: Array<any>;
  selectFileHandler: (fileId: string) => void;
  selectBlockHandler: (blockId: string) => void;
}
const pageSize = 10;
const FileListNew: React.FC<FileListProps> = ({
  fileList,
  selectFile,
  selectBlock,
  selectFileHandler,
  selectBlockHandler
}) => {
  const [isOpenList, setIsOpenList] = useState<boolean>(false);
  const [checkedFileList, setCheckedFileList] = useState<Array<string>>([]);
  const [pageNo, setPageNo] = useState<number>(1);
  const [total, setTotal] = useState<number>(0);

  const totalChunkList = useMemo(() => {
    if (fileList && fileList.length) {
      setCheckedFileList(fileList.map((i: any) => i.url));

      const list = fileList.map((i: any) => {
        const { fileExtension, fileName, list, url } = i;
        return (list || []).map((l: any) =>
          Object.assign({}, l, {
            fileExtension,
            fileName,
            url
          })
        );
      });
      console.log("list:", list);
      return [...list.flat(Infinity)];
    }
    return [];
  }, [fileList]);

  const chundList = useMemo(() => {
    const list = totalChunkList.filter((i: any) =>
      checkedFileList.includes(i.url)
    );
    if (list.length) {
      setTotal(list.length);
      let _pageNo = pageNo;
      if (_pageNo > 1 && (_pageNo - 1) * pageSize > list.length) {
        _pageNo = 1;
      }
      const curList = list.slice(pageSize * (_pageNo - 1), _pageNo * pageSize);
      return curList.length ? [...curList] : [];
    }
    return [];
  }, [totalChunkList, pageNo, checkedFileList]);

  const selectThisFile = (fileId: string) => () => {
    if (selectFile !== fileId) {
      selectFileHandler(fileId);
    }
  };

  const selectThisBlock = (fileId: string, blockId: string) => () => {
    if (selectBlock !== blockId) {
      fileId !== selectFile && selectFileHandler(fileId);
      selectBlockHandler(blockId);
    }
  };
  const changeOpenSta = () => {
    setIsOpenList(!isOpenList);
  };

  const checkedFileListOnChange = (url: string) => (e: any) => {
    const _checkedFileList = [...checkedFileList];
    if (e.target.checked) {
      setCheckedFileList(Array.from(new Set([..._checkedFileList, url])));
    } else {
      setCheckedFileList(_checkedFileList.filter((i) => i !== url));
    }
  };

  const pageNoOnChangeHandler = (pageNo: number) => {
    setPageNo(pageNo);
  };

  const traverseTree = (tree: any[]) => {
    function traverseTreeNode(node: any) {
      if (node.children && node.children.length > 0) {
        node.children.forEach((child: any, index: any) => {
          if (child.text) {
            if (isMarkdownTableData(child.text)) {
              node.children[index] = tableValue(node.children[0].text)[0];
            }
          }
          traverseTreeNode(child); // 递归遍历子节点
        });
      }
    }

    // 从根节点开始遍历整个树
    tree.forEach((node, index) => {
      traverseTreeNode(node);
    });
  };

  const WithPlate = ({ id, data, className = "", type }: any) => {
    const tempEditor = createPlateEditor({
      plugins: [...displayerEditor({}).plugins]
    });

    let deserializedData = deserializeMd(tempEditor, data || "");
    if (type === "table") {
      deserializedData = validateAndFixNodes(deserializedData);
      traverseTree(deserializedData);
    }

    const editor = createPlateEditor({
      ...displayerEditor({}),
      id: id,
      shouldNormalizeEditor: true,
      value: deserializedData
    });

    return (
      <Plate editor={editor}>
        <Editor readOnly className={className} />
      </Plate>
    );
  };

  return (
    <div className="refrence-list-wrap text-[#2a2a2a] text-sm">
      <div className="bg-white rounded-lg mb-3 overflow-hidden select-none">
        <div
          className={`px-5 py-3 min-h-8 flex list-title-wrap justify-between ${
            isOpenList ? "open-list" : ""
          }`}
        >
          <div className="text-[#2a2a2a]">
            已筛选：<span className="mx-1">{checkedFileList.length}</span>个文件
          </div>
          <div
            className={`${isOpenList ? "open-btn" : "close-btn"} opener-btn`}
          >
            <span onClick={changeOpenSta}>
              {isOpenList ? "收起" : "展开"}
              {isOpenList ? <CaretDownOutlined /> : <CaretRightOutlined />}
            </span>
          </div>
        </div>
        {isOpenList ? (
          <div className="list-wrap px-5 py-4">
            {fileList.length === 0 ? (
              <div className="text-center text-[#555] text-xs">暂无文件</div>
            ) : (
              (fileList || []).map((i: any, idx: number) => {
                const { fileExtension, fileName, list, url } = i;
                return (
                  <div key={`file-name-row-${idx}`}>
                    <Checkbox
                      onChange={checkedFileListOnChange(url)}
                      checked={checkedFileList.includes(url)}
                    >
                      <div className="text-ellipsis break-words line-clamp-1 overflow-hidden">
                        {getNameBySource(i?.metadata?.source)}
                      </div>
                    </Checkbox>
                  </div>
                );
              })
            )}
          </div>
        ) : null}
      </div>
      {(chundList || []).map((i: any) => {
        const {
          fileExtension,
          fileName,
          url,
          page_content,
          id,
          pic_url_list,
          metadata
        } = i;
        const { chunk_type, image_path } = metadata;
        return (
          <div
            key={`chunk-row-${id}`}
            className={`rounded-lg bg-white mb-3 overflow-hidden text-sm chunk-wrap ${
              selectBlock === id ? "select-chunk" : ""
            }`}
          >
            <div
              className="px-5 py-4 chatView"
              style={{ borderBottom: "1px solid #EFF5FF" }}
              onClick={selectThisBlock(url, id)}
            >
              {chunk_type === "text" ? (
                <span>{page_content}</span>
              ) : (
                <div className={`${image_path ? "flex" : ""}`}>
                  {image_path ? (
                    <Image
                      src={image_path}
                      className="object-contain max-w-[126px] max-h-[126px]"
                    />
                  ) : null}

                  <div
                    className={`text-sm ${
                      image_path ? "w-[calc(100%-150px)] ml-[10px]" : ""
                    }`}
                  >
                    <WithPlate
                      id={uid(32)}
                      className="px-0 py-0 text-[14px] text-[#2a2a2a] overflow-x-hidden bg-transparent"
                      data={page_content}
                      type={chunk_type}
                    />
                  </div>
                  {pic_url_list && pic_url_list.length ? (
                    <div className="flex flex-wrap mt-[10px]">
                      <ImageGroupView imageList={pic_url_list} />
                    </div>
                  ) : null}
                </div>
              )}
            </div>
            <div className="relative pl-11 pt-3 pr-5 pb-4 text-xs text-[#555] bg-[#fafcff]">
              <img
                src={
                  FILEIMG[getTypeBySource(metadata.source)] || FILEIMG["doc"]
                }
                width={16}
                height={16}
                className="absolute left-5 top-[10px]"
              />
              <div
                className={`text-ellipsis break-words line-clamp-1 overflow-hidden file-name-link ${
                  selectFile === url ? "select-file" : ""
                }`}
                onClick={selectThisFile(url)}
              >
                {getNameBySource(metadata.source)}
              </div>
            </div>
          </div>
        );
      })}
      {chundList.length ? (
        <div className="bg-white px-5 py-4 mb-1 rounded-lg overflow-hidden">
          <Pagination
            defaultCurrent={pageNo}
            total={total}
            pageSize={pageSize}
            align="end"
            onChange={pageNoOnChangeHandler}
          />
        </div>
      ) : null}
    </div>
  );
};
export default FileListNew;
