import mysqlIcon from "@/assets/svg/mysql.svg";
import mongoIcon from "@/assets/svg/mongo.svg";
import defaultDbIcon from "@/assets/svg/db.svg";
import { CONNECT_TYPES } from "@/const/database";

interface Iprops {
  info: any;
}

const dbIcon: any = {
  0: mysqlIcon,
  1: mongoIcon
};

const DataBaseDetailInfo = (props: Iprops) => {
  const { info } = props;

  const getConnectStatus = (item: any) => {
    const { status } = item;

    return status === CONNECT_TYPES.CONNECTED ? (
      <span className="border-[1px] border-[#a1d7c2] border-solid bg-[#f7fcfb] rounded-sm inline-block w-14 text-center text-[#47a376] text-xs">
        已连接
      </span>
    ) : status === CONNECT_TYPES.DISABLED ? (
      <span className="border-[1px]border-solid rounded-sm inline-block w-14 text-center text-xs">
        未连接
      </span>
    ) : null;
  };

  return (
    <div className="bg-white rounded-lg px-4 py-4 flex items-center align-middle">
      <div className="flex w-[285px] box-border">
        <div className="w-14 h-14 px-1 py-1 bg-[#fafafa] rounded flex justify-center items-center mr-4">
          <img src={dbIcon[info?.type] || defaultDbIcon} />
        </div>
        <div>
          <div className="py-1">
            <b className="mr-2 text-[#2a2a2a] tetx-base">{info.name || "--"}</b>
            {getConnectStatus(info)}
          </div>
          <div className="">
            <span className="rounded-sm bg-[#eaf4ff] px-2 text-[#3a87ce] text-sm text-center">
              {info.dbType || "--"}
            </span>
          </div>
        </div>
      </div>
      <div>
        <div className="flex text-sm text-[#888] mb-3">
          <div className="mr-4 text-nowrap">
            用户名：
            <span className="text-[#2a2a2a]">{info.useName || "--"}</span>
          </div>
          <div className="mr-4 text-nowrap">
            创建时间：
            <span className="text-[#2a2a2a]">{info.createTime || "--"}</span>
          </div>
          <div className="truncate text-nowrap pr-4">
            服务器地址：
            <span className="text-[#2a2a2a]" title={info.connectUrl || "--"}>
              {info.connectUrl}
            </span>
          </div>
        </div>
        <div className="flex text-sm">
          <div className="text-[#888]">描述：</div>
          <div
            className="text-[#2a2a2a] pr-2 flex-1 truncate max-w-[calc(100vw-500px)]"
            title={info.description || "--"}
          >
            {info.description}
          </div>
        </div>
      </div>
    </div>
  );
};
export default DataBaseDetailInfo;
