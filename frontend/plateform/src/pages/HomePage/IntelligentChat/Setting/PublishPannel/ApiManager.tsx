import { useEffect, useState, useMemo } from "react";
import {
  Table,
  Button,
  Tooltip,
  Modal,
  Form,
  Input,
  DatePicker,
  message,
  Popconfirm,
  Pagination
} from "antd";
import { Eye, EyeOff, Copy, Trash2 } from "lucide-react";
import dayjs from "dayjs";
import copy from "copy-to-clipboard";
import { getApiKeys, createKey, deleteKey } from "./service.ts";

const initialPage = {
  pageNo: 1,
  pageSize: 10,
  total: 0
};

export const ApiManager = ({
  onLatestKeyChange,
  onKeyListChange,
  agentId
}: {
  onLatestKeyChange?: (key: string | null) => void;
  onKeyListChange?: (key?: any[]) => void;
  agentId: number;
}) => {
  const [data, setData] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [showKeyIds, setShowKeyIds] = useState<string[]>([]);
  const [tableLoading, setTableLoading] = useState(false);
  const [page, setPage] = useState(initialPage);
  const [isShowKey, setIsShowKey] = useState();

  useEffect(() => {
    fetchList(initialPage);
  }, []);

  const fetchList = async (pageParam: any) => {
    try {
      setTableLoading(true);
      const param: any = {
        ...pageParam,
        targetId: agentId
      };
      const res = await getApiKeys(param);
      setTableLoading(false);
      if (res) {
        setData(res.records);
        setPage({
          pageNo: res.current,
          pageSize: res.size,
          total: res.total
        });
      }
    } catch (e) {
      setTableLoading(false);
    }
  };
  // 刷新
  const refreshList = async () => {
    await fetchList(initialPage);
  };
  // 分页
  const onPageSizeChange = (pageNo: number, pageSize: number) => {
    fetchList({
      pageNo,
      pageSize
    });
  };

  // 生成新key
  const handleCreate = async () => {
    form.validateFields().then(async (values) => {
      setLoading(true);
      const newKey = {
        targetId: values.assistId,
        expireTime: values.expireTime.format("YYYY-MM-DD HH:mm:ss")
      };
      const res = await createKey(newKey);
      if (res) {
        setModalOpen(false);
        setLoading(false);
        message.success("新 Key 已生成，请妥善保存");
        form.resetFields();
        await refreshList();
        if (onKeyListChange) onKeyListChange();
      }
    });
  };

  // 复制key
  const handleCopy = (key: string) => {
    copy(key);
    console.log("======", key);
    message.success("已复制到剪贴板");
  };

  // 查看/隐藏key
  const toggleShowKey = (id: string) => {
    setShowKeyIds((ids) =>
      ids.includes(id) ? ids.filter((i) => i !== id) : [...ids, id]
    );
  };

  // 删除key
  const handleDelete = async (id: string) => {
    const res = await deleteKey(id);
    if (res) {
      // 刷新
      await refreshList();
      message.success("Key 已删除");
      if (onKeyListChange) onKeyListChange();
    }
    // setData((data) => data.filter((k) => k.id !== id));
  };

  // 计算剩余天数
  const getExpireText = (expireTime: string) => {
    const now = dayjs();
    const exp = dayjs(expireTime);
    if (exp.isBefore(now)) return <span className="text-red-500">已过期</span>;
    const days = exp.diff(now, "day");
    return <span className="text-gray-700">剩余{days}天</span>;
  };

  const columns = [
    {
      title: "API Key",
      dataIndex: "apiKey",
      render: (text: string, record: any) => {
        const isShow = showKeyIds.includes(record.id);

        return (
          <div className="flex items-center gap-2">
            <span className="font-mono select-all">
              {text
                ? isShow
                  ? text
                  : text.slice(0, 8) + "****" + text.slice(-4)
                : ""}
            </span>
            <Tooltip
              title={isShow ? "隐藏" : "查看"}
              open={isShowKey == record.id}
            >
              <Button
                type="text"
                size="small"
                onMouseEnter={() => setIsShowKey(record.id)}
                onMouseLeave={() => setIsShowKey(undefined)}
                icon={isShow ? <EyeOff size={18} /> : <Eye size={18} />}
                onClick={() => {
                  toggleShowKey(record.id);
                  setIsShowKey(undefined);
                }}
                style={{ color: "#1677ff" }}
              />
            </Tooltip>
            <Tooltip title="复制">
              <Button
                type="text"
                size="small"
                icon={<Copy size={18} />}
                onClick={() => handleCopy(record.apiKey)}
                style={{ color: "#1677ff" }}
              />
            </Tooltip>
          </div>
        );
      }
    },
    {
      title: "到期时间",
      dataIndex: "expireTime",
      render: (text: string) => getExpireText(text)
    },
    {
      title: "操作",
      dataIndex: "action",
      render: (_: any, record: any) => (
        <Popconfirm
          title="确定删除该 Key？"
          onConfirm={() => handleDelete(record.id)}
          okText="删除"
          cancelText="取消"
        >
          <Button
            type="text"
            size="small"
            icon={<Trash2 size={18} />}
            style={{ color: "#1677ff" }}
          >
            删除
          </Button>
        </Popconfirm>
      )
    }
  ];

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <span className="font-semibold text-lg">API Key 管理</span>
        <Button
          type="primary"
          style={{ background: "#1677ff", borderColor: "#1677ff" }}
          icon={<Eye size={18} />}
          onClick={() => setModalOpen(true)}
        >
          生成新 Key
        </Button>
      </div>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        pagination={false}
        loading={tableLoading}
        size="middle"
      />
      <div className="h-[64px] flex justify-end items-center">
        <Pagination
          disabled={tableLoading}
          total={page.total}
          pageSize={page.pageSize}
          current={page.pageNo}
          showSizeChanger={false}
          onChange={onPageSizeChange}
        ></Pagination>
      </div>
      <Modal
        title="生成新 API Key"
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          form.resetFields();
          setLoading(false);
        }}
        onOk={handleCreate}
        confirmLoading={loading}
        okText="生成"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ assistId: agentId }}
        >
          <Form.Item
            label="应用ID (assistId)"
            name="assistId"
            rules={[{ required: true, message: "必填" }]}
          >
            <Input disabled />
          </Form.Item>
          <Form.Item
            label="过期时间"
            name="expireTime"
            rules={[{ required: true, message: "请选择过期时间" }]}
          >
            <DatePicker
              showTime
              format="YYYY-MM-DD HH:mm"
              style={{ width: "100%" }}
              showNow={false}
              disabledDate={(current) => {
                // Can not select days before today and today
                return current && current <= dayjs().endOf("hours");
              }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
