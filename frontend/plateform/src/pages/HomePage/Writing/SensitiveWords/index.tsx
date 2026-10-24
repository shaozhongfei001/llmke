import { Flex } from "antd";
import { useEffect, useMemo } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import SensitiveWords from "@/components/Sensitive/list";
import IconArrowLeft from "@/assets/svg/icon-arrow-left.svg";

const SensitiveWordsPage = () => {
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
      <Flex justify="flex-start" align="center" className="mb-4">
        {/* <img
          className="mr-2 pb-[2px] cursor-pointer"
          src={IconArrowLeft}
          onClick={() => {
            navigator(`/docWriting/template/segment/${id}`, {
              replace: true
            });
          }}
        />
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
        <span className="text-[#BBBBBB] mx-[4px]">/</span> */}
        <b className="text-[16px] text-text-color1">敏感词管理</b>
      </Flex>
      <SensitiveWords />
    </>
  );
};
export default SensitiveWordsPage;
