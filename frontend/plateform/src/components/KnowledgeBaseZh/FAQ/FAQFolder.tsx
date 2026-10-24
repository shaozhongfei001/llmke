import { Button, Checkbox, Popconfirm, Popover, Tag } from "antd";
import { rowActionType } from "../common/useFaqController";
import IconFolder from "@/assets/knowledgebase/icon-folder.svg";
import EditTag from "@/assets/img/editTag.png";
import { useMemo, useState } from "react";
import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";
import LabelCom from "../components/LabelCom";
const FAQFolder = ({ key, item, rowActionHandler, idx }: any) => {
  const labels = useMemo(() => {
    if (item.label) {
      return item.label.split(",");
    } else {
      return [];
    }
  }, [item]);
  return (
    <>
      <div
        key={key}
        className="flex items-center pt-[12px] pb-[16px] px-[12px] mb-[4px]"
        style={{ borderBottom: "1px solid #ebebeb" }}
      >
        <Checkbox
          checked={item.isChecked}
          className="mr-[16px]"
          onChange={(v) =>
            rowActionHandler(rowActionType.CHECK_QA, {
              idx,
              isChecked: v.target.checked
            })
          }
        />
        <img className="mr-2 relative top-[2px] h-5" src={IconFolder} />
        <div
          className="mr-[20px] w-[200px] text-ellipsis line-clamp-1 cursor-pointer"
          onClick={() => {
            rowActionHandler(rowActionType.CLICK_FOLDER, {
              folderId: item.dataType === 1 ? item.folderId : item.fileId,
              name: item.folderName || item.fileName,
              dataType: item.dataType
            });
          }}
        >
          {item.folderName || item.fileName || "未命名文件夹"}
        </div>

        <LabelCom
          labels={labels}
          item={item}
          rowActionHandler={rowActionHandler}
        />
        <div className="w-[210px] flex justify-end">
          <Button
            type="link"
            size={"small"}
            disabled={getBtnDisabled(FILE_BTN.EDIT, item.permission)}
            onClick={() => {
              rowActionHandler(rowActionType.TRANSFER, item);
            }}
          >
            转移到
          </Button>
          {item.dataType === 1 && (
            <Button
              type="link"
              size={"small"}
              onClick={() => {
                rowActionHandler(rowActionType.FOLDER_RENAME, item);
              }}
              disabled={getBtnDisabled(FILE_BTN.EDIT, item.permission)}
            >
              重命名
            </Button>
          )}
          <Button
            size={"small"}
            type="link"
            onClick={() => {
              rowActionHandler(rowActionType.PERMISSION, item);
            }}
            disabled={getBtnDisabled(FILE_BTN.AUTHORIZE, item.permission)}
          >
            授权
          </Button>
          <Popconfirm
            title="删除文件"
            placement="topLeft"
            description={
              <span>
                删除后将连同子文件一并移
                <br />
                除，确定要继续吗?
              </span>
            }
            okText="确认"
            cancelText="取消"
            onConfirm={() =>
              rowActionHandler(rowActionType.DELETE_FOLDER, item)
            }
          >
            <Button
              type="link"
              size={"small"}
              disabled={getBtnDisabled(FILE_BTN.DELETE, item.permission)}
            >
              删除
            </Button>
          </Popconfirm>
        </div>
      </div>
    </>
  );
};

export default FAQFolder;
