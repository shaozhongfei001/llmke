import {
  Button,
  Checkbox,
  CheckboxChangeEvent,
  Form,
  FormInstance,
  Input,
  message,
  Modal,
  Select
} from "antd";
import { useEffect, useMemo, useState } from "react";
import { PrimaryBtn } from "../../../common/components/PrimaryBtn";
import "./style.less";
import { useServices } from "./service";
import { UseQueryResult } from "@tanstack/react-query";
import mysqlIcon from "@/assets/svg/mysql.svg";
import mongoIcon from "@/assets/svg/mongo.svg";
import defaultDbIcon from "@/assets/svg/db.svg";
import CryptoJS from "crypto-js";

interface Iprops {
  openModal: boolean | "init";
  queryDbList: UseQueryResult<any, unknown>;
}

const dbIcon: any = {
  0: mysqlIcon,
  1: mongoIcon
};

const { TextArea, Password } = Input;

const driverOptsConf: any = {
  0: [
    {
      label: "com.mysql.cj.jdbc.Driver",
      value: "com.mysql.cj.jdbc.Driver"
    }
  ],
  1: [
    {
      label: "mongo",
      value: "mongo"
    }
  ]
};
const SECRET_KEY = "datasourceSecret";
// 加密函数
const encryptPassword = (originalPassword: string) => {
  if (!originalPassword) {
    alert("请输入原始密码");
    return;
  }

  // 使用 CryptoJS 的 AES 加密，模式为 ECB，填充为 Pkcs7
  const encrypted = CryptoJS.AES.encrypt(
    originalPassword,
    CryptoJS.enc.Utf8.parse(SECRET_KEY),
    {
      mode: CryptoJS.mode.ECB,
      padding: CryptoJS.pad.Pkcs7
    }
  ).toString();
  return encrypted;
};

const AddTable = ({ openModal, queryDbList }: Iprops) => {
  const { getOnlineDb, getOnlineDbTables, createDb } = useServices();
  const [open, setOpen] = useState<boolean>(false);
  const [form] = Form.useForm();
  const [linkState, setLinkState] = useState<boolean>(false);
  const [dbListOpts, setDbListOpts] = useState([]);
  const [tableList, setTableList] = useState<
    {
      name: string;
      description: string;
      [key: string]: any;
    }[]
  >([]);
  const curType = Form.useWatch("type", form);
  const curDbName = Form.useWatch("name", form);
  const curTables = Form.useWatch("tables", form);

  useEffect(() => {
    form.setFieldValue("driver", "");
  }, [curType]);

  const driverOpts = useMemo(() => {
    return driverOptsConf[curType] || [];
  }, [curType]);

  const getTableList = async (form: FormInstance<any>) => {
    if (!curDbName) return [];
    const formData = form.getFieldsValue();
    const _tableList = await getOnlineDbTables.mutateAsync(formData);
    setTableList(Array.isArray(_tableList) ? _tableList : []);
  };

  useEffect(() => {
    getTableList(form);
  }, [curDbName, form]);

  const tableOptions = useMemo(() => {
    return tableList.map((i: any) => ({
      label: i.name,
      value: i.name
    }));
  }, [tableList]);

  useEffect(() => {
    if (openModal === "init") return;
    setOpen(true);
  }, [openModal]);

  const closeModal = () => {
    form.resetFields();
    setOpen(false);
    setLinkState(false);
  };

  const handleLink = () => {
    form.validateFields().then(async (formData) => {
      const dbList = await getOnlineDb.mutateAsync({
        ...formData,
        password: encryptPassword(formData.password)
      });
      setDbListOpts(
        (dbList || []).map((i: string) => ({
          label: i,
          value: i
        }))
      );
      setLinkState(true);
    });
  };

  const confirmCreate = async () => {
    form.validateFields().then(async (_formData) => {
      const _tables = _formData.tables;
      const _createTables = _tables.reduce((pre: any[], cur: string) => {
        const _findItem = tableList.find((i) => i.name === cur);
        _findItem && pre.push(_findItem);
        return pre;
      }, []);
      const _params = {
        ..._formData,
        tables: _createTables,
        password: encryptPassword(_formData.password)
      };
      await createDb.mutateAsync(_params);
      message.success("创建成功");
      closeModal();
      queryDbList.refetch();
    });
  };

  const [tablesCheckedAll, setTablesCheckedAll] = useState(false);
  const getChecked = (value: string) => {
    const checkedTables = form.getFieldValue("tables") || [];
    return checkedTables.includes(value);
  };
  const tablesCheckedAllChange = (e: CheckboxChangeEvent) => {
    const checked = e.target.checked;
    if (checked) {
      form.setFieldValue(
        "tables",
        tableOptions.map((i) => i.value)
      );
    } else {
      form.setFieldValue("tables", []);
    }
  };
  useEffect(() => {
    if (curTables && curTables.length === tableOptions.length)
      setTablesCheckedAll(true);
    if (!curTables || curTables.length === 0) setTablesCheckedAll(false);
  }, [curTables, tableOptions]);

  const tablesCheckedAllIndeterminate = useMemo(() => {
    if (!curTables || !tableOptions) return false;
    return curTables.length !== 0 && curTables.length !== tableOptions.length;
  }, [curTables, tableOptions]);

  return (
    <Modal
      open={open}
      centered={true}
      title={<span className="font-normal">添加数据表</span>}
      classNames={{
        content: "add-table-modal-content",
        header: "add-table-modal-header",
        footer: "add-table-modal-footer"
      }}
      destroyOnClose
      onCancel={closeModal}
      footer={
        <div className="flex justify-end gap-4">
          <Button
            style={{
              border: "1px solid #ebebeb",
              color: "#555"
            }}
            onClick={closeModal}
          >
            取消
          </Button>
          <PrimaryBtn
            disabled={!linkState}
            style={{
              opacity: linkState ? 1 : 0.5
            }}
            onClick={confirmCreate}
            loading={createDb.isLoading}
          >
            确认
          </PrimaryBtn>
        </div>
      }
    >
      <span
        style={{
          borderTop: "1px solid #f0f0f0",
          height: 0,
          display: "block"
        }}
      />
      <Form
        layout="vertical"
        className="pt-6 px-5 max-h-[500px] overflow-y-auto"
        form={form}
      >
        <Form.Item
          label="数据库类型"
          required
          className="mb-5"
          name={"type"}
          rules={[{ required: true, message: "请选择数据库类型" }]}
        >
          <Select
            options={[
              { label: "mysql", value: 0 },
              { label: "mongo", value: 1 }
            ]}
            disabled={linkState}
          />
        </Form.Item>
        <Form.Item
          label="数据库驱动"
          required
          className="mb-5"
          name={"driver"}
          rules={[{ required: true, message: "请选择数据库驱动" }]}
        >
          <Select options={driverOpts} disabled={linkState} />
        </Form.Item>
        <Form.Item
          label="服务器地址"
          required
          className="mb-5"
          name={"address"}
          rules={[{ required: true, message: "请填写服务器地址" }]}
        >
          <TextArea
            autoSize={{ minRows: 3, maxRows: 3 }}
            disabled={linkState}
          />
        </Form.Item>
        <div className="flex gap-4 mb-5">
          <Form.Item
            label="用户名"
            required
            className="w-1/2 mb-0"
            name={"account"}
            rules={[{ required: true, message: "请填写用户名" }]}
          >
            <Input disabled={linkState} />
          </Form.Item>
          <Form.Item
            label="密码"
            required
            className="w-1/2 mb-0"
            name={"password"}
            rules={[{ required: true, message: "请填写密码" }]}
          >
            <Password disabled={linkState} />
          </Form.Item>
        </div>
        {!linkState && (
          <PrimaryBtn onClick={handleLink} loading={getOnlineDb.isLoading}>
            连接
          </PrimaryBtn>
        )}
        {linkState && (
          <>
            <Form.Item
              label="选择数据库"
              required
              className="mb-5"
              name={"name"}
              rules={[{ required: true, message: "请选择数据库" }]}
            >
              <Select
                options={dbListOpts}
                // optionRender={({ label, value }) => {
                //   return (
                //     <div className="flex h-[60px] box-border justify-center items-center py-3 px-2">
                //       <img
                //         src={dbIcon[curType] || defaultDbIcon}
                //         alt=""
                //         width={24}
                //         className="mr-3"
                //       />
                //       <div>
                //         <span>{label}</span>
                //       </div>
                //     </div>
                //   );
                // }}
              />
            </Form.Item>
            <Form.Item
              label="选择数据表"
              required
              className="mb-5"
              name={"tables"}
              rules={[{ required: true, message: "请选择数据表" }]}
            >
              <Select
                maxTagCount="responsive"
                mode="multiple"
                options={tableOptions}
                disabled={!curDbName}
                loading={getOnlineDb.isLoading}
                dropdownRender={(originNode) => {
                  return (
                    <div>
                      <div className="flex px-4 gap-3 h-8 items-center">
                        <Checkbox
                          checked={tablesCheckedAll}
                          indeterminate={tablesCheckedAllIndeterminate}
                          onChange={tablesCheckedAllChange}
                        />
                        全选
                      </div>
                      {originNode}
                    </div>
                  );
                }}
                optionRender={({ label, value }) => {
                  return (
                    <div className="flex px-4 gap-3 h-full items-center">
                      <Checkbox checked={getChecked(value as string)} />
                      {label}
                    </div>
                  );
                }}
              />
            </Form.Item>
            <Form.Item label="描述" className="mb-5" name={"description"}>
              <TextArea autoSize={{ minRows: 3, maxRows: 3 }} />
            </Form.Item>
          </>
        )}
      </Form>
    </Modal>
  );
};
export default AddTable;
