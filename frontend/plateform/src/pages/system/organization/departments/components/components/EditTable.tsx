import React, { useState } from "react";
import type { TableProps } from "antd";
import {
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Select,
  Table,
  Typography
} from "antd";
import { EditOutlined } from "@ant-design/icons";

interface DataType {
  key: string;
  name: string;
  age: number;
  address: string;
}

interface EditableCellProps extends React.HTMLAttributes<HTMLElement> {
  editing: boolean;
  dataIndex: string;
  title: any;
  inputType: "number" | "text";
  record: any;
  index: number;
  save: any;
  options: any;
  handleSearch: (arg: string) => void;
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
  options,
  handleSearch,
  ...restProps
}) => {
  const inputNode =
    inputType === "number" ? (
      <InputNumber />
    ) : (
      <Select
        options={options}
        onBlur={() => save(record.id)}
        fieldNames={{ label: "userRealname", value: "id" }}
        showSearch
        filterOption={(input, option) => {
          return (
            (option?.userEmail ?? ("" as any))
              .toLowerCase()
              .includes(input.toLowerCase()) ||
            (option?.userRealname ?? ("" as any))
              .toLowerCase()
              .includes(input.toLowerCase())
          );
        }}
      />
    );

  return (
    <td {...restProps}>
      {editing ? (
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
      ) : (
        children
      )}
    </td>
  );
};

const ResourceTable = ({ data, setData, form, options, loading }: any) => {
  const [editingKey, setEditingKey] = useState("");

  const isEditing = (record: any) => record.id === editingKey;

  const edit = (record: Partial<any> & { key: React.Key }) => {
    form.setFieldsValue({ name: "", age: "", address: "", ...record });
    setEditingKey(record.id);
  };

  const cancel = () => {
    setEditingKey("");
  };

  const save = async (key: React.Key) => {
    try {
      const row = (await form.validateFields()) as DataType;
      const newData = [...data];
      const index = newData.findIndex((item) => key === item.id);
      if (index > -1) {
        const item = newData[index];
        newData.splice(index, 1, {
          ...item,
          ...row
        });
        setData(newData);
        setEditingKey("");
      } else {
        newData.push(row);
        setData(newData);
        setEditingKey("");
      }
    } catch (errInfo) {
      console.log("Validate Failed:", errInfo);
    }
  };

  const columns = [
    {
      title: "资源",
      dataIndex: "resource",
      width: "20%",
      editable: false
    },
    {
      title: "描述",
      dataIndex: "description",
      width: "30%",
      editable: false
    },
    {
      title: "接收方",
      dataIndex: "userId",
      width: "40%",
      editable: true,
      render: (_: any) => {
        const cur = (options || []).find((item: any) => item.id === _);
        return cur?.userRealname;
      }
    },
    {
      title: "",
      width: "10%",
      dataIndex: "operation",
      render: (_: any, record: DataType) => {
        const editable = isEditing(record);
        return editable ? (
          <span>
            {/* <Typography.Link
              onClick={() => save(record.id)}
              style={{ marginInlineEnd: 8 }}
            >
              Save
            </Typography.Link>
            <Popconfirm title="Sure to cancel?" onConfirm={cancel}>
              <a>Cancel</a>
            </Popconfirm> */}
          </span>
        ) : (
          // <Typography.Link
          //   disabled={editingKey !== ""}
          //   onClick={() => edit(record)}
          // >
          //   Edit
          // </Typography.Link>
          <EditOutlined
            disabled={editingKey !== ""}
            onClick={() => edit(record)}
          />
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
        inputType: col.dataIndex === "age" ? "number" : "text",
        dataIndex: col.dataIndex,
        title: col.title,
        editing: isEditing(record),
        save,
        options
      })
    };
  });

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
        rowKey="id"
        loading={loading}
      />
    </Form>
  );
};

export default ResourceTable;
