import MultiSelection, { getId } from "@root/src/components/MultiSelection";
import { useEffect, useState } from "react";
import { MockDepartmentData } from "../common/mockData";
import useSystemApi from "@root/src/apis/system";
import { uid } from "uid";
import { ELEMENT_TYPE } from "@root/src/const/permission";
import _ from "lodash";
export enum EVENT_TYPE {
  CHANGE_PERMISSION = 0
}

const InitData = [
  {
    id: uid(),
    hideCheck: true,
    name: "联系人",
    elementType: 1,
    children: [
      {
        id: uid(),
        hideCheck: true,
        name: "组织架构",
        children: [],
        elementType: 1
      },
      {
        id: uid(),
        hideCheck: true,
        name: "用户组",
        children: [],
        elementType: 1
      }
    ]
  }
];

const SelectOrganization = ({
  checkedData,
  setCheckedData,
  open,
  type
}: {
  open: boolean;
  checkedData: any;
  setCheckedData: (arg: any) => void;
  type?: string;
}) => {
  const api = useSystemApi();

  const [loading, setLoading] = useState(false);
  const [curPartment, setCurPartment] = useState<any>([
    `${InitData[0].id}_${InitData[0].elementType}`
  ]);
  const [allList, setAllList]: any = useState(InitData);

  const clearData = () => {
    setCurPartment([`${InitData[0].id}_${InitData[0].elementType}`]);
    setCheckedData([]);
  };

  const clickNavbar = (item: any) => {
    if (!item) {
      return setCurPartment(null);
    }
    if (item.elementType === ELEMENT_TYPE.DEPARTMENT && !item.checked) {
      if (curPartment) {
        const i = curPartment.indexOf(item.id);
        if (i > -1) {
          setCurPartment(curPartment.splice(0, i + 1));
          return;
        }
      }

      setCurPartment((pre: any[] | null) => {
        if (item.parentId && pre?.length) {
          return [...pre, item.id];
        }
        const top = InitData[0];
        const zuzhi = top.children[0];
        const zu = top.children[1];
        if (
          pre?.length === 1 &&
          (pre[0] === `${zuzhi.id}_${zuzhi.elementType}` ||
            pre[0] === `${zu.id}_${zu.elementType}` ||
            pre[0] === `${top.id}_${top.elementType}`)
        ) {
          return [...pre, item.id];
        }
        return [item.id];
      });
    }
  };

  const getDepartmentInfo = async () => {
    setLoading(true);
    try {
      const res: any = await api.getTreeFrame({}, {});
      setLoading(false);
      if (res.success) {
        setAllList((pre: any) => {
          if (res?.data?.length) {
            const [all, ...rest] = res.data;
            pre[0].children[0].children = [...(all?.children || []), ...rest];
            return [...pre];
          } else {
            return pre;
          }
        });
      }
    } catch (error) {
      setLoading(false);
      console.log("error", error);
    }
  };

  const getGroupInfo = async () => {
    setLoading(true);
    try {
      const res: any = await api.getTreeGroup({}, {});
      setLoading(false);
      if (res.success) {
        setAllList((pre: any) => {
          pre[0].children[1].children = res.data;
          return [...pre];
        });
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  useEffect(() => {
    if (open) {
      getGroupInfo();
      getDepartmentInfo();
      clearData();
    }
  }, [open]);

  return (
    <MultiSelection
      clickNavbar={clickNavbar}
      curPartment={curPartment}
      allList={allList}
      setCheckedData={setCheckedData}
      checkedData={checkedData}
      loading={loading}
      type={type}
      width={658}
    />
  );
};

export default SelectOrganization;
