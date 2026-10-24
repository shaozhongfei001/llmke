import React, { useEffect, useState, useMemo } from "react";
import { ExclamationCircleFilled } from "@ant-design/icons";
import { Button, Modal, Input, message } from "antd";
import { PrimaryBtn } from "@/pages/HomePage/Writing/common/components/PrimaryBtn";
import { useServices } from "../common/server.ts";
interface IModal {
  isShow: boolean;
  id?: string;
  initailTitle?: string;
  closeModal: () => void;
  confirmModal: (title: string, id?: string) => Promise<any>;
}

const AddComponent = (props: IModal) => {
  const { isShow, closeModal, id, confirmModal, initailTitle = "" } = props;
  const [title, setTitle] = useState<string>();
  const [loading, setLoading] = useState<boolean>(false);

  const handlerCancel = () => {
    closeModal();
  };

  const canSave = useMemo(() => {
    return title && !!title.trim();
  }, [title]);

  const confirm = async () => {
    if (!title || !title.trim()) {
      message.warning("请输入组件名称");
      return;
    } else {
      try {
        setLoading(true);

        const res = await confirmModal(title, id);
        if (res) {
          closeModal();
        }
      } catch (e) {
        console.log("add section err------>", e);
      } finally {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    if (isShow && initailTitle) {
      setTitle(initailTitle);
    }
    return () => {
      setTitle(undefined);
      setLoading(false);
    };
  }, [isShow, initailTitle]);

  return (
    <Modal
      className="add-modal"
      open={isShow}
      width={520}
      title={id ? "重命名" : "新建组件"}
      onCancel={handlerCancel}
      footer={
        <div className="flex justify-end gap-4">
          <Button
            key="back"
            onClick={handlerCancel}
            className="border-solid border-[1px] border-[#ebebeb]"
          >
            <span className="text-[#555]">取消</span>
          </Button>
          <PrimaryBtn
            onClick={confirm}
            disabled={!canSave}
            loading={loading}
            style={{
              opacity: !canSave ? "50%" : "100%"
            }}
          >
            确认
          </PrimaryBtn>
        </div>
      }
    >
      <div className="">
        <Input
          className="h-[40px]"
          value={title}
          onChange={(e: any) => setTitle(e.target.value)}
        />
      </div>
    </Modal>
  );
};

export default AddComponent;
