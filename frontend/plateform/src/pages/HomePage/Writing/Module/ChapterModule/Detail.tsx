import { useState, useEffect, useRef, useMemo } from "react";
import { Button, Form, Input, message } from "antd";
import chapter from "@/assets/img/chapter.png";
import loading from "@/assets/gif/loading.gif";

import type { InputRef } from "antd/es/input";
import { useServices } from "../common/server.ts";
import { ISection } from "../common/type.ts";
import { extractTemplateVariables } from "../common/utils.ts";
import Section from "./Section";
import ModuleTest from "@root/src/components/ModuleTest/index.tsx";
import EditableTextAdvanced from "@root/src/components/EditableTextAdvanced";
import "../common/style.less";
import ModuleHeader from "@root/src/components/ModuleHeader/index.tsx";
import { debounce } from "lodash";
import { Title } from "@radix-ui/react-dialog";
interface Iprops {
  id: number;
  refreshDetail: boolean;
  updateTreeData: (key: string, property: string, value: any) => void;
  resetLayout: () => void;
}
const handleItemChange = ({
  value,
  itemKey,
  setDetailData,
  updateInfoById
}: {
  value: string;
  itemKey: string;
  setDetailData: any;
  updateInfoById: (params: any) => any;
}) => {
  if (itemKey === "systemPrompt" && !value) {
    message.error("系统提示词未填写");
    return;
  }
  // 更新表单
  setDetailData((p: any) => ({
    ...p,
    [itemKey]: value
  }));
  // 请求接口
  updateInfoById({
    [itemKey]: value
  });
};
const debounceChange = debounce(handleItemChange, 500);
const ChapterDetail = ({
  id,
  refreshDetail,
  updateTreeData,
  resetLayout
}: Iprops) => {
  const [chapterDetail, setChapterDetail] = useState<ISection>();
  const { getChapterById, updateChanpter } = useServices();
  const [showTest, setShowTest] = useState<boolean>(false);
  const [formSchema, setFormSchema] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    if (id) {
      getChapterDetail();
    }
  }, [id, refreshDetail]);

  //获取章节组件详情
  const getChapterDetail = async () => {
    try {
      setIsLoading(true);
      const res = await getChapterById.mutateAsync(id);
      const formS = extractTemplateVariables(res.sectionPrompt);
      setFormSchema(formS);
      setChapterDetail(res);
    } catch (e) {
      console.log("get chapter detail err ------>", e);
    } finally {
      setIsLoading(false);
    }
  };

  const test = (prompt?: string, isShow?: boolean) => {
    isShow && setShowTest(true);
    const formS = prompt ? extractTemplateVariables(prompt) : [];
    setFormSchema(formS);
  };

  // ======================== 章节详情 =========================
  const [form] = Form.useForm();
  const handleNameChange = async (title: string) => {
    if (title == chapterDetail?.sectionTitle) return;
    const res = await updateInfoById({
      sectionTitle: title
    });
    res && updateTreeData(id.toString(), "title", title);
  };

  const moduleHeaderProps = useMemo(() => {
    form.setFieldsValue({
      description: chapterDetail?.description || ""
    });
    return {
      name: chapterDetail?.sectionTitle || "未命名组件",
      systemPrompt: chapterDetail?.sectionPrompt || "",
      gmtModified: chapterDetail?.gmtModified || "",
      description: chapterDetail?.description || ""
    };
  }, [chapterDetail]);

  const updateInfoById = async (params: any) => {
    if (!id) {
      message.error("id不存在");
      return;
    }
    const res: any = await updateChanpter.mutateAsync({
      ...params,
      id: id
    });
    if (res && res.success) {
      return res;
    } else {
      false;
    }
  };

  return (
    <div className="w-full h-full pl-[20px]">
      {isLoading ? (
        <div className="w-full h-full flex justify-center items-center">
          <img src={loading} width={56} />
        </div>
      ) : (
        <>
          {chapterDetail && (
            <>
              <div className="desc flex items-center h-[78px] py-[6px] justify-between mr-[20px]">
                <div className="flex items-center">
                  <img src={chapter} width={46}></img>
                  <div className="ml-[12px]">
                    <ModuleHeader
                      {...moduleHeaderProps}
                      handleNameChange={handleNameChange}
                      type="chapter"
                    />
                    {/* <div className="font-bold mb-[4px] text-[16px] cursor-pointer">
                    <EditableTextAdvanced
                      initialValue={chapterDetail.sectionTitle}
                      onSave={async (title) => {
                        if (title == chapterDetail.sectionTitle) return;
                        const newInfo = {
                          ...chapterDetail,
                          sectionTitle: title
                        };
                        setChapterDetail(newInfo);
                        await saveSection(newInfo, true);
                      }}
                      canEmpty={false}
                    />
                  </div>
                  <div className="text-[#555555] flex items-center text-[12px] w-full cursor-pointer">
                    <div className="text-[#888888]">描述：</div>
                    <EditableTextAdvanced
                      initialValue={chapterDetail?.description || ""}
                      onSave={async (desc) => {
                        if (desc == chapterDetail?.description) return;
                        const newInfo = {
                          ...chapterDetail,
                          description: desc
                        };
                        setChapterDetail(newInfo);
                        await saveSection(newInfo, false);
                      }}
                      canEmpty={true}
                    />
                  </div> */}
                  </div>
                </div>
                <div>
                  <Button
                    style={{
                      border: "1px solid #EEEEEE",
                      color: "#2a2a2a"
                    }}
                    onClick={() => {
                      resetLayout();
                      test(chapterDetail.sectionPrompt, true);
                    }}
                  >
                    测试
                  </Button>
                </div>
              </div>
              <div className="w-full flex h-[calc(100%-75px)]  justify-between ">
                <div
                  className={`w-${showTest ? "[50%]" : "full"} h-full pr-[20px]`}
                >
                  <Form
                    form={form}
                    layout="vertical"
                    className="w-full mt-4 pb-0"
                  >
                    <Form.Item
                      label={<span className="font-bold">描述</span>}
                      name="description"
                      className="mt-[20px]"
                    >
                      <Input.TextArea
                        placeholder="请输入"
                        rows={1}
                        onChange={(e) =>
                          debounceChange({
                            value: e.target.value,
                            itemKey: "description",
                            setDetailData: setChapterDetail,
                            updateInfoById
                          })
                        }
                      />
                    </Form.Item>
                  </Form>
                  <Section
                    id={id}
                    section={chapterDetail}
                    setSection={setChapterDetail}
                    showTest={test}
                    updateTreeData={updateTreeData}
                  />
                </div>

                {showTest && (
                  <div className="bg-[#EFF1FE] w-[50%] rounded-l-[8px] ">
                    <ModuleTest
                      formSchema={formSchema}
                      closeModule={() => {
                        setShowTest(false);
                      }}
                      mouduleName={"SECTION"}
                      testId={id}
                    />
                  </div>
                )}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
};

export default ChapterDetail;
