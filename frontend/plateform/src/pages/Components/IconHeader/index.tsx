import { Avatar } from "antd";
import { Building2 } from "lucide-react";
import Apartment from "@/assets/img/Apartment.png";
import AllUser from "@/assets/img/allUser.png";
import Group from "@/assets/img/group.png";
import { ELEMENT_TYPE } from "@root/src/const/permission";
import READ_ONLY from "@root/src/assets/img/readOnly.png";
import EDIT from "@root/src/assets/img/edit.png";
import ALLPERMISSION from "@root/src/assets/img/allpermission.png";
const IconHeader = ({
  text,
  size,
  type = ELEMENT_TYPE.USER,
  bg,
  len,
  rounded,
  fontSize,
  mr,
  className
}: {
  text: string;
  size?: number;
  len?: number;
  bg?: string;
  type?: number;
  rounded?: string;
  mr?: string;
  fontSize?: string;
  className?: string;
}) => {
  const noBg: any = [
    ELEMENT_TYPE.COLLABORATORS_ALL_PERMISSION,
    ELEMENT_TYPE.COLLABORATORS_READONLY,
    ELEMENT_TYPE.COLLABORATORS_READ_AND_WRITE,
    ELEMENT_TYPE.ALLUSER
  ];
  return (
    <div
      className={`flex shrink-0 ${rounded || "rounded-[4px]"} justify-center items-center text-white text-[14px] ${mr || "mr-[16px]"} ${className || ""}`}
      style={{
        width: `${size || 28}px`,
        height: `${size || 28}px`,
        background:
          noBg.includes(type) ||
          type === ELEMENT_TYPE.DEPARTMENT ||
          type === ELEMENT_TYPE.GROUP
            ? ""
            : bg || "linear-gradient(-50deg, #7FC0FB 10%, #4088F4 90%)"
      }}
    >
      {type === ELEMENT_TYPE.COLLABORATORS_ALL_PERMISSION && (
        <img src={ALLPERMISSION} width={size || 28} height={size || 28} />
      )}
      {type === ELEMENT_TYPE.COLLABORATORS_READONLY && (
        <img src={READ_ONLY} width={size || 28} height={size || 28} />
      )}
      {type === ELEMENT_TYPE.COLLABORATORS_READ_AND_WRITE && (
        <img src={EDIT} width={size || 28} height={size || 28} />
      )}
      {(type === ELEMENT_TYPE.DEPARTMENT || type === ELEMENT_TYPE.GROUP) && (
        <img src={Group} width={size || 28} height={size || 28} />
      )}
      {type === ELEMENT_TYPE.ALLUSER && (
        <img src={AllUser} width={size || 28} height={size || 28} />
      )}
      {type === ELEMENT_TYPE.USER && (
        <div className={`${fontSize || "text-[14px]"}`}>
          {text?.substr(0, len || 1)}
        </div>
      )}
    </div>
  );
};

export default IconHeader;
