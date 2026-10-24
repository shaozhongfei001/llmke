import { HeadLessContainer } from './useHeadless';

export interface IUseLayouts {
  // isHeadLess?: boolean;
  isMoblie?: boolean;
  breakPoints?: string[];
}

export const useLayouts = (props?: IUseLayouts) => {
  return {
    HeadLessContainer: HeadLessContainer,
  };
};
