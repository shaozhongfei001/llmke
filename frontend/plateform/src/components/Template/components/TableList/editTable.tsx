import { Select, Form, Input, Table, Switch, DatePicker, Tag } from "antd";
import React, { useContext, useEffect, useRef, useState } from "react";
import type { GetRef, InputRef } from "antd";
import { useSortable } from "@dnd-kit/sortable";
import { TypeOptions } from "../../core/constants";
import { InitCount } from "../../core/useStateStore";
type FormInstance<T> = GetRef<typeof Form<T>>;

interface Item {
  key: number;
  dataIndex: string;
  title: string;
  required: boolean;
  type: string;
  defaultValue: string | string[] | undefined;
}

const EditableContext = React.createContext<FormInstance<any> | null>(null);
export interface DataType {
  key: number | string;
  dataIndex: string;
  title: string;
  required: boolean;
  type: string;
}

type EditableTableProps = Parameters<typeof Table>[0];
export type ColumnTypes = Exclude<EditableTableProps["columns"], undefined>;
interface EditableCellProps {
  title: React.ReactNode;
  editable: boolean;
  dataIndex: keyof Item;
  record: Item;
  form: any;
  handleSave: (record: Item) => void;
}

interface EditableRowProps {
  index: number;
}

export const EditableCell: React.FC<
  React.PropsWithChildren<EditableCellProps>
> = ({
  title,
  editable,
  children,
  dataIndex,
  record,
  handleSave,
  ...restProps
}) => {
  const [editing, setEditing] = useState(false);
  const inputRef = useRef<InputRef>(null);
  const form = useContext(EditableContext)!;

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
    }
  }, [editing]);

  const getW = () => {
    switch (dataIndex) {
      case "required":
        return "44px";
      case "type":
        return "100px";
      default:
        return "auto";
    }
  };

  const toggleEdit = () => {
    if (record.key !== InitCount) {
      setEditing(!editing);
    } else {
      if (dataIndex == "title" || dataIndex == "defaultValue") {
        setEditing(!editing);
      }
    }

    form.setFieldsValue({ [dataIndex]: record[dataIndex] });
  };

  const renderFormItem = (dataIndex: string) => {
    if (dataIndex === "required") {
      form.setFieldsValue({ required: record[dataIndex] });
    }

    switch (dataIndex) {
      case "required":
        return <Switch onChange={save} disabled={record.key === InitCount} />;
      case "type":
        return <Select options={TypeOptions} onSelect={save} />;
      case "defaultValue": {
        if (record.type == "select") {
          return (
            <Select
              mode="tags"
              placeholder="请输入可选项"
              onBlur={save}
              onChange={save}
              options={[]}
            />
          );
        }
        // if (record.type == "date") {
        //   return <DatePicker onChange={save} />;
        // }
        return <Input ref={inputRef} onPressEnter={save} onBlur={save} />;
      }
      default:
        return <Input ref={inputRef} onPressEnter={save} onBlur={save} />;
    }
  };

  const save = async () => {
    try {
      const values = await form.validateFields();
      if (dataIndex !== "required") {
        toggleEdit();
      } else {
        form.setFieldsValue({ [dataIndex]: values[dataIndex] });
      }
      if (values?.type && values?.type !== record.type) {
        delete record.defaultValue;
      }
      handleSave({ ...record, ...values });
    } catch (errInfo) {
      console.log("Save failed:", errInfo);
    }
  };

  let childNode = children;

  if (dataIndex === "required") {
    childNode = (
      <Form.Item style={{ margin: 0 }} name={dataIndex}>
        {renderFormItem(dataIndex)}
      </Form.Item>
    );
  } else if (editable) {
    childNode = editing ? (
      <Form.Item style={{ margin: 0 }} name={dataIndex}>
        {renderFormItem(dataIndex)}
      </Form.Item>
    ) : (
      <div
        className={`text-ellipsis whitespace-nowrap break-words overflow-hidden px-[11px] leading-[32px] h-[32px] border-[1px] border-solid border-transparent ${record.key === InitCount && !["title", "defaultValue"].includes(dataIndex) ? "cursor-not-allowed" : "hover:border-[rgba(0,0,0,.05)] cursor-pointer"}`}
        style={{ minWidth: getW(), paddingInlineEnd: 24 }}
        onClick={toggleEdit}
      >
        {record.type == "select" && dataIndex == "defaultValue"
          ? Array.isArray(record.defaultValue) && record.defaultValue.join(",")
          : children}
      </div>
    );
  }

  return <td {...restProps}>{childNode}</td>;
};

export const EditableRow: React.FC<EditableRowProps> = ({
  index,
  ...props
}: any) => {
  const [form] = Form.useForm();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({
    id: props["data-row-key"]
  });

  // const style: React.CSSProperties = {
  //   ...props.style,
  //   transform: CSS.Translate.toString(transform),
  //   transition,
  //   cursor: 'move',
  //   ...(isDragging ? { position: 'relative', zIndex: 9999 } : {}),
  // };
  return (
    <Form
      form={form}
      component={false}
      initialValues={{ type: "string", required: false }}
    >
      <EditableContext.Provider value={form}>
        <tr {...props} ref={setNodeRef} {...attributes} {...listeners} />
      </EditableContext.Provider>
    </Form>
  );
};
