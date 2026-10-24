import { Button, Input, Pagination, Popconfirm, Table, Tag } from "antd";
import "@/assets/styles/knowledgebase.less";
import {
  InfoCircleFilled,
  PlusCircleOutlined,
  PlusOutlined,
  SearchOutlined
} from "@ant-design/icons";
import { useSensitiveTableController } from "./common/useSensitiveTableController";
import dayjs from "dayjs";
import CreateModal from "./common/components/createModal";
import { formatTime } from "@root/src/core/helps";

const SensitiveWords = () => {
  const tableProps: any = useSensitiveTableController();
  return (
    <div className="h-full">
      <MainPage tableProps={tableProps} />
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

const MainPage = ({ tableProps }: any) => {
  return (
    <>
      <div className="flex items-center justify-between  pb-[20px]">
        <div className="flex items-center">
          <div className="text-[16px] text-text-color1 font-bold">
            敏感词配置
          </div>
        </div>
      </div>
      <div className="px-[20px] pt-[20px] h-[calc(100%-76px)] overflow-auto bg-white rounded-[8px]">
        <div className={`search-bar flex justify-between mb-[20px]`}>
          <Button
            type="primary"
            icon={<PlusCircleOutlined />}
            className="w-[138px] border-none"
            style={{ background: "linear-gradient(90deg,#075BFF,#AC96FF)" }}
            onClick={() => {
              tableProps.setOpenType("add");
              tableProps.setShowCreateModal(true);
            }}
          >
            新建敏感词库
          </Button>
          <Input
            // allowClear
            value={tableProps.fuzzyNameOrId}
            placeholder="请输入内容"
            style={{ width: "240px" }}
            suffix={
              <SearchOutlined
                style={{ color: "#999", fontSize: 12 }}
                onClick={() => tableProps.fetchList()}
              />
            }
            onChange={tableProps.fuzzyNameOrIdOnChange}
            onKeyDown={tableProps.handleKeyDown}
          />
        </div>
        <SensitiveTable {...tableProps} />
      </div>
    </>
  );
};

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
                <Tag bordered={false} color="processing" key={index}>
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
        return r.gmtCreate ? formatTime(r.gmtCreate) : "-";
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
      <div className="h-[calc(100%-116px)] overflow-auto nlp-setting-list-table">
        <Table
          columns={columns}
          dataSource={tableList}
          pagination={false}
          rowKey={(record: any) => record.id}
          loading={tableLoading}
        />
      </div>
      <div className="h-[64px] flex justify-end items-center">
        <Pagination
          disabled={tableLoading}
          total={listCount}
          pageSize={page.pageSize}
          current={page.pageNo}
          showSizeChanger={false}
          // showQuickJumper
          onChange={onPageSizeChange}
        ></Pagination>
      </div>
    </>
  );
};
