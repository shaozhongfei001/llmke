import { PlusCircleOutlined, SearchOutlined } from "@ant-design/icons";
import { PrimaryBtn } from "../../../common/components/PrimaryBtn";
import { Input, Pagination, Spin } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import "./style.less";
import DatabaseCard from "@/pages/HomePage/Writing/common/components/Cards/DataBaseCard/index";
import AddTable from "./AddTable";
import { useServices } from "./service";
import { useQuery } from "@tanstack/react-query";

const Database = () => {
  const { getDbList } = useServices();

  const searchValueRef = useRef<string>("");
  const [searchWord, setSearchWord] = useState<string>("");
  const [queryDbListParams, setQueryDbListParams] = useState({
    pageNo: 1,
    pageSize: 12
  });
  const queryDbList = useQuery({
    queryKey: [queryDbListParams.pageNo, searchWord],
    queryFn: () =>
      getDbList({
        searchWord,
        pageNo: queryDbListParams.pageNo,
        pageSize: queryDbListParams.pageSize
      }),
    enabled: !!queryDbListParams.pageNo || !!queryDbListParams.pageNo
  });

  const dbList = useMemo(() => {
    return (queryDbList?.data || {})?.details || [];
  }, [queryDbList?.data]);

  const [openModal, setOpenModal] = useState<boolean | "init">("init");

  const createTable = () => setOpenModal(!openModal);

  const onSearch = (value: string) => {
    setSearchWord(value);
  };

  return (
    <>
      <AddTable openModal={openModal} queryDbList={queryDbList} />
      <div className="py-4 px-5">
        <header className="flex justify-between align-middle mb-4">
          <PrimaryBtn onClick={createTable}>
            <PlusCircleOutlined />
            添加
          </PrimaryBtn>
          <Input
            placeholder="输入名称搜索"
            className="w-[240px] h-[32px]"
            suffix={
              <SearchOutlined
                style={{ color: "#999", fontSize: 16 }}
                onClick={() => onSearch(searchValueRef.current)}
              />
            }
            onChange={(e) => {
              searchValueRef.current = e.target.value;
            }}
            onPressEnter={() => onSearch(searchValueRef.current)}
          />
        </header>
        <Spin spinning={queryDbList.isLoading}>
          <section className="h-[calc(100vh-320px)] overflow-y-auto">
            <div className="card-container">
              {(dbList || []).map((item: any) => {
                return (
                  <DatabaseCard
                    key={item.id}
                    item={item}
                    queryDbList={queryDbList}
                  />
                );
              })}
            </div>
          </section>
          <Pagination
            className="mt-[16px]"
            align="end"
            total={queryDbList?.data?.totalCount || 0}
            pageSize={queryDbListParams.pageSize}
            current={queryDbListParams.pageNo}
            onChange={(page) => {
              setQueryDbListParams({ ...queryDbListParams, pageNo: page });
            }}
            showSizeChanger={false}
          />
        </Spin>
      </div>
    </>
  );
};
export default Database;
