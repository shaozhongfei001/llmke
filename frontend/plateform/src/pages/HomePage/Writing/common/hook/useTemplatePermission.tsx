import { useEffect, useState } from "react";
import { useSelector } from "react-redux";

const useManageTemplatePermission = () => {
  const [manageTemplatePermission, setManageTemplatePermission] =
    useState<boolean>(false);
  const globalMenu: any = useSelector((state: any) => state.global.globalMenu);
  useEffect(() => {
    if (!globalMenu) return;
    //这里目前只处理写作模版的权限
    const docMenu = globalMenu.filter(
      (i: any) => i.url === "/docWriting/template"
    );
    if (!docMenu || docMenu.length === 0) return;
    const templateManagePermission = docMenu[0]?.subMenuDTOList.filter(
      (i: any) => i.url === "/docWriting/template/permission"
    );
    setManageTemplatePermission(templateManagePermission[0]?.permission);
  }, [globalMenu]);
  return {
    manageTemplatePermission
  };
};
export default useManageTemplatePermission;
