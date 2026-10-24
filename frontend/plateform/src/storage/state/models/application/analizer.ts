import { createModel } from '@rematch/core'

export const analizer = createModel()({
  name: 'analizer',
  state: {
    analyserTabCount: 0,
    caseMap: new Map()
  },
  reducers: {
    clickAnalyserTab: (state: any, payload: any) => {
      return {
        ...state,
        analyserTabCount: ++state.analyserTabCount
      }
    },
    clearAnalyserTab: (state: any, payload: any) => {
      return {
        ...state,
        analyserTabCount: -1
      }
    },
    saveCaseCanvas: (state: any, payload: any) => {
      const { key, val } = payload
      return {
        ...state,
        caseMap: state.caseMap.set(key, val)
      }
    },
    getCaseCanvasByKey: (state: any, payload: any) => {
      const CaseCanvasIsExits = state.caseMap.has(payload)
      if (CaseCanvasIsExits) {
        return state.caseMap.get(payload)
      } else {
        return state
      }
    },
    deleteCaseCanvasByKey: (state: any, payload: any) => {
      const CaseCanvasIsExits = state.caseMap.has(payload)
      if (CaseCanvasIsExits) {
        state.caseMap.delete(payload)
      }
      return {
        ...state
      }
    },
    clearAllCase: (state: any, payload: any) => {
      state.caseMap.clear()
      return {
        ...state
      }
    }
  },
  effects: (dispatch: any) => {
    const { players } = dispatch
    return {
      async getPlayers(): Promise<any> {
        const response = await fetch('https://www.balldontlie.io/api/v1/players')
        const { data } = await response.json()
        players.SET_PLAYERS(data)
      }
    }
  }
})
