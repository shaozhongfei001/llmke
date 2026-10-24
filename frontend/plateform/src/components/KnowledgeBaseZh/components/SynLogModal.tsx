import { useEffect, useState } from "react";
import { Table } from "antd";
import { CaretDownOutlined, CaretRightOutlined } from "@ant-design/icons";
import "@/assets/styles/knowledgebase.less";
import { useServices } from "../service";
interface ISynLog {
  row: any;
}

const SynLog = ({ row }: ISynLog) => {
  const { getSynLog } = useServices("rag-qa");
  const [curRow, setCurRow] = useState([]);
  const [expandedRowKeys, setExpandedRowKeys] = useState<any[]>([]);
  const columns = [
    {
      title: "ID",
      dataIndex: "id",
      key: "id",
      width: 80
    },
    {
      title: "知识库ID",
      dataIndex: "kbId",
      width: 120,
      key: "kbId"
    },
    {
      title: "文件ID",
      dataIndex: "targetId",
      width: 120,
      key: "targetId"
    },
    {
      title: "日志类型",
      dataIndex: "logType",
      width: 120,
      key: "logType",
      render: (_: any) => {
        return _ == 1 ? "文件解析" : "FAQ抽取";
      }
    },
    {
      title: "错误码",
      dataIndex: "errorCode",
      width: 120,
      key: "errorCode"
    }
  ];

  const hanldeRowExpand = (expanded: boolean, record: any) => {
    setExpandedRowKeys((prevKeys) =>
      expanded
        ? [...prevKeys, record.id]
        : prevKeys.filter((key) => key !== record.id)
    );
  };

  const getList = async () => {
    try {
      const res: any = await getSynLog({ fileId: row.fileId });
      if (res?.records) {
        setCurRow(res.records.map((item: any) => ({ ...item, key: item.id })));
      }
    } catch (error) {}
  };

  useEffect(() => {
    if (row?.fileId) {
      getList();
    }
  }, [row]);

  return (
    <Table
      columns={columns}
      dataSource={curRow}
      pagination={{ pageSize: 10 }}
      expandable={{
        expandedRowKeys,
        onExpand: hanldeRowExpand,
        expandedRowRender: (record: any) => {
          return (
            <div className="expand-info">
              <div className="info-row">
                <div className="label">错误消息：</div>
                <div className="text">{record.errorMessage || "-"}</div>
              </div>
              <div className="info-row">
                <div className="label">错误详情：</div>
                <div className="text">{record.errorDetail || "-"}</div>
              </div>
            </div>
          );
        },
        expandIcon: ({ expanded, onExpand, record }: any) =>
          expanded ? (
            <CaretDownOutlined onClick={(e) => onExpand(record, e)} />
          ) : (
            <CaretRightOutlined onClick={(e) => onExpand(record, e)} />
          )
      }}
    />
  );
};

export default SynLog;
