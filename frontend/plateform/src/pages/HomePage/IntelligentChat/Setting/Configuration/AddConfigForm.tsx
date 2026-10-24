import { Modal, Form, Input, Button, Select, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import "@/assets/styles/knowledgebase.less";
import {
  getGroupList,
  getUserList,
  setGroupPermission,
  setUserPermission
} from "./service";
import { useParams } from "react-router-dom";

interface IEmpty {
  type: string;
  cb?: () => void;
  isShowCreateModal: boolean;
  closeModal: (isRefresh: boolean) => void;
}

const AddConfigForm = (props: IEmpty) => {
  const { isShowCreateModal, closeModal, cb, type } = props;
  const { id: knowledgeBaseId }: any = useParams();
  const [createForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [userList, setUserList] = useState([]);
  const [groupList, setGroupList] = useState([]);

  const setGroupP = async (data: any) => {
    const { groupIds, permission } = data;
    const res = await setGroupPermission({
      groupIds,
      permission,
      bizType: 1,
      targetId: knowledgeBaseId
    });
    if (res) {
      message.success("添加权限成功!");
      closeModal(false);
      cb && cb();
    }
  };

  const setUserP = async (data: any) => {
    const { permission, userIds } = data;

    const res = await setUserPermission({
      userIds,
      permission,
      bizType: 1,
      targetId: knowledgeBaseId
    });
    if (res) {
      message.success("添加权限成功!");
      closeModal(false);
      cb && cb();
    }
  };

  const handleCreate = async () => {
    createForm
      .validateFields()
      .then(async (data) => {
        setLoading(true);

        if (!knowledgeBaseId) {
          message.warning("未传知识库ID");
          return;
        }

        type === "1" ? setGroupP(data) : setUserP(data);
      })
      .catch((e) => {
        console.log("e--->", e);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handlerCancle = () => {
    createForm.resetFields();
    closeModal(false);
  };

  const fetchGroupList = async () => {
    try {
      const res = await getGroupList({ pageNo: 1, pageSize: 9999 });
      if (res?.records?.length) {
        return res.records.map((item: any) => ({
          value: item.id,
          label: item.name
        }));
      } else {
        return [];
      }
    } catch (e) {
      return [];
    }
  };

  const fetchUserList = async () => {
    try {
      const res = await getUserList({ pageNo: 1, pageSize: 9999 });
      if (res?.records?.length) {
        return res.records.map((item: any) => ({
          value: item.id,
          label: item.userName
        }));
      } else {
        return [];
      }
    } catch (e) {
      return [];
    }
  };

  const initOptions = async () => {
    const userList = await fetchUserList();
    const groupList = await fetchGroupList();
    setUserList(userList);
    setGroupList(groupList);
  };

  useEffect(() => {
    initOptions();
  }, []);

  useEffect(() => {
    if (!isShowCreateModal) {
      createForm.resetFields();
    }
  }, [isShowCreateModal]);

  return (
    <Modal
      title="添加"
      open={isShowCreateModal}
      width={512}
      onCancel={handlerCancle}
      onOk={handleCreate}
      confirmLoading={loading}
      forceRender
    >
      <div className="create-form">
        <Form form={createForm}>
          {type === "1" ? (
            <Form.Item
              label="用户组"
              name="groupIds"
              rules={[{ required: true }]}
              labelCol={{ span: 5 }}
            >
              <Select
                showSearch
                placeholder="请选择"
                optionFilterProp="label"
                mode="multiple"
                options={groupList}
              />
            </Form.Item>
          ) : (
            <Form.Item
              label="用户"
              name="userIds"
              rules={[{ required: true }]}
              labelCol={{ span: 5 }}
            >
              <Select
                showSearch
                optionFilterProp="label"
                placeholder="请选择"
                mode="multiple"
                options={userList}
              />
            </Form.Item>
          )}
          <Form.Item
            label="权限"
            name="permission"
            rules={[{ required: true }]}
            labelCol={{ span: 5 }}
          >
            <Select
              placeholder="请选择"
              options={[
                { value: 1, label: "查看" },
                { value: 2, label: "编辑" }
              ]}
            />
          </Form.Item>
        </Form>
      </div>
    </Modal>
  );
};

export default AddConfigForm;
