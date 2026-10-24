import { createModel } from '@rematch/core'

export const manager = createModel()({
  state: {
    afterAddRole: 0 // 0不触发 1添加角色 2 编辑角色
  },
  reducers: {
    SET_AFTER_ADD_ROLE: (state: any, payload: any) => {
      return {
        ...state,
        afterAddRole: payload
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
