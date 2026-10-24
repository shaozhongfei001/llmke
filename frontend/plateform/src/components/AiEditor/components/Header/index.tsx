import { cn } from "@udecode/cn";
import { Button, Typography, Modal, Input, Divider, Flex, message } from "antd";
import {
  api_exportArticleById,
  api_saveArticleSetting,
} from "../../core/services/servers";
import { useStateStore } from "../../core/states/useStateStore";
import { useEffect, useState } from "react";
import EditIcon from "@/components/AiEditor/assets/icon/edit.svg";
import HomeIcon from "@/components/AiEditor/assets/img/home.png";
import useAiEditorOperators from "../../core/operators/useAiEditorOperators";
import { EDITOR_EVENT_NAME, editorEventBus } from "../../editorEventBus";

const { Text } = Typography;

const Header = ({ handleBack }) => {
  const { projectData, setProjectData, serverInfo } = useStateStore();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [confirmLoading, setConfirmLoading] = useState(false);

  useEffect(() => {
    setTitle(projectData.title);
  }, [projectData.title]);

  const submitTitle = async () => {
    setProjectData((p) => ({
      ...p,
      title: title,
    }));
    const params: any = {
      title: title,
      id: projectData.id,
    };
    try {
      setConfirmLoading(true);
      await api_saveArticleSetting({
        data: { params },
        config: serverInfo,
      });
    } catch (e) {
      console.log("e");
    } finally {
      setConfirmLoading(false);
    }

    setOpen(false);
  };

  const handleTitleChange = (e) => {
    setTitle(e.target.value);
  };

  return (
    <div
      className={cn(
        "w-full relative !text-[#555555] box-border h-full px-[20px] flex justify-between  items-center ",
        " bg-white shadow-sm z-50"
      )}
    >
      <Modal
        open={open}
        onCancel={() => setOpen(false)}
        title={"编辑标题"}
        footer={
          <div>
            <Button
              className="mr-[16px] w-[76px]"
              onClick={() => {
                setOpen(false);
              }}
            >
              取消
            </Button>
            <Button
              type="primary"
              className="w-[76px] border-none"
              loading={confirmLoading}
              onClick={submitTitle}
            >
              确认
            </Button>
          </div>
        }
      >
        <Input value={title} onChange={handleTitleChange} />
      </Modal>
      <Flex
        align="center"
        className="  cursor-pointer"
        onClick={() => setOpen(true)}
      >
        <img
          src={HomeIcon}
          width={20}
          className="cursor-pointer"
          onClick={() => {
            handleBack && handleBack();
          }}
        />
      </Flex>
    </div>
  );
};

export default Header;
