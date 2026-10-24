import { Button, Input, Pagination, Popconfirm, Table, Tag } from "antd";
import "@/assets/styles/knowledgebase.less";
import {
  InfoCircleFilled,
  PlusCircleOutlined,
  PlusOutlined,
  SearchOutlined
} from "@ant-design/icons";
import dayjs from "dayjs";
import CreateModal from "./components/createModal";
import { useSensitiveTableController } from "./useSensitiveTableController";

const FLAT_BREAD_CRUMB = [
  {
    href: "/chats",
    title: "智能会话"
  },
  {
    title: "敏感词配置"
  }
];
const SensitiveWords = ({ title }: any) => {
  const tableProps: any = useSensitiveTableController();

  return (
    <div className="h-full">
      <div className="px-[20px] pt-[20px] h-[calc(100%-76px)] overflow-auto bg-white rounded-[8px]">
        <div className={`search-bar flex justify-between mb-[20px]`}>
          <Button
            type="primary"
            icon={<PlusCircleOutlined />}
            className="w-[80px] border-none"
            style={{ background: "linear-gradient(90deg,#075BFF,#AC96FF)" }}
            onClick={() => {
              tableProps.setOpenType("add");
              tableProps.setShowCreateModal(true);
            }}
          >
            新建
          </Button>
          <Input
            // allowClear
            value={tableProps.fuzzyNameOrId}
            placeholder="请输入内容"
            style={{ width: "240px" }}
            suffix={
              <SearchOutlined
                style={{ color: "#999", fontSize: 12 }}
                onClick={() => tableProps.handleSearch()}
              />
            }
            onChange={tableProps.fuzzyNameOrIdOnChange}
            onKeyDown={tableProps.handleKeyDown}
          />
        </div>
        <SensitiveTable {...tableProps} />
      </div>
      <CreateModal
        showCreateModal={tableProps.showCreateModal}
        setShowCreateModal={tableProps.setShowCreateModal}
        type={tableProps.openType}
        data={tableProps.editData}
        loading={tableProps.modalConfirmLoading}
        cb={(data: any) => tableProps.handleEvent("createOrEdit", data)}
      />
    </div>
  );
};

export default SensitiveWords;

const SensitiveTable = ({
  listCount,
  deleteByIds,
  page,
  onPageSizeChange,
  tableList,
  tableLoading,
  handleEvent
}: any) => {
  const columns = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      width: 200,
      ellipsis: true
    },
    {
      title: "敏感词",
      dataIndex: "words",
      key: "words",
      ellipsis: true,
      render: (_: any, r: any) => {
        return _
          ? _.map((text: string, index: number) => {
              return (
                <Tag
                  bordered={false}
                  className="text-[#2A2A2A] bg-[#FAFAFA]"
                  key={index}
                >
                  {text}
                </Tag>
              );
            })
          : "-";
      }
    },
    {
      title: "创建日期",
      dataIndex: "gmtCreate",
      width: 180,
      render: (_: any, r: any) => {
        return r.gmtCreate
          ? dayjs(r.gmtCreate).format("YYYY-MM-DD HH:mm")
          : "-";
      }
    },
    {
      title: "数量",
      dataIndex: "count",
      key: "count",
      width: 100
    },
    {
      title: "操作",
      dataIndex: "operations",
      key: "operations",
      width: 150,
      render: (_: any, record: any) => {
        return (
          <>
            <div className="table-btn-group-wrap">
              <Button
                type="link"
                title="编辑"
                size={"small"}
                onClick={() => handleEvent("detail", record)}
              >
                编辑
              </Button>
              <Popconfirm
                title="删除"
                description="确认删除该敏感词库吗？"
                okText="确认"
                cancelText="取消"
                onConfirm={() => deleteByIds([record.id])}
              >
                <Button
                  type="link"
                  title="删除"
                  style={{ cursor: "pointer" }}
                  size={"small"}
                >
                  删除
                </Button>
              </Popconfirm>
            </div>
          </>
        );
      }
    }
  ];

  return (
    <>
      <div className="h-[calc(100%-56px)] overflow-auto pb-[10px]">
        <Table
          size="small"
          columns={columns}
          dataSource={tableList}
          pagination={false}
          rowKey={(record: any) => record.id}
          loading={tableLoading}
        />
        <Pagination
          className="mt-[16px]"
          align="end"
          disabled={tableLoading}
          total={listCount}
          pageSize={page.pageSize}
          current={page.pageNo}
          onChange={onPageSizeChange}
          showSizeChanger={false}
        ></Pagination>
      </div>
      {/* <div className="h-[64px] flex justify-end items-center"></div> */}
    </>
  );
};
