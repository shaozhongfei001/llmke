import { Button, ConfigProvider, Form, Input, message, Modal } from "antd";
import { serialize, WithPlate } from "../common/editor";
import { uid } from "uid";
import "../style.less";
import { useEffect, useMemo } from "react";

export enum ChunkType {
  CONFIRM = "confirm"
}

const EditChunkModal = ({
  showModal,
  setShowModal,
  data = {},
  loading,
  handleEvent
}: any) => {
  const handleConfirm = () => {
    if (!editor) {
      message.error("编辑器不存在");
      return;
    }

    const value = serialize(editor.children);
    if (value.length > 3000) {
      return message.warning("切片内容不能超过3000字");
    }
    handleEvent(ChunkType.CONFIRM, { content: value, chunkId: data.id });
  };

  const modalStyles = {
    header: {
      padding: "20px 24px",
      margin: 0,
      borderBottom: "1px solid #F0F0F0"
    },
    body: { padding: "20px 24px 0 24px" },
    mask: {},
    footer: { padding: "20px 24px 20px 24px", margin: 0 },
    content: { padding: 0 }
  };

  const { element, editor }: any = useMemo(() => {
    if (!showModal) return {};
    const { element, editor }: any = WithPlate({
      className:
        "px-0 py-0 text-[14px] text-[#2a2a2a] overflow-x-hidden bg-transparent !border-none focus-visible:!outline-none focus-visible:!ring-offset-0 focus:!outline-[none] min-h-[360px]",
      data: data.content,
      type: data.type
    });
    return { element, editor };
  }, [data, showModal]);

  return (
    <ConfigProvider
      modal={{
        styles: modalStyles
      }}
    >
      <Modal
        title="编辑切片"
        open={showModal}
        width={908}
        className="min-w-[908px]"
        onClose={() => {
          setShowModal(false);
        }}
        onCancel={() => {
          setShowModal(false);
        }}
        footer={
          <div className="flex justify-end">
            <Button
              className="mr-[16px] w-[76px] border-[#EBEBEB]"
              onClick={() => {
                setShowModal(false);
              }}
            >
              取消
            </Button>
            <Button
              type="primary"
              loading={loading}
              className="w-[76px] border-none bg-[linear-gradient(90deg,#0359FF,#BD9CFF)]"
              onClick={handleConfirm}
            >
              确认
            </Button>
          </div>
        }
      >
        <div
          className="w-[812px] h-[370px] bg-[#F1F5FE] rounded-[6px] px-[24px] py-[24px] overflow-y-auto chatView"
          style={{ border: "1px solid #D4DEF5" }}
        >
          {element}
        </div>
      </Modal>
    </ConfigProvider>
  );
};

export default EditChunkModal;
