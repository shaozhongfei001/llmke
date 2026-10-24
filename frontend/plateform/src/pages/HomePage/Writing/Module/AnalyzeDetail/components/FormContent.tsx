import { Button, Form, Input, message, Modal, Popover } from "antd";
import { debounce } from "lodash";
import { useEffect, useRef, useState } from "react";
import { IAnalyzeDetail } from "..";
import { extractTemplateVariables } from "../../common/utils";
import { CloseOutlined, SearchOutlined } from "@ant-design/icons";
import EmptyIndicator from "@/assets/img/empty-indicators.png";
import SearchItem, { ItemProps } from "./SearchItem";
import { useServices } from "../common/server";
import { useClickAway } from "ahooks";

interface IProps {
  description?: string;
  systemPrompt?: string;
  userPrompt?: string;
  indicatorList?: number[];
  setDetailData: React.Dispatch<
    React.SetStateAction<{
      name: string;
      description: string;
      systemPrompt: string;
      gmtModified: string;
      userPrompt: string;
      id: string | undefined;
      categoryId: string;
      indicatorList: number[];
    }>
  >;
  updateInfoById: (params: IAnalyzeDetail) => any;
  setFormSchema: React.Dispatch<any>;
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
  updateInfoById: (params: IAnalyzeDetail) => any;
}) => {
  if (itemKey === "systemPrompt" && !value) {
    message.error("系统提示词未填写");
    return;
  }
  // 更新表单
  setDetailData((p: IAnalyzeDetail) => ({
    ...p,
    [itemKey]: value
  }));
  // 请求接口
  updateInfoById({
    [itemKey]: value
  });
};

const debounceChange = debounce(handleItemChange, 500);

function FormContent({
  description,
  systemPrompt,
  userPrompt,
  indicatorList = [],
  setDetailData,
  updateInfoById,
  setFormSchema
}: IProps) {
  const { queryIndicator } = useServices();

  const [form] = Form.useForm();

  const [indicatorsVisible, setIndicatorsVisible] = useState<boolean>(false);
  const [selectedIndicators, setSelectedIndicators] = useState<any[]>([]);
  const [searchResults, setSearchResults] = useState<ItemProps[]>([]);
  const searchValue = useRef("");
  const searchResultRef = useRef(null);

  // 点击搜索结果以外的区域，清空搜索结果
  useClickAway(() => {
    setSearchResults([]);
  }, searchResultRef);

  useEffect(() => {
    form.setFieldsValue({
      description: description || "",
      systemPrompt: systemPrompt || "",
      userPrompt: userPrompt || ""
    });
  }, [description, systemPrompt, userPrompt]);

  useEffect(() => {
    indicatorList.length && setSelectedIndicators(indicatorList);
  }, [indicatorList]);

  useEffect(() => {
    systemPrompt && setFormSchema(extractTemplateVariables(systemPrompt));
  }, [systemPrompt]);

  // 搜索指标
  const handleSearch = async () => {
    if (!searchValue.current) {
      return;
    }
    const res = await queryIndicator.mutateAsync(searchValue.current);
    setSearchResults(res);
  };

  const handleItemClick = (item: ItemProps) => {
    console.log(item, "handleItemClick");
    const isSelected = selectedIndicators.some(
      (indicator) => indicator.id === item.id
    );
    if (isSelected) {
      setSearchResults([]);
      return;
    } else {
      setSelectedIndicators((prev) => [...prev, item]);
      setSearchResults([]);
    }
  };

  const handleDelItem = (item: ItemProps) => {
    setSelectedIndicators((prev) =>
      prev.filter((indicator) => indicator.id !== item.id)
    );
  };

  // 提交请求，关闭弹窗，清空搜索项
  const handleCloseModal = async () => {
    setIndicatorsVisible(false);
    setSearchResults([]);
    searchValue.current = "";
    updateInfoById({
      indicators: selectedIndicators.map((item) => item.id)
    });
  };

  return (
    <div className="h-full w-full box-border flex flex-col px-10 py-5 overflow-y-auto">
      <Form form={form} layout="vertical" className="w-full h-full">
        {/* 描述 */}
        <Form.Item label="描述" name="description">
          <Input.TextArea
            placeholder="请输入"
            rows={2}
            onChange={(e) =>
              debounceChange({
                value: e.target.value,
                itemKey: "description",
                setDetailData,
                updateInfoById
              })
            }
          />
        </Form.Item>

        {/* 系统提示词 */}
        <Form.Item
          label="系统提示词"
          name="systemPrompt"
          rules={[{ required: true, message: "系统提示词未填写" }]}
        >
          <Input.TextArea
            placeholder="请输入"
            autoSize={{ minRows: 6, maxRows: 600 }}
            onChange={(e) =>
              debounceChange({
                value: e.target.value,
                itemKey: "systemPrompt",
                setDetailData,
                updateInfoById
              })
            }
          />
        </Form.Item>

        {/* 用户提示词 */}
        <Form.Item label="用户提示词" name="userPrompt">
          <Input.TextArea
            placeholder="请输入"
            autoSize={{ minRows: 6, maxRows: 600 }}
            onChange={(e) =>
              debounceChange({
                value: e.target.value,
                itemKey: "userPrompt",
                setDetailData,
                updateInfoById
              })
            }
          />
        </Form.Item>
        <div className="mb-3">关联指标</div>
        <div
          className="h-[32px] flex justify-center items-center w-full text-[#2a2a2a] hover:text-[#055AFF] cursor-pointer border-[1px] border-solid border-[#d9d9d9] hover:border-[#d9d9d9]"
          onClick={() => {
            systemPrompt && setIndicatorsVisible(true);
          }}
          style={{
            cursor: systemPrompt ? "pointer" : "not-allowed"
          }}
        >
          选择关联指标({selectedIndicators.length})
        </div>
      </Form>
      <Modal
        open={indicatorsVisible}
        footer={null}
        onCancel={handleCloseModal}
        centered={true}
        closable={false}
        styles={{
          content: {
            padding: "0px"
          },
          body: {
            padding: "16px",
            boxSizing: "border-box",
            height: "610px",
            width: "520px",
            overflowY: "auto"
          }
        }}
      >
        <div
          className="flex justify-between items-center gap-4 relative"
          ref={searchResultRef}
        >
          <Input
            placeholder="输入名称搜索"
            className="h-[32px] w-[450px]"
            suffix={
              <SearchOutlined
                style={{ color: "#999", fontSize: 16 }}
                onClick={handleSearch}
              />
            }
            onChange={(e) => {
              searchValue.current = e.target.value;
            }}
            onFocus={() => {
              if (searchValue.current) {
                handleSearch();
              }
            }}
            onPressEnter={handleSearch}
          />
          <CloseOutlined
            className="cursor-pointer"
            onClick={handleCloseModal}
          />
          {!!searchResults.length && (
            <div
              className="absolute left-0 top-[32px] bg-white w-[450px] rounded p-[16px] box-border max-h-[378px] overflow-y-auto mt-[6px]"
              style={{
                boxShadow: "0 4px 16px 0 rgba(0, 0, 0, 0.08)"
              }}
            >
              {searchResults.map((item) => (
                <SearchItem
                  key={item.id}
                  detail={item}
                  itemClick={handleItemClick}
                />
              ))}
            </div>
          )}
        </div>
        <div>
          <div className="mt-3 text-[#055AFF] mb-[14px]">
            已选择 {selectedIndicators.length} 个指标
          </div>
          {!selectedIndicators.length && (
            <div className="flex justify-center items-center">
              <img
                src={EmptyIndicator}
                alt=""
                width={500}
                className="mt-[100px]"
              />
            </div>
          )}
          {selectedIndicators.length > 0 &&
            (selectedIndicators || []).map((item) => (
              <SearchItem detail={item} delItem={handleDelItem} />
            ))}
        </div>
      </Modal>
    </div>
  );
}

export default FormContent;
