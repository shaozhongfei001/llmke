import TextArea from "antd/es/input/TextArea";
import triangle from "@/assets/img/triangle.png";
import { Button } from "antd";
import "./style.less";
import { ChangeEventHandler, useEffect, useState } from "react";

const AnswerTextArea = ({ defaultValue, content, setContent }: any) => {
  const [doEdit, setDoEdit] = useState(false);
  const [curContent, setCurContent] = useState("");

  useEffect(() => {
    setCurContent(content || defaultValue);
  }, [content]);
  return (
    <div className="answerText relative border-solid border-[1px] border-[#D9D9D9] rounded-[4px]">
      <div className="h-[100px] w-full flex items-center justify-between">
        <TextArea
          bordered={false}
          style={{ height: "75px", resize: "none" }}
          className="flex-1"
          value={curContent}
          onChange={(e: any) => {
            setCurContent(e.target.value);
          }}
          disabled={!doEdit}
        />
        {doEdit ? (
          <div className="100px">
            <Button
              type="link"
              className="mr-[8px]"
              onClick={() => {
                setContent(curContent);
                setDoEdit(false);
              }}
            >
              保存
            </Button>
            <Button
              type="link"
              className="mr-[10px]"
              onClick={() => {
                setCurContent(content);
                setDoEdit(false);
              }}
            >
              取消
            </Button>
          </div>
        ) : (
          <Button
            type="link"
            className="mr-[10px]"
            onClick={() => {
              setContent(curContent);
              setDoEdit(true);
            }}
          >
            编辑
          </Button>
        )}
      </div>
      <img
        className="absolute w-[24px] h-[15px] top-[-10px] right-[63px]"
        src={triangle}
      />
    </div>
  );
};

export default AnswerTextArea;
