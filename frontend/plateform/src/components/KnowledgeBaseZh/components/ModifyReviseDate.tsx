import { Button, Modal, DatePicker } from "antd";
import type { DatePickerProps } from "antd";
import { useState } from "react";

interface IModifyReviseDate {
  row: any;
  cancleHandle: () => void;
  confirmHandle: (date: any, callback?: () => void) => void;
}

const ModifyReviseDate = (props: IModifyReviseDate) => {
  const { row, cancleHandle, confirmHandle } = props;
  const [reviseDate, setReviseDate] = useState<any>();
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const onReviseDateChange: DatePickerProps["onChange"] = (_, dateString) => {
    setReviseDate(dateString);
  };

  const closeLoading = () => {
    setIsLoading(false);
  };

  const updateReviseDate = () => {
    if (reviseDate) {
      setIsLoading(true);
      confirmHandle(reviseDate, closeLoading);
    }
  };

  return (
    <Modal
      destroyOnClose={true}
      footer={null}
      open={row}
      width={600}
      onCancel={cancleHandle}
      title="订正修订时间"
    >
      {/* <div>
        {JSON.stringify(row)}---{reviseDate}
      </div> */}
      <div style={{ padding: "20px 0" }}>
        <DatePicker
          style={{ width: "540px", height: "40px" }}
          onChange={onReviseDateChange}
        />
      </div>
      <div style={{ display: "flex", gap: 10, flexDirection: "row-reverse" }}>
        <Button
          type="primary"
          //   disabled={!reviseDate}
          loading={isLoading}
          onClick={updateReviseDate}
          style={{
            width: "76px",
            background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
          }}
        >
          确认
        </Button>
        <Button
          disabled={isLoading}
          onClick={cancleHandle}
          style={{
            width: "76px",
            border: "1px solid #ebebeb",
          }}
        >
          取消
        </Button>
      </div>
    </Modal>
  );
};

export default ModifyReviseDate;
