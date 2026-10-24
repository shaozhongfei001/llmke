import { create } from 'zustand';

interface GlobalState {
  siderBarWidth: number;
  theme: string;
  collapsed: boolean;
  globalMenu: any;
  prevRoute: string;
  setPrevRoute: (route: string) => void;
  setGlobalState: (state: Partial<GlobalState>) => void;
  toggleCollapsed: () => void;
  setGlobalMenu: (menu: any) => void;
}

export const useGlobalStore = create<GlobalState>((set) => ({
  // 初始状态
  siderBarWidth: 80,
  theme: "default",
  collapsed: true,
  globalMenu: null,
  prevRoute: "",

  // actions
  setPrevRoute: (route) => set({ prevRoute: route }),

  setGlobalState: (newState) => {
    if (typeof newState !== "object" || newState === null) {
      return;
    }
    set((state) => ({ ...state, ...newState }));
  },

  toggleCollapsed: () => set((state) => ({ collapsed: !state.collapsed })),

  setGlobalMenu: (menu) => set({ globalMenu: menu })
})); 