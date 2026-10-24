import {
  BetaSchemaForm,
  ProFormColumnsType,
  SubmitterProps
} from "@ant-design/pro-form";
import { useImperativeHandle, useMemo, useRef } from "react";
import { TypeToValueType } from "./constant";

interface FormData {
  dataIndex: string;
  title: string;
  required: boolean;
  type: "string" | "int" | "number";
  width?: number | "sm" | "md" | "xl" | "xs" | "lg";
  [key: string]: any;
}

interface SchemaFormI {
  formData: FormData;
  submitter?: false | SubmitterProps;
  onref: any;
}

type DataItem = {
  name: string;
  state: string;
};

const CreateSchemaForm = (props: SchemaFormI) => {
  const formRef: any = useRef();
  const { formData, submitter = false, onref } = props;

  useImperativeHandle(onref, () => ({
    toSubmit: async () => {
      const val1 = await formRef.current?.validateFieldsReturnFormatValue?.();
      return val1;
    },
    getFormRef: () => {
      return formRef;
    }
  }));

  const columns: ProFormColumnsType<DataItem>[] = useMemo(() => {
    return formData.map((item: FormData) => {
      const p: any = {
        ...item,
        key: item.dataIndex,
        valueType: TypeToValueType[item.type],
        formItemProps: {
          rules: [
            {
              required: item.required,
              message: `${item.title}为必填项`
            }
          ]
        },
        width: "100%"
      };
      if (item.type === "int") {
        p.fieldProps = { precision: 0 };
      }
      return p;
    });
  }, [formData]);

  return (
    <BetaSchemaForm<DataItem>
      formRef={formRef}
      submitter={submitter}
      onFinish={async (values) => {
        console.log(values);
      }}
      columns={columns}
    />
  );
};

export default CreateSchemaForm;
