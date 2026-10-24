import axios$ from "@root/src/apis";
const prefix = '/proxy'

export const regist = async(params:any) => {
   try {
    const res: any = await axios$.post(
      `${prefix}/auth/user/regist`,
      params
    );
    resInfo("regist", res);
    if (res) return res.data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

export const login = async(params:any) => {
   try {
    const res: any = await axios$.post(
      `${prefix}/auth/user/login`,
      params
    );
    resInfo("login", res);
    if (res) return res.data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

export const api_getKaptchaImage = async() => {
   try {
    const res: any = await axios$.get(
      `${prefix}/auth/user/kaptcha`, {
        responseType: 'arraybuffer', 
        headers: { Accept: '*/*', 'Content-Type': 'application/json' },
      }
    );
    resInfo("api_getKaptchaImage", res);
    if (res) return res;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const resInfo = (name: string, res: any) => {
  console.log(`${name}---------->`, res);
};