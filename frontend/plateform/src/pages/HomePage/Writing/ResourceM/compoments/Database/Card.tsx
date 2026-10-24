import mysqlIcon from "@/assets/svg/mysql.svg";
import mongoIcon from "@/assets/svg/mongo.svg";
import defaultDbIcon from "@/assets/svg/db.svg";
import { DeleteOutlined } from "@ant-design/icons";
import { PrimaryBtn } from "../../../common/components/PrimaryBtn";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import DeleteConfirm from "../../../common/components/DeleteModal";
import { useServices } from "./service";

const dbTypes: any = {
  0: "mysql",
  1: "mongo"
};

const dbIcon: any = {
  0: mysqlIcon,
  1: mongoIcon
};

const Card = ({ item, queryDbList }: any) => {
  const {
    id,
    name,
    description,
    type,
    driver,
    connectionState,
    updateState,
    tables,
    account,
    errorLog,
    gmtCreate,
    address
  } = item;
  const { delDbById, getOnlineDb } = useServices();
  const navigate = useNavigate();

  const [hoverId, setHoverId] = useState<number | undefined>();
  const [isShowDeleteModal, setIsShowDeleteModal] = useState<boolean>(false);

  const cancelDelete = (state: boolean) => {
    setIsShowDeleteModal(state);
  };

  const deleteDb = async () => {
    await delDbById.mutateAsync(id);
    cancelDelete(false);
    queryDbList.refetch();
  };

  const gotoDetail = () => {
    navigate(`/docWriting/resource/db/${id}`);
  };

  const refresh = async () => {
    const res = await getOnlineDb.mutateAsync({
      account,
      address,
      driver,
      id,
      type
    });
    res && queryDbList.refetch();
  };

  return (
    <>
      <DeleteConfirm
        isShowDeleteModal={isShowDeleteModal}
        closeModal={cancelDelete}
        confirmModal={deleteDb}
        loading={delDbById.isLoading}
      />
      <div
        className="card p-4 rounded-lg relative"
        onMouseEnter={() => setHoverId(id)}
        onMouseLeave={() => setHoverId(undefined)}
      >
        {!!updateState && (
          <span className="inline-block absolute top-4 right-4 w-3 h-3 rounded-full bg-[#ffa500]" />
        )}
        <div className="mb-4 flex">
          <div>
            <img src={dbIcon[type] || defaultDbIcon} alt="" className="mr-3" />
          </div>
          <div>
            <div>{name || "--"}</div>
            <span className="inline-block text-[#3a87ce] bg-[#eaf4ff] px-2 py-[1px] align-middle mt-[5px]">
              {dbTypes[type] || "--"}
            </span>
          </div>
        </div>
        <div className="flex align-middle mb-2">
          <div className="font-[#888]">用户名：</div>
          <div>{account || "--"}</div>
        </div>
        <div className="flex align-middle mb-2">
          <div className="font-[#888]">链接状态：</div>
          <div
            style={{
              color: connectionState ? "#34c759" : "#ff3830"
            }}
          >
            {connectionState ? "已连接" : "连接失败"}
          </div>
        </div>
        <div className="flex align-middle mb-2">
          <div className="font-[#888]">创建时间：</div>
          <div>
            {gmtCreate ? dayjs(gmtCreate).format("YYYY-MM-DD hh:mm") : "--"}
          </div>
        </div>
        <div className="flex align-middle mb-2">
          <div className="font-[#888] min-w-[42px]">描述：</div>
          <div className="truncate">{description || "--"}</div>
        </div>

        {hoverId && (
          <div className="absolute top-0 left-0 h-full w-full rounded-lg bg-[rgba(0,0,0,0.5)] flex justify-center items-center">
            <div className="flex gap-2">
              <div className="h-8 w-8 rounded bg-white flex justify-center items-center">
                <DeleteOutlined
                  style={{
                    fontSize: 16
                  }}
                  onClick={() => {
                    setIsShowDeleteModal(true);
                  }}
                />
              </div>
              {connectionState ? (
                <PrimaryBtn onClick={gotoDetail}>查看详情</PrimaryBtn>
              ) : (
                <PrimaryBtn onClick={refresh} loading={getOnlineDb.isLoading}>
                  刷新
                </PrimaryBtn>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
};
export default Card;
