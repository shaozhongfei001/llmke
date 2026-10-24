import { Flex } from "antd";
import { useEffect, useMemo } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import SensitiveWords from "@/components/Sensitive/list";
import SensitiveDetail from "@/components/Sensitive/detail";
import IconArrowLeft from "@/assets/svg/icon-arrow-left.svg";

const Title = () => {
  const location = useLocation();
  const navigator = useNavigate();
  const { id, version } = useParams();
  const modalType = useMemo(() => {
    return id && id.indexOf("temp") > -1 ? "add" : "edit";
  }, [id]);
  const isVersion = useMemo(() => {
    return location.pathname.includes("/docWriting/template/version");
  }, [location]);
  const versionTxt = useMemo(() => {
    return version ? version.split("-")[1] : 0;
  }, [version]);
  return (
    <>
      <b
        className="text-base text-[#055AFF] cursor-pointer"
        onClick={() => {
          navigator(`/docWriting/template/segment/${id}`, {
            replace: true
          });
        }}
      >
        {isVersion
          ? `查看场景版本 - V1.${versionTxt}`
          : modalType === "edit"
            ? "编辑场景"
            : "新建场景"}
      </b>
      <span className="text-[#BBBBBB] mx-[4px]">/</span>
      <b
        className="text-[16px] text-[#055AFF] border cursor-pointer"
        onClick={() => {
          navigator(-1);
        }}
      >
        敏感词库管理
      </b>
      <span className="text-[#BBBBBB] mx-[4px]">/</span>
    </>
  );
};

const SensitiveDetailPage = () => {
  return <SensitiveDetail />;
};
export default SensitiveDetailPage;
