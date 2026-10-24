import { useState, useEffect } from "react";
import { message } from "antd";
import { useNavigate } from "react-router-dom";
import loading from "@/assets/gif/loading.gif";
import AnalysisPng from "@/assets/img/analysis_component.png";
import { PrimaryBtn } from "@/pages/HomePage/Writing/common/components/PrimaryBtn";
import { useServices } from "../common/server.ts";
import { IAnalysis } from "../common/type.ts";
import { PlusOutlined } from "@ant-design/icons";
import AnalysisCard from "../../common/components/Cards/AnalysisCard.tsx";
import AddModal from "../components/AddModal";
import "../common/style.less";
interface Iprops {
  id: string;
  refreshTree: () => void;
}
const AnalysisCategoryDetail = ({ id, refreshTree }: Iprops) => {
  const [analysisList, setAnalysisList] = useState<IAnalysis[]>();
  const [isShowModal, setIsShowModal] = useState<{
    isShow: boolean;
    id?: string;
    title?: string;
  }>({
    isShow: false
  });
  const {
    getAnalysisList,
    deleteAnalysis,
    copyAnalysis,
    updateAnalysis,
    addAnalysis
  } = useServices();
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const navigator = useNavigate();

  useEffect(() => {
    if (id) {
      setIsLoading(true);
      getAnalysisCategoryDetail();
    }
  }, [id]);

  //获取分析组件列表
  const getAnalysisCategoryDetail = async () => {
    try {
      const res = await getAnalysisList.mutateAsync({ id });
      setAnalysisList(res?.details);
      setIsLoading(false);
    } catch (e) {
      console.log("get chapter detail err ------>", e);
    }
  };

  const deleteNode = async (id: string) => {
    try {
      const res = await deleteAnalysis.mutateAsync(id);
      if (res) {
        getAnalysisCategoryDetail();
      }
    } catch (e) {
      console.error("delete ananlysis failed---->", e);
    }
  };

  const duplicateNode = async (id: string) => {
    try {
      const res = await copyAnalysis.mutateAsync(id);
      if (res) {
        getAnalysisCategoryDetail();
      }
    } catch (e) {
      console.error("copy ananlysis failed---->", e);
    }
  };

  const updateNode = async (name: string, id: string) => {
    try {
      const res = await updateAnalysis.mutateAsync({
        id,
        name
      });
      if (res) {
        message.success("组件重命名成功");
        await getAnalysisCategoryDetail();
        return res;
      }
    } catch (e) {
      console.error("rename ananlysis failed---->", e);
    }
  };

  const addNode = async (name: string) => {
    try {
      const res = await addAnalysis.mutateAsync({
        categoryId: id,
        name
      });
      if (res) {
        await getAnalysisCategoryDetail();
        return res;
      }
    } catch (e) {
      console.error("add ananlysis failed---->", e);
    }
  };

  const goDetail = (id: string) => {
    navigator(`/docWriting/component/analyze/${id}`);
  };

  return (
    <>
      {isLoading ? (
        <div className="w-full h-full flex justify-center items-center">
          <img src={loading} width={56} />
        </div>
      ) : (
        <div className="px-[20px] py-[16px] h-full">
          <div className="w-full flex h-[32px]  justify-between items-center">
            <PrimaryBtn
              icon={<PlusOutlined color="#ffffff" />}
              onClick={() => {
                setIsShowModal({
                  isShow: true
                });
              }}
            >
              新建
            </PrimaryBtn>
          </div>
          {analysisList && analysisList?.length > 0 ? (
            <div className="mt-[16px] h-[calc(100%-48px)] flex flex-wrap content-start gap-4 overflow-y-auto">
              {analysisList.map((a: IAnalysis) => {
                return (
                  <AnalysisCard
                    key={`card-list-${a.id}`}
                    detail={a}
                    deleteNode={deleteNode}
                    duplicateNode={duplicateNode}
                    goDetail={goDetail}
                    renameNode={() => {
                      setIsShowModal({
                        isShow: true,
                        id: a.id,
                        title: a.name
                      });
                    }}
                  />
                );
              })}
            </div>
          ) : (
            <div className="flex w-full justify-center items-center h-[calc(100%-48px)]">
              <img src={AnalysisPng} width={540} />
            </div>
          )}
          <AddModal
            isShow={isShowModal.isShow}
            closeModal={() =>
              setIsShowModal({
                isShow: false,
                id: undefined,
                title: undefined
              })
            }
            id={isShowModal.id}
            initailTitle={isShowModal.title}
            confirmModal={async (title, id) => {
              if (id) {
                return updateNode(title, id);
              } else {
                return addNode(title);
              }
            }}
          />
        </div>
      )}
    </>
  );
};

export default AnalysisCategoryDetail;
