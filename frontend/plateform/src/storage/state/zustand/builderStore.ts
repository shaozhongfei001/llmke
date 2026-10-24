import { create } from 'zustand';

interface BuilderState {
  graphData: any;
  setGraphData: (data: any) => void;
  clearGraphData: () => void;
}

export const useBuilderStore = create<BuilderState>((set) => ({
  graphData: null,
  
  setGraphData: (data) => set({ graphData: data }),
  
  clearGraphData: () => set({ graphData: null }),
})); 