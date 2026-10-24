import { Modal, Form, Input, Button } from "antd";
import { useEffect, useState } from "react";
import { useServices } from "../service";
import "@/assets/styles/knowledgebase.less";
import TagsInputer from "./TagsInputer";
import { useLocation } from "react-router-dom";
const { TextArea } = Input;

interface IRow {
  id?: number;
  kbName?: string;
  kbDes?: string | null;
  [key: string]: any;
}
interface IEmpty {
  isShowCreateModal: boolean;
  editRow: IRow;
  closeModal: (isRefresh: boolean) => void;
  platform: string;
}

const CreateForm = (props: IEmpty) => {
  const { isShowCreateModal, editRow, closeModal, platform } = props;
  const [createForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const { createKb, updateById } = useServices(platform);
  const [tagsStr, setTagsStr] = useState("");
  const { pathname } = useLocation();

  const handleCreate = async () => {
    createForm.validateFields().then((data) => {
      // console.log("editRow:", editRow)
      setLoading(true);
      const { id } = editRow;
      if (id) {
        tagsStr && (data.kbLabel = tagsStr);
        updateById({ ...data, id })
          .then(() => {
            successFn();
          })
          .catch((e) => {
            console.log(e);
            setLoading(false);
          });
      } else {
        tagsStr && (data.kbLabel = tagsStr);
        if (pathname.indexOf("chats") > -1) {
          data.fileType = "intelligent";
        }

        if (pathname.indexOf("docWriting") > -1) {
          data.fileType = "financial";
        }
        createKb({ ...data })
          .then(() => {
            successFn();
          })
          .catch((e) => {
            console.log(e);
            setLoading(false);
          });
      }
    });
  };

  const successFn = () => {
    closeModal(true);
    setLoading(false);
    createForm.resetFields();
  };

  const handlerCancle = () => {
    createForm.resetFields();
    closeModal(false);
  };

  useEffect(() => {
    if (editRow) {
      createForm.setFieldsValue({
        kbName: editRow.kbName,
        kbDes: editRow.kbDes
      });
      setTagsStr(editRow?.kbLabel);
    }
  }, [editRow]);

  return (
    <Modal
      title={editRow.id ? "编辑知识库" : `创建知识库`}
      open={isShowCreateModal}
      width={512}
      onCancel={handlerCancle}
      onOk={handleCreate}
      confirmLoading={loading}
      // footer={false}
    >
      <div className="create-form">
        <Form form={createForm}>
          <Form.Item
            label="名称"
            name="kbName"
            rules={[{ required: true }]}
            labelCol={{ span: 5 }}
          >
            <Input placeholder="请输入" />
          </Form.Item>
          <Form.Item name="kbDes" label="知识库描述" labelCol={{ span: 5 }}>
            <TextArea
              placeholder="请输入"
              style={{ height: 100, resize: "none" }}
            />
          </Form.Item>
          {/* <Form.Item name="kbLabel" label="标签" labelCol={{ span: 5 }}>
            <TagsInputer
              setTagsStr={setTagsStr}
              editTags={tagsStr}
              isEdit={editRow.id != undefined}
            />
          </Form.Item> */}
        </Form>
      </div>
    </Modal>
  );
};

export default CreateForm;
