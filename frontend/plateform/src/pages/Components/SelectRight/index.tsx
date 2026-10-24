import {
  BASE_USER_TYPE,
  ELEMENT_TYPE,
  PERMISSION_STATUS
} from "@root/src/const/permission";
import { Select } from "antd";

const SelectCom = ({
  onChange,
  className,
  value,
  userType,
  disabled,
  type
}: any) => {
  const getOptions = (type: any) => {
    switch (type) {
      case "cec-temp":
        return [
          // { value: PERMISSION_STATUS.NO_PERMISSION, label: "无任何权限" },
          { value: PERMISSION_STATUS.READ_ONLY, label: "可使用" },
          { value: PERMISSION_STATUS.READ_AND_WRITE, label: "可编辑" },
          { value: PERMISSION_STATUS.ALL_PERMISSION, label: "可管理" }
        ];
      default:
        break;
    }
    if (userType === BASE_USER_TYPE.READ_ONLY) {
      return [
        { value: PERMISSION_STATUS.NO_PERMISSION, label: "无任何权限" },
        { value: PERMISSION_STATUS.READ_ONLY, label: "可阅读" }
      ];
    } else if (userType === BASE_USER_TYPE.EDIT) {
      return [
        { value: PERMISSION_STATUS.NO_PERMISSION, label: "无任何权限" },
        { value: PERMISSION_STATUS.READ_AND_WRITE, label: "可编辑" }
      ];
    } else if (userType === BASE_USER_TYPE.MANAGE) {
      return [
        { value: PERMISSION_STATUS.NO_PERMISSION, label: "无任何权限" },
        { value: PERMISSION_STATUS.ALL_PERMISSION, label: "可管理" }
      ];
    }
    return [
      // { value: PERMISSION_STATUS.NO_PERMISSION, label: "无任何权限" },
      { value: PERMISSION_STATUS.READ_ONLY, label: "可阅读" },
      { value: PERMISSION_STATUS.READ_AND_WRITE, label: "可编辑" },
      { value: PERMISSION_STATUS.ALL_PERMISSION, label: "可管理" }
    ];
  };
  return (
    <Select
      value={value}
      style={{ width: "100px", border: "none" }}
      className={className || ""}
      placeholder="请选择"
      variant="borderless"
      options={getOptions(type)}
      disabled={!!disabled}
      optionRender={(option, { selected }: any) => (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            padding: "0 8px",
            height: "32px"
          }}
        >
          {option.label}
        </div>
      )}
      onChange={(value) => onChange(value)}
    />
  );
};

export default SelectCom;
