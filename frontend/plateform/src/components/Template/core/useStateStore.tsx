import { create } from "zustand";
export const InitCount = 1;
export const InitData = {
  key: InitCount,
  dataIndex: "title",
  title: "文章标题",
  required: true,
  type: "string"
};
interface IZustandState {
  plateValue: Array<any>;
  contentValue: any;
  setPlateValue: (val: Array<any>) => void;
  allList: Array<any>;
  setAllList: (val: Array<any>) => void;
  restList: Array<any>;
  setRestList: (val: Array<any>) => void;
  tableList: Array<any>;
  setTableList: (val: Array<any>) => void;
  isModalOpen: boolean;
  setIsModalOpen: (val: boolean) => void;
  supportMaterials: boolean;
  setSupportMaterials: (val: boolean) => void;
  supportOutlines: boolean;
  setSupportOutlines: (val: boolean) => void;
  traceToMaterial: boolean;
  setTraceToMaterial: (val: boolean) => void;
  close: () => void;
}

export const INIT_PLATE_VALUE = [
  {
    type: "p",
    children: [{ text: "" }]
  }
];

export const useStateStore = create<IZustandState>((set) => ({
  plateValue: INIT_PLATE_VALUE,
  setPlateValue: (plateValue) => {
    set({ plateValue });
  },
  contentValue: INIT_PLATE_VALUE,
  allList: [],
  setAllList: (allList) => {
    set({ allList });
  },
  restList: [],
  setRestList: (restList) => {
    set({ restList });
  },
  tableList: [InitData],
  setTableList: (tableList) => {
    set({ tableList: !tableList?.length ? [InitData] : tableList });
  },
  isModalOpen: false,
  setIsModalOpen: (isModalOpen) => {
    set({ isModalOpen });
  },
  supportMaterials: false,
  setSupportMaterials: (open) => {
    set({ supportMaterials: open });
  },
  supportOutlines: false,
  setSupportOutlines: (open) => {
    set({ supportOutlines: open });
  },
  traceToMaterial: false,
  setTraceToMaterial: (open) => {
    set({ traceToMaterial: open });
  },
  close: () => {
    set({
      tableList: [InitData],
      restList: [],
      allList: [],
      plateValue: INIT_PLATE_VALUE,
      supportMaterials: false,
      supportOutlines: false,
      traceToMaterial: false
    });
  }
}));
