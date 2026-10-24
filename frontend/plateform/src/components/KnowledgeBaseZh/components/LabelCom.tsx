import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";
import { Popover, Tag } from "antd";
import { rowActionType } from "../common/useFaqController";
import EditTag from "@/assets/img/editTag.png";

const LabelCom = ({
  labels,
  item,
  rowActionHandler
}: {
  labels: any[];
  item: any;
  rowActionHandler: any;
}) => {
  return (
    <div className="flex flex-1 items-center">
      {labels.length ? (
        <>
          <Popover
            placement="bottom"
            content={
              <div className="w-[400px]">
                {labels.reduce((acc: any, cur: any) => {
                  return `${acc}#${cur}# `;
                }, "")}
              </div>
            }
          >
            <>
              {labels.slice(0, 2).map((item: any) => {
                return (
                  <Tag
                    bordered={false}
                    color="processing"
                    className="max-w-[100px] text-ellipsis *:overflow-hidden whitespace-nowrap overflow-hidden cursor-default"
                  >
                    {item}
                  </Tag>
                );
              })}
            </>
          </Popover>
          {labels.length ? (
            <Tag bordered={false} color="processing" className="cursor-default">
              +{labels.length}
            </Tag>
          ) : null}
        </>
      ) : null}
      <img
        src={EditTag}
        width={24}
        height={24}
        className={`${getBtnDisabled(FILE_BTN.EDIT, item.permission) ? "cursor-not-allowed opacity-50" : "cursor-pointer"}`}
        onClick={() => {
          if (getBtnDisabled(FILE_BTN.EDIT, item.permission)) return;
          rowActionHandler(rowActionType.OPEN_TAGS, { ...item, tags: [] });
        }}
      />
    </div>
  );
};

export default LabelCom;
