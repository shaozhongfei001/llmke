import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";
import { Empty, Table, Pagination } from "antd";
import { useEffect, useState } from "react";

const DATA_DEMO = [
  {
    dataSourceType: "DataTable",
    databaseId: 201,
    databaseName: "数据库问答",
    fetchUrl: "/index/database/dataTable/queryTableFileData/931",
    fileId: 931,
    tableName: "tools_table_459",
    total: 17
  }
];

const DrawerDatabase = ({ curFileInfo }: any) => {
  const [pageNo, setPageNo] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [columns, setColumn] = useState([]);
  const [dataList, setDataList] = useState([]);
  const [totalData, setTotalData] = useState(0);

  useEffect(() => {
    const url = curFileInfo?.metadata?.fetchUrl || curFileInfo?.fetchUrl;
    if (url) {
      toGetDataBaseData(url);
    }
  }, [curFileInfo, pageNo, pageSize]);

  const getDataBaseData = async ({ url, params }: any) => {
    try {
      const res = await axios$.get(
        `${getUrlPrefix()}${url}?${new URLSearchParams(params).toString()}`
      );
      const data = res?.data;
      if (data) {
        const { columns, dataList, totalData } = data;
        setColumn(
          (columns?.slice(1) || []).map((col: any) => ({
            title: col.businessName,
            dataIndex: col.physicalName,
            key: col.physicalName
          }))
        );
        setDataList(dataList || []);
        setTotalData(totalData || []);
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  const toGetDataBaseData = async (url: string) => {
    getDataBaseData({
      url: `${url}`,
      params: {
        pageNo,
        pageSize
      }
    });
  };

  const renderTitle = () => {
    const { file, metadata } = curFileInfo;
    const { dataSourceType, databaseName, tableName, businessTableName } =
      metadata;
    if (dataSourceType == "DataTable") {
      return `${databaseName} - ${businessTableName}`;
    }

    if (dataSourceType == "DirectDB") {
      return `${databaseName} - ${tableName}`;
    }

    return file;
  };

  return (
    <div>
      <div className="h-[52px] leading-[52px] font-bold text-[16px] px-[15px] overflow-hidden border-t-none border-l-none border-b-[1px] border-solid border-[rgb(222,226,230)]">
        {renderTitle()}
      </div>

      {columns?.length > 0 ? (
        <div>
          <div className="p-4 overflow-auto h-[calc(100vh-120px)]">
            <Table
              columns={columns}
              dataSource={dataList}
              pagination={false}
              scroll={{ x: "max-content" }}
            />
          </div>
          <div className="flex justify-end px-[18px]">
            <Pagination
              current={pageNo}
              pageSize={pageSize}
              responsive
              simple
              total={totalData}
              showSizeChanger
              showQuickJumper
              onChange={(page, size) => {
                setPageNo(page);
                setPageSize(size || 10);
              }}
              onShowSizeChange={(current, size) => {
                setPageNo(1);
                setPageSize(size);
              }}
            />
          </div>
        </div>
      ) : (
        <Empty />
      )}
    </div>
  );
};

export default DrawerDatabase;
