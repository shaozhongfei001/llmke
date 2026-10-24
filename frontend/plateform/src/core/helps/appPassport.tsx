import { getTokenLocal } from "@root/src/apis/token";
import {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useState
} from "react";

interface AppInfoBase {
  name?: string;
  authors?: string[];
  version?: string;
  theme?: string;
  lang?: string;
  [key: string]: any;
}

interface UserInfoBase {
  userName?: string;
  role?: string;
  email?: string;
  avatar?: string;
  phone?: string;
  realName?: string;

  [key: string]: any;
}
interface AppPassportObj {
  appName: string;
  appInfo?: AppInfoBase;
  userInfo?: UserInfoBase;
  lastupdate?: number;
  isLoggedIn: boolean;
}

const defaultAppInfo = {
  authors: ["hanfeng zhang"],
  version: "0.0.1",
  theme: "light",
  lang: "cn_zh"
};
const defaultUserInfo = {
  userName: "未登录用户",
  email: "gitech@example.com",
  avatar: "www.example.com/placeholdAvator.png"
};
export class AppPassport {
  //除了token 存在cookie, 其他都存在localstore
  static appInfo: AppInfoBase = defaultAppInfo;
  static userInfo: UserInfoBase = defaultUserInfo;
  static pre_name: string = "gitech_ril:";
  constructor() {}
  static init(
    appName: string,
    info?: { appInfo?: AppInfoBase; userInfo?: UserInfoBase; token?: string },
    expire?: string
  ) {
    // 存储应用信息和用户信息到 localStorage
    const appPassportObj: AppPassportObj = {
      appName,
      appInfo: info?.appInfo ? info.appInfo : this.appInfo,
      userInfo: info?.userInfo ? info.userInfo : this.userInfo,
      lastupdate: Date.now(),
      isLoggedIn: this.isLogined(appName)
    };

    localStorage.setItem(
      `${this.pre_name}${appName}`,
      JSON.stringify(appPassportObj)
    );

    // 存储 token 到 Cookie
    if (info?.token) {
      this.setToken(appName, info.token, expire);
    }
  }

  static update(appName: string, data: Partial<AppInfoBase & UserInfoBase>) {
    const storedData = localStorage.getItem(`${this.pre_name}${appName}`);
    if (storedData) {
      const appPassportObj: AppPassportObj = JSON.parse(storedData);
      appPassportObj.userInfo = {
        ...appPassportObj.userInfo,
        ...data.userInfo
      };
      appPassportObj.appInfo = { ...appPassportObj.appInfo, ...data.appInfo };
      appPassportObj.lastupdate = Date.now();
      localStorage.setItem(
        `${this.pre_name}${appName}`,
        JSON.stringify(appPassportObj)
      );
    } else {
      localStorage.setItem(`${this.pre_name}${appName}`, JSON.stringify(data));
    }
  }

  static clear(appName: string) {
    // 移除 localStorage 中的应用信息和用户信息
    localStorage.removeItem(`${this.pre_name}${appName}`);

    // 移除 cookie 中的 token
    document.cookie = `${appName}_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
  }

  static getInfo(appName: string): AppPassportObj | undefined {
    const storedData = localStorage.getItem(`${this.pre_name}${appName}`);
    return storedData ? JSON.parse(storedData) : undefined;
  }

  static getUserInfo(appName: string): UserInfoBase | undefined {
    const appPassportObj = this.getInfo(appName);
    return appPassportObj ? appPassportObj.userInfo : undefined;
  }

  static getAppInfo(appName: string): AppInfoBase | undefined {
    const appPassportObj = this.getInfo(appName);
    return appPassportObj ? appPassportObj.appInfo : undefined;
  }

  static setToken(appName: string, token: string, expire?: string) {
    let cookieStr = `${appName}_token=${token}; path=/`;
    if (expire) {
      cookieStr += `; expires=${expire}`;
    }
    document.cookie = cookieStr;
  }

  static getToken(appName: string): string | null {
    return getTokenLocal();
    const name = `${appName}_token=`;
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.indexOf(name) === 0) {
        const token = cookie.substring(name.length, cookie.length);
        if (token && token !== "null" && token !== "undefined") {
          return token;
        }
      }
    }
    return null;
  }

  static freshToken(appName: string, newToken: string, expire?: string) {
    this.setToken(appName, newToken, expire);
  }

  static isLogined(appName: string): boolean {
    const token = this.getToken(appName);
    return token !== null;
  }
}

interface AppPassportContextType {
  appInfo: AppInfoBase;
  userInfo: UserInfoBase;
  update: (data: Partial<AppInfoBase & UserInfoBase>) => void;
  clear: () => void;
  getUserInfo: () => UserInfoBase | undefined;
  getAppInfo: () => AppInfoBase | undefined;
  getToken: () => string | null;
  freshToken: (newToken: string, expire?: string) => void;
  isLogined: () => boolean;
}

const defaultContext: AppPassportContextType = {
  appInfo: defaultAppInfo,
  userInfo: defaultUserInfo,
  update: () => {},
  clear: () => {},
  getUserInfo: () => undefined,
  getAppInfo: () => undefined,
  getToken: () => null,
  freshToken: () => {},
  isLogined: () => false
};

const AppPassportContext =
  createContext<AppPassportContextType>(defaultContext);
interface AppPassportProviderProps {
  name: string;
  children?: ReactNode;
}
export const AppPassportProvider: React.FC<AppPassportProviderProps> = ({
  children,
  name
}) => {
  const [appName] = useState(name);
  const [appInfo, setAppInfo] = useState<AppInfoBase>(defaultAppInfo);
  const [userInfo, setUserInfo] = useState<UserInfoBase>(defaultUserInfo);

  useEffect(() => {
    const storedInfo = AppPassport.getInfo(appName);
    if (storedInfo) {
      setAppInfo(storedInfo.appInfo || defaultAppInfo);
      setUserInfo(storedInfo.userInfo || defaultUserInfo);
    } else {
      AppPassport.init(appName, { appInfo, userInfo });
    }
  }, [appName]);

  const update = (data: Partial<AppInfoBase & UserInfoBase>) => {
    AppPassport.update(appName, data);
    setAppInfo((prev) => ({ ...prev, ...data }));
    setUserInfo((prev) => ({ ...prev, ...data }));
  };

  const clear = () => {
    AppPassport.clear(appName);
    setAppInfo(defaultAppInfo);
    setUserInfo(defaultUserInfo);
  };

  const getUserInfo = (): UserInfoBase | undefined =>
    AppPassport.getUserInfo(appName);
  const getAppInfo = (): AppInfoBase | undefined =>
    AppPassport.getAppInfo(appName);
  const getToken = (): string | null => AppPassport.getToken(appName);
  const freshToken = (newToken: string, expire?: string) =>
    AppPassport.freshToken(appName, newToken, expire);
  const isLogined = (): boolean => AppPassport.isLogined(appName);

  return (
    <AppPassportContext.Provider
      value={{
        appInfo,
        userInfo,
        update,
        clear,
        getUserInfo,
        getAppInfo,
        getToken,
        freshToken,
        isLogined
      }}
    >
      {children}
    </AppPassportContext.Provider>
  );
};

export const useAppPassport = () => useContext(AppPassportContext);
