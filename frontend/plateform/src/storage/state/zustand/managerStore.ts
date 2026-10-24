import { create } from 'zustand';

interface ManagerState {
  afterAddRole: number;
  setAfterAddRole: (value: number) => void;
}

export const useManagerStore = create<ManagerState>((set) => ({
  afterAddRole: 0,
  
  setAfterAddRole: (value) => set({ afterAddRole: value }),
})); 