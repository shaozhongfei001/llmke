process.env.NODE_ENV === 'development' && console.log('[CONFIG]');
const storeName = 'saic_store';
interface SearchItem {
  id: string;
  text: string;
  timedata: string;
}
export interface UserInfo {
  empNo: string,
  gmtCreate: string,
  id: string,
  ip: string,
  onlineTime: string,
  roleIds: string,
  roles: string,
  stat: number,
  token: string,
  url: string,
  userEmail: string,
  userIphone: string,
  userName: string,
  userRealname: string,
}
export type SaiclStoreType = {
  historySearchList: SearchItem[];
  userInfo: UserInfo;
  menu: any[]
};

const InitiaSaiclStore: SaiclStoreType = {
  historySearchList: [],
  userInfo: {} as UserInfo, // 注意：这样的断言可能会导致运行时错误，因为它只是一个空对象，不符合 UserInfo 的完整定义。
  menu: []
};

export {
  storeName,
  InitiaSaiclStore
}