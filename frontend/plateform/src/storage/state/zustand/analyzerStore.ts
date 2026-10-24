import { create } from 'zustand';

interface AnalyzerState {
  currentGraph: any;
  graphList: any[];
  setCurrentGraph: (graph: any) => void;
  setGraphList: (list: any[]) => void;
  addGraph: (graph: any) => void;
  removeGraph: (id: string) => void;
  updateGraph: (id: string, data: any) => void;
  clearGraphs: () => void;
}

export const useAnalyzerStore = create<AnalyzerState>((set) => ({
  currentGraph: null,
  graphList: [],
  
  setCurrentGraph: (graph) => set({ currentGraph: graph }),
  
  setGraphList: (list) => set({ graphList: list }),
  
  addGraph: (graph) => set((state) => ({
    graphList: [...state.graphList, graph]
  })),
  
  removeGraph: (id) => set((state) => ({
    graphList: state.graphList.filter(graph => graph.id !== id)
  })),
  
  updateGraph: (id, data) => set((state) => ({
    graphList: state.graphList.map(graph => 
      graph.id === id ? { ...graph, ...data } : graph
    )
  })),
  
  clearGraphs: () => set({ graphList: [], currentGraph: null }),
})); 