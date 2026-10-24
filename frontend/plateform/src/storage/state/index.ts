import { RematchDispatch, RematchRootState, init } from '@rematch/core'
import { RootModel, models } from './models'
import { global } from './models/global';


export const store = init({
  models
})

export {global}
export type Store = typeof store
export type Dispatch = RematchDispatch<RootModel>
export type RootState = RematchRootState<RootModel>