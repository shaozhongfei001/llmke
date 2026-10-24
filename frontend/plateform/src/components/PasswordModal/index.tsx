import { Modal, Form, Input, Button } from "antd";
import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";
import { SecurityCom } from "./components/SecurityCom";
import { ResetPassword } from "./components/ResetPassword";
import { useEffect, useMemo, useState } from "react";
import { SuperResetPassword } from "./components/SuperResetPassword";
import { SuperViewPassword } from "./components/SuperViewPassword";
import { AfterSuperReset } from "./components/AfterSuperReset";

export enum MODAL_TYPE {
  SECURITYSET = "securitySet",
  SECURITYUPDATE = "securityUpdate",
  RESET = "reset",
  REGISTER = "register",
  SUPER_RESET = "superReset",
  SUPER_VIEW = "superView",
  AfterSuperReset = "afterSuperReset"
}
export type typeTYPE =
  | MODAL_TYPE.SECURITYSET
  | MODAL_TYPE.RESET
  | MODAL_TYPE.SECURITYUPDATE
  | MODAL_TYPE.REGISTER
  | MODAL_TYPE.SUPER_RESET
  | MODAL_TYPE.SUPER_VIEW
  | MODAL_TYPE.AfterSuperReset;

export interface PasswordModalProps {
  userId?: string;
  visible: boolean;
  onCancel: () => void;
  type: typeTYPE;
  eventEmit?: (type: string, data?: any) => void;
}

export default function PasswordModal({
  visible,
  onCancel,
  type,
  userId,
  eventEmit
}: PasswordModalProps) {
  const [showReset, setShowReset] = useState<boolean>(false);
  const [securityKey, setSecurityKey] = useState<any>();
  const [tempTitle, setTempTitle] = useState("");
  const title = useMemo(() => {
    if (tempTitle) return tempTitle;
    if (type === MODAL_TYPE.RESET) {
      return showReset ? "重置密码" : "密保问题校验";
    } else if (type === MODAL_TYPE.SECURITYSET) {
      return "密保问题设置";
    } else if (type === MODAL_TYPE.SECURITYUPDATE) {
      return "密保问题设置";
    } else if (
      type === MODAL_TYPE.SUPER_RESET ||
      type === MODAL_TYPE.AfterSuperReset
    ) {
      return "重置密码";
    } else if (type === MODAL_TYPE.SUPER_VIEW) {
      return "查看密码";
    }
  }, [type, showReset, tempTitle]);

  const emitEvent = (n: string, d: any) => {
    switch (n) {
      case "resetPassword:cancel":
        setShowReset(false);
        onCancel();
        break;
      case "cancel":
        onCancel();
        break;
      case "superReset:cancel":
        eventEmit && eventEmit("superReset:afterReset");
        onCancel();
      case "setTitle":
        setTempTitle(d);
        break;
    }
  };

  return (
    <Modal
      title={title}
      open={visible}
      footer={null}
      width={600}
      closable={false}
      destroyOnHidden
    >
      {type === MODAL_TYPE.AfterSuperReset && (
        <AfterSuperReset emitEvent={emitEvent} />
      )}
      {type === MODAL_TYPE.SUPER_VIEW && (
        <SuperViewPassword emitEvent={emitEvent} userId={userId} />
      )}
      {type === MODAL_TYPE.SUPER_RESET && (
        <SuperResetPassword emitEvent={emitEvent} userId={userId} />
      )}
      {type === MODAL_TYPE.SECURITYSET && (
        <SecurityCom
          onCancel={onCancel}
          type={type}
          setShowReset={setShowReset}
          setSecurityKey={setSecurityKey}
        />
      )}
      {type === MODAL_TYPE.SECURITYUPDATE && (
        <SecurityCom
          onCancel={onCancel}
          type={type}
          setShowReset={setShowReset}
          setSecurityKey={setSecurityKey}
        />
      )}
      {type === MODAL_TYPE.REGISTER && (
        <SecurityCom
          onCancel={onCancel}
          type={type}
          setShowReset={setShowReset}
          setSecurityKey={setSecurityKey}
        />
      )}
      {type === MODAL_TYPE.RESET &&
        (showReset ? (
          <ResetPassword emitEvent={emitEvent} securityKey={securityKey} />
        ) : (
          <SecurityCom
            onCancel={onCancel}
            type={type}
            setShowReset={setShowReset}
            setSecurityKey={setSecurityKey}
          />
        ))}
    </Modal>
  );
}
