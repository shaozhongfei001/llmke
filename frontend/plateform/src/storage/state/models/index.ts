import { builder } from './application/builder'
import { Models } from '@rematch/core'
import { manager } from './application/manager';
import { analizer } from './application/analizer'
import { global } from './global';

export interface RootModel extends Models<RootModel> {
  manager: typeof manager
  analizer: typeof analizer
  builder: typeof builder
  global: typeof global
}

export const models: RootModel = { manager, builder, analizer, global }
