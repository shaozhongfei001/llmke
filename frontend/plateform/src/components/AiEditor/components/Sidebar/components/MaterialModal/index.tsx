import { useEffect, useMemo, useState } from "react";

import { Item, MaterialCard } from "../MaterialCard";
import { Flex, Modal, Input, Button, message } from "antd";
import empty from "@/components/AiEditor/assets/img/empty.png";
import { Loading } from "../../../Loading";
import { CustomizedTitle } from "../../../CustomizedTitle";
import { api_getArticleMaterialList } from "@/components/AiEditor/core/services/servers";
import { useStateStore } from "@/components/AiEditor/core/states/useStateStore";
const { Search } = Input;

export const MaterialModal = ({
  open,
  closeMaterial,
  confirmSelect,
  contentSources,
  selectMaterialList,
  setSelectMaterialList,
}) => {
  const { serverInfo } = useStateStore();
  // 所有的文章列表
  const [materialList, setMaterialList] = useState<Item[]>([]);

  const [getMaterialLoading, setGetMaterialLoading] = useState<boolean>(false);

  useEffect(() => {
    if (contentSources && contentSources.length !== 0) {
      const { refIds, refNames } = contentSources[0];
      const list = refIds.map((i, index) => ({
        id: Number(i),
        fileName: refNames[index],
        fileSuffix: refNames[index].split(".")[1],
      }));
      setSelectMaterialList(list);
    }
  }, [contentSources]);

  const getArticleMaterial = async (searchValue = "") => {
    setGetMaterialLoading(true);
    const res = await api_getArticleMaterialList({
      data: {
        fileName: searchValue,
        pageSize: 999,
        pageNo: 1,
        state: 3,
      },
      config: serverInfo,
    });
    setGetMaterialLoading(false);
    const { details } = res;
    if (selectMaterialList.length) {
      const selectId = selectMaterialList.map((i) => i.id);
      setMaterialList((details || []).filter((i) => !selectId.includes(i.id)));
    } else {
      {
        setMaterialList(details || []);
      }
    }
  };

  const [searchValue, setSearchValue] = useState<string>("");
  useEffect(() => {
    if (!open) return;
    getArticleMaterial(searchValue);
  }, [searchValue, open]);

  // 上一次选中的素材列表，用于制作取消功能
  const preMaterialList = useMemo(() => {
    if (!open) return [];
    return selectMaterialList;
  }, [open]);

  const handleSearch = (value) => {
    if (value === searchValue) return;
    setSearchValue(value);
  };

  const handleClick = ({ type, item }) => {
    if (type === "add") {
      if (selectMaterialList.length === 10) {
        message.warning("最多添加10个素材");
        return;
      }
      setSelectMaterialList((p) => [...p, item]);
      setMaterialList((p) => p.filter((i) => i.id !== item.id));
    } else {
      setSelectMaterialList((p) => p.filter((i) => i.id !== item.id));
      setMaterialList((p) => [...p, item]);
    }
  };

  const handleCancel = () => {
    setSelectMaterialList(preMaterialList);
    closeMaterial();
  };

  const handleOk = () => {
    confirmSelect(selectMaterialList);
    closeMaterial();
  };

  const Footer = () => {
    return (
      <Flex justify="center" align="center">
        <Flex gap={16}>
          <Button type="primary" ghost onClick={handleCancel}>
            取消
          </Button>
          <Button type="primary" onClick={handleOk}>
            确认
          </Button>
        </Flex>
      </Flex>
    );
  };
  return (
    <>
      <Modal
        title="自定义素材"
        open={open}
        footer={Footer}
        width={"80vw"}
        onCancel={handleCancel}
        style={{
          minWidth: "1000px",
        }}
      >
        <Flex
          justify="space-between"
          gap={30}
          className="box-border min-h-[500px] h-[60vh]"
        >
          <Flex vertical={true} className="w-1/2 h-full">
            <CustomizedTitle text="素材库" />
            <Search
              placeholder="输入文件名搜索"
              className="mt-[12px]"
              style={{ width: "240px" }}
              onSearch={handleSearch}
            />
            {getMaterialLoading && <Loading></Loading>}
            {materialList.length === 0 && !getMaterialLoading && (
              <Flex vertical={true} flex={1} justify="center" align="center">
                <img src={empty} width={106} />
                <span className="text-[#333] mt-[10px]">暂无数据</span>
              </Flex>
            )}
            {materialList.length !== 0 && !getMaterialLoading && (
              <Flex
                wrap={"wrap"}
                gap={30}
                flex={1}
                className="my-[12px] overflow-y-auto content-start flex-wrap"
              >
                {materialList.map((item) => (
                  <MaterialCard
                    item={item}
                    key={item.id}
                    type="add"
                    itemClick={handleClick}
                  />
                ))}
              </Flex>
            )}
          </Flex>
          <Flex vertical={true} wrap={"wrap"} className="w-1/2 h-full">
            <CustomizedTitle text="已选文章" />
            {selectMaterialList.length === 0 && (
              <Flex vertical={true} flex={1} justify="center" align="center">
                <img src={empty} width={106} />
                <span className="text-[#333] mt-[10px]">暂无数据</span>
              </Flex>
            )}
            {selectMaterialList.length !== 0 && (
              <Flex
                wrap={"wrap"}
                gap={30}
                flex={1}
                className="my-[12px] overflow-y-auto content-start flex-wrap"
              >
                {selectMaterialList.map((item) => (
                  <MaterialCard
                    item={item}
                    key={item.id}
                    type="del"
                    itemClick={handleClick}
                  />
                ))}
              </Flex>
            )}
          </Flex>
        </Flex>
      </Modal>
    </>
  );
};
