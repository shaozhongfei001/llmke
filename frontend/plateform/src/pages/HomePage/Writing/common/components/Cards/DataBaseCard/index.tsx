import {
  DeleteOutlined,
  QuestionCircleOutlined,
  EllipsisOutlined
} from "@ant-design/icons";
import mysqlIcon from "@/assets/svg/mysql.svg";
import mongoIcon from "@/assets/svg/mongo.svg";
import defaultDbIcon from "@/assets/svg/db.svg";

import { useState } from "react";
import { Tooltip } from "antd";
import { useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import "./style.less";
import DeleteConfirm from "@/pages/HomePage/Writing/common/components/DeleteModal";
import { useServices } from "@/pages/HomePage/Writing/ResourceM/compoments/Database/service.ts";
const dbTypes: any = {
  0: "mysql",
  1: "mongo"
};

const dbIcon: any = {
  0: mysqlIcon,
  1: mongoIcon
};
const DatabaseCard = ({ item, queryDbList }: any) => {
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
    if (connectionState) {
      navigate(`/docWriting/resource/db/${id}`);
    } else {
      return;
    }
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
        onClick={gotoDetail}
        style={{
          cursor: connectionState ? "pointer" : "not-allowed"
        }}
      >
        {!!updateState && (
          <span className="inline-block absolute top-[8px] right-[8px] w-3 h-3 rounded-full bg-[#ffa500]" />
        )}
        <div className="mb-4 flex">
          <div>
            <img src={dbIcon[type] || defaultDbIcon} alt="" className="mr-3" />
          </div>
          <div>
            <div>{name || "--"}</div>
            <div className="flex">
              <span className="text-[#3a87ce] bg-[#eaf4ff] px-2 py-[1px] align-middle mt-[5px] mr-[5px]">
                {dbTypes[type] || "--"}
              </span>
              <span
                className=" px-2 py-[1px] align-middle mt-[5px]"
                style={{
                  color: connectionState ? "#47A376" : "#FF483D",
                  backgroundColor: connectionState ? "#F2FFFC" : "#FFF9F9"
                }}
              >
                {connectionState ? (
                  "已连接"
                ) : (
                  <Tooltip
                    title={<span className="text-[#555555]">{errorLog}</span>}
                    color={"#fff"}
                  >
                    <span className="cursor-pointer">连接失败</span>
                    <QuestionCircleOutlined
                      color={"#FF483D"}
                      className="ml-[6px]"
                    />
                  </Tooltip>
                )}
              </span>
            </div>
          </div>
        </div>
        <div className="flex align-middle mb-2">
          <div className="text-[#888] min-w-[42px]">描述：</div>
          <div className="truncate text-[#555555]">{description || "--"}</div>
        </div>
        <div className="flex align-middle mb-2">
          <div className="text-[#888]">用户名：</div>
          <div className="text-[#555555]">{account || "--"}</div>
        </div>
        <div className="flex align-middle mb-2 justify-between items-center">
          <div className="flex align-middle">
            <div className="text-[#888]">创建时间：</div>
            <div className="text-[#555555]">
              {gmtCreate ? dayjs(gmtCreate).format("YYYY-MM-DD hh:mm") : "--"}
            </div>
          </div>
          <Tooltip
            className="inline-block"
            placement="right"
            arrow={false}
            overlayInnerStyle={{
              padding: 0
            }}
            title={
              <div className="w-[68px] text-center leading-[32px] cursor-pointer">
                {!connectionState && (
                  <div
                    className="text-[#555555] hover:bg-[#F1F5FF]"
                    onClick={(e) => {
                      e.stopPropagation();
                      refresh();
                    }}
                  >
                    重连
                  </div>
                )}
                <div
                  className="text-[#555555] hover:bg-[#F1F5FF]"
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsShowDeleteModal(true);
                  }}
                >
                  删除
                </div>
              </div>
            }
            color={"#fff"}
          >
            <EllipsisOutlined
              className="hover:bg-[#F1F5FF] hover:text-[#055AFF] cursor-pointer h-6 px-1 text-base rounded pt-[2px]"
              onClick={(e) => e.stopPropagation()}
            />
          </Tooltip>
        </div>
      </div>
    </>
  );
};
export default DatabaseCard;
