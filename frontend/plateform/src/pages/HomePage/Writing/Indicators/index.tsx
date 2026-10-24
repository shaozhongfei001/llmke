import React, { useCallback, useMemo } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { CommonLayout } from "../common/components/CommonLayout";
import SplitLayout from "@/components/SplitLayout";
import { SplitLayoutProvider } from "@/components/SplitLayout/SplitLayoutContext";
import CategoryTree from "./CategoryTree";
import IndicatorDetail from "./IndicatorDetail";
import { BackIcon } from "@/components/Icon";

const WritingIndicatorsPage: React.FC = () => {
  const location = useLocation();
  const navigator = useNavigate();

  const isIndex = useMemo(() => {
    return location.pathname.split("/").length === 3;
  }, [location.pathname]);

  const goBackToIndicator = () => {
    navigator(`/docWriting/indicator`);
  };

  const getName = useCallback(() => {
    return isIndex ? (
      "指标管理"
    ) : (
      <div className="text-gray-2a text-base">
        <BackIcon
          className="cursor-pointer mr-4 hover:opacity-85"
          onClick={goBackToIndicator}
        />
        <b>勾稽关系配置</b>
      </div>
    );
  }, [isIndex]);

  return (
    <CommonLayout name={getName()}>
      {isIndex ? (
        <SplitLayout
          leftPanel={<CategoryTree />}
          rightPanel={<IndicatorDetail />}
          className="rounded-lg overflow-hidden "
        />
      ) : (
        <SplitLayoutProvider>
          <Outlet />
        </SplitLayoutProvider>
      )}
    </CommonLayout>
  );
};

export default WritingIndicatorsPage;
