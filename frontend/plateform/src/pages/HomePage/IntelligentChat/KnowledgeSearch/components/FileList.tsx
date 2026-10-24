import React, { useState, useMemo, useEffect } from "react";
import { uid } from "uid";
import xls from "@/components/AiChatComparison/assets/img/xls.png";
import txt from "@/components/AiChatComparison/assets/img/txt.png";
import doc from "@/components/AiChatComparison/assets/img/doc.png";
import pdf from "@/components/AiChatComparison/assets/img/pdf.png";
import ppt from "@/components/AiChatComparison/assets/img/ppt.png";
import { DownOutlined, UpOutlined } from "@ant-design/icons";
import { createPlateEditor, Plate } from "@udecode/plate-common/react";
import { displayerEditor } from "@/components/AiChat/components/editor/plugins/displayer";
import { deserializeMd } from "@udecode/plate-markdown";
import { validateAndFixNodes } from "@/components/CommonEditor/ChatViewEditor";
import {
  isMarkdownTableData,
  tableValue
} from "@/components/CommonEditor/ui/tableValue";
import { Editor } from "@/components/AiChat/components/editor";
import { Image } from "antd";
import ImageGroupView from "@root/src/components/ImageGroupView";
import "./style.less";

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

const FileList: React.FC<FileListProps> = ({
  fileList,
  selectFile,
  selectBlock,
  selectFileHandler,
  selectBlockHandler
}) => {
  const [openIds, setOpenIds] = useState<Array<string>>([]);

  const closeBlock = (id: string) => () => {
    const idx = openIds.findIndex((i) => i === id);
    const _openIds = [...openIds];
    _openIds.splice(idx, 1);
    setOpenIds([..._openIds]);
  };

  const openBlock = (id: string) => () => {
    const _openIds = Array.from(new Set([...openIds, id]));
    setOpenIds([..._openIds]);
  };

  const selectThisFile = (fileId: string) => () => {
    if (selectFile !== fileId) {
      selectFileHandler(fileId);
    }
  };

  const selectThisBlock = (blockId: string) => () => {
    if (selectBlock !== blockId) {
      selectBlockHandler(blockId);
    }
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
      {(fileList || []).map((i: any, idx: number) => {
        const { fileExtension, fileName, list, url } = i;
        return (
          <div
            key={`refrence-row-${idx}`}
            className={`mb-3 refrence-row ${selectFile === url ? (!selectBlock ? "selected-row" : "only-select-block") : "cursor-pointer"}`}
            onClick={selectThisFile(url)}
          >
            <div className="mb-1 relative pl-6">
              <img
                src={FILEIMG[fileExtension] || FILEIMG["doc"]}
                width={16}
                height={16}
                className="absolute left-0 top-[1px]"
              />
              {fileName}.{fileExtension}
            </div>
            <div className="mb-3"></div>
            {list && list.length ? (
              <>
                <div className="line-wrap mb-3"></div>
                {/* {JSON.stringify(list.map((i) => i.page_content))} */}
                <div
                  className={`text-[#555] ${openIds.includes(url) ? "mb-3" : ""}`}
                >
                  召回chuck文本块
                  <span className="inline-block ml-2 mr-3 text-[#055aff]">
                    {list.length}
                  </span>
                  {openIds.includes(url) ? (
                    <UpOutlined
                      className="cursor-pointer text-[#888] text-xs"
                      onClick={closeBlock(url)}
                    />
                  ) : (
                    <DownOutlined
                      className="cursor-pointer text-[#888] text-xs"
                      onClick={openBlock(url)}
                    />
                  )}
                </div>
                <div className={`${openIds.includes(url) ? "" : "hidden"}`}>
                  {/* {JSON.stringify(list)} */}
                  {list.map((l: any) => {
                    const { page_content, id, pic_url_list, metadata } = l;
                    const { chunk_type, image_path } = metadata;
                    // pic_url_list.push(
                    //   "/minio/dev-rag-data/演示富文本/演示富文本_保险Ⅱ行业点评报告国常会个人养老金个人所得税优惠政策点评优限额降税费个人参与积极性有望提升行业研报/V0/parsed/images/image-4.jpg"
                    // )
                    // console.log(l)
                    return (
                      <div
                        key={`page_content_${id}`}
                        className={`p-3 rounded bg-[#f7f8fc] mb-3 block-wrap ${selectBlock === id ? "selected-block cursor-default" : "cursor-pointer"}`}
                        onClick={selectThisBlock(id)}
                      >
                        <div
                          className="text-ellipsis break-words line-clamp-2 leading-6 chatView"
                          title={chunk_type === "text" ? page_content : null}
                        >
                          {chunk_type === "text" ? (
                            <span>{page_content}</span>
                          ) : image_path ? (
                            <div className="flex ">
                              <Image
                                src={image_path}
                                className="object-contain max-w-[126px] max-h-[126px]"
                              />
                              <div className="text-[12px] w-[calc(100%-150px)] ml-[10px]">
                                <WithPlate
                                  id={uid(32)}
                                  className="px-0 py-0 text-[14px] text-[#2a2a2a] overflow-x-hidden bg-transparent"
                                  data={page_content}
                                  type={chunk_type}
                                />
                              </div>
                            </div>
                          ) : (
                            <div>
                              <div className="text-[12px]">
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
                          <WithPlate
                            id={uid(32)}
                            className="px-0 py-0 text-[14px] text-[#2a2a2a] overflow-x-hidden bg-transparent"
                            data={page_content}
                            type={chunk_type}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : null}
          </div>
        );
      })}
    </div>
  );
};
export default FileList;
