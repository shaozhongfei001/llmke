import React, { useEffect, useState } from "react";
import type { TableProps } from "antd";
import {
  Button,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Table,
  Typography
} from "antd";
import { TableRowSelection } from "antd/es/table/interface";
import { CheckOutlined, CloseOutlined } from "@ant-design/icons";
import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";
interface DataType {
  key: string;
  similarQuestion: string;
  add?: boolean;
  first?: boolean;
}

interface EditableCellProps extends React.HTMLAttributes<HTMLElement> {
  editing: boolean;
  similarLoading: string;
  dataIndex: string;
  title: any;
  inputType: "number" | "text";
  record: DataType;
  index: number;
  save: (arg: any) => void;
  cancel: (arg: any) => void;
}

const EditableCell: React.FC<React.PropsWithChildren<EditableCellProps>> = ({
  editing,
  dataIndex,
  title,
  inputType,
  record,
  index,
  children,
  save,
  cancel,
  similarLoading,
  ...restProps
}) => {
  const inputNode =
    inputType === "number" ? <InputNumber /> : <Input className="w-[518px]" />;

  return (
    <td {...restProps}>
      {editing ? (
        <div className="flex w-full">
          <Form.Item
            name={dataIndex}
            style={{ margin: 0 }}
            rules={[
              {
                required: true,
                message: `请输入${title}!`
              }
            ]}
          >
            {inputNode}
          </Form.Item>
          <div className="flex ml-[12px]">
            <Button
              style={{
                background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
                color: "#fff",
                marginRight: "12px",
                border: "none"
              }}
              icon={<CheckOutlined />}
              loading={similarLoading === "save"}
              onClick={() => save(record.key)}
            />
            <Button
              style={{
                background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
                color: "#fff",
                border: "none"
              }}
              icon={<CloseOutlined />}
              onClick={() => cancel(record.key)}
            />
          </div>
        </div>
      ) : (
        children
      )}
    </td>
  );
};

const EditSimilarTable = ({
  data,
  similarLoading,
  submitAddSimilar,
  deleteSimilarConfirm,
  submitUpdateSimilar,
  tableLoading,
  selectedRowKeys,
  setSelectedRowKeys,
  kbInfo,
  setData
}: any) => {
  useEffect(() => {
    console.log("datadatadata", data);

    if (!data.length) {
      setEditingKey("");
    }
  }, [data]);
  const [form] = Form.useForm();
  const [editingKey, setEditingKey] = useState("");
  const isEditing = (record: DataType) => record.key === editingKey;

  const edit = (record: Partial<DataType> & { key: React.Key }) => {
    form.setFieldsValue({ similarQuestion: "", ...record });
    setEditingKey(record.key);
  };

  const cancel = async (key: string) => {
    const similarQuestion = form.getFieldValue("similarQuestion");
    if (key.indexOf("add_") > -1 && !similarQuestion) {
      setData((pre: any) => {
        return pre.filter((item: any) => item.key !== key);
      });
    }
    setEditingKey("");
  };

  const save = async (key: React.Key) => {
    try {
      const row = (await form.validateFields()) as DataType;
      const success = () => {
        setEditingKey("");
      };
      (key as any).indexOf("add_") > -1
        ? submitAddSimilar(row.similarQuestion, success)
        : submitUpdateSimilar(
            { similarQuestion: row.similarQuestion, pk: key },
            success
          );
    } catch (errInfo) {
      console.log("Validate Failed:", errInfo);
    }
  };

  const columns = [
    {
      title: "问题",
      dataIndex: "similarQuestion",
      editable: true,
      ellipsis: true
    },
    {
      title: "操作",
      width: "120px",
      dataIndex: "operation",
      render: (_: any, record: DataType) => {
        const editable = isEditing(record);
        if (record.first) {
          edit(record);
          delete record.first;
        }
        return (
          <>
            <Typography.Link
              disabled={
                editingKey !== "" ||
                getBtnDisabled(FILE_BTN.EDIT, kbInfo.permission)
              }
              onClick={() => edit(record)}
              className="mr-[8px]"
            >
              修改
            </Typography.Link>{" "}
            <Popconfirm
              title="删除相似问"
              disabled={similarLoading === "del"}
              description="确认删除相似问吗？"
              okText="确认"
              cancelText="取消"
              placement="topLeft"
              onConfirm={() => deleteSimilarConfirm([record.key])}
            >
              <Typography.Link
                disabled={
                  editingKey !== "" ||
                  getBtnDisabled(FILE_BTN.DELETE, kbInfo.permission)
                }
              >
                删除
              </Typography.Link>
            </Popconfirm>
          </>
        );
      }
    }
  ];

  const mergedColumns: TableProps<DataType>["columns"] = columns.map((col) => {
    if (!col.editable) {
      return col;
    }
    return {
      ...col,
      onCell: (record: DataType) => ({
        record,
        inputType: "text",
        dataIndex: col.dataIndex,
        title: col.title,
        editing: isEditing(record),
        save,
        cancel,
        similarLoading
      })
    };
  });
  const onSelectChange = (newSelectedRowKeys: React.Key[], b: any) => {
    console.log("selectedRowKeys changed: ", newSelectedRowKeys);
    setSelectedRowKeys(newSelectedRowKeys);
  };
  const rowSelection: TableRowSelection<DataType> = {
    selectedRowKeys,
    onChange: onSelectChange
  };
  return (
    <Form form={form} component={false}>
      <Table<DataType>
        components={{
          body: { cell: EditableCell }
        }}
        dataSource={data}
        columns={mergedColumns}
        rowClassName="editable-row"
        pagination={false}
        rowSelection={rowSelection}
        loading={tableLoading || !!similarLoading}
      />
    </Form>
  );
};

export default EditSimilarTable;
