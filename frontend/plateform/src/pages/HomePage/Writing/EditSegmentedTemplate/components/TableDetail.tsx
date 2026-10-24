import { memo } from "react";
import { Empty } from "antd";
interface Iprops {
  tableDetail: any;
}

const TableDetail = ({ tableDetail }: Iprops) => {
  return (
    <div className="p-[12px] h-full w-full">
      {tableDetail ? (
        <>
          <div className="font-bold mb-4">
            {tableDetail.name ? `${tableDetail.name}数据表详情` : "-"}
          </div>
          <div className="text-[#555] mb-4 leading-5">
            <span className="text-[#888]">描述：</span>
            {tableDetail.description || "-"}
          </div>
          <div className="flex py-4 text-[#555] font-bold bg-[#fafafa] border-solid border-0 border-b-[1px] border-[#eee]">
            <div className="pl-8 w-44">字段名称</div>
            <div className="pl-4 w-32">数据类型</div>
            <div className="pl-4 flex-1">描述</div>
          </div>

          {tableDetail?.fields?.length ? (
            <div className="overflow-y-auto h-[250px]">
              {tableDetail?.fields.map((i: any, idx: number) => {
                return (
                  <div
                    key={`common-key-${i.id}-${idx}`}
                    className="flex py-4 text-[#555] border-solid border-0 border-b-[1px] border-[#eee] items-center kew-row hover:bg-[#f1f5ff]"
                  >
                    <div className="pl-8 w-44 h-8 leading-8">{i.name}</div>
                    <div className="pl-4 w-32">{i.type || "-"}</div>
                    <div className="pl-4 w-[370px] truncate">
                      {i.description || "-"}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <Empty className="mt-20" />
          )}
        </>
      ) : (
        <Empty className="mt-20" />
      )}
    </div>
  );
};

export default memo(TableDetail);
