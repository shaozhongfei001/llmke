import { createModel } from '@rematch/core'

export const builder = createModel()({
  state: {
    siderBarWidth: 80
  },
  reducers: {
    SET_SIDER_BAR_WIDTH: (state: any, payload: any) => {
      return {
        ...state,
        siderBarWidth: payload
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
