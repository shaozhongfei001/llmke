import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";

const api_getkaptchaSix = async () => {
  try {
    const res: any = await axios$.get(
      `${getUrlPrefix()}/auth/kaptcha/kaptchaSix`,
      {
        responseType: "arraybuffer",
        headers: { Accept: "*/*", "Content-Type": "application/json" }
      }
    );
    if (res) return res;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const api_getKaptchaImage = async () => {
  try {
    const res: any = await axios$.get(`${getUrlPrefix()}/auth/user/kaptcha`, {
      responseType: "arraybuffer",
      headers: { Accept: "*/*", "Content-Type": "application/json" }
    });
    if (res) return res;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const api_saveUserSecurityQuestion = async (params: any) => {
  try {
    const res: any = await axios$.post(
      `${getUrlPrefix()}/auth/userSecurityQuestion/save`,
      params
    );
    if (res) return res;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

// auth/userSecurityQuestion/findByUserName/admin
const api_findByUserName = async (user: string) => {
  try {
    const res: any = await axios$.get(
      `${getUrlPrefix()}/auth/userSecurityQuestion/findByUserName/${user}`
    );
    if (res) return res;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const api_validateSecurityQuestion = async (params: any) => {
  try {
    const res: any = await axios$.post(
      `${getUrlPrefix()}/auth/userSecurityQuestion/validateSecurityQuestion`,
      params
    );
    if (res) return res;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const api_updatePasswordByQuestion = async (params: any) => {
  try {
    const res: any = await axios$.post(
      `${getUrlPrefix()}/auth/userSecurityQuestion/updatePasswordByQuestion`,
      params
    );
    if (res) return res;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const api_updateUserSecurityQuestion = async (params: any) => {
  try {
    const res: any = await axios$.post(
      `${getUrlPrefix()}/auth/userSecurityQuestion/update`,
      params
    );
    if (res) return res;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const api_resetPassword = async (params: any) => {
  try {
    const res: any = await axios$.post(
      `${getUrlPrefix()}/auth/userAdmin/resetPassword`,
      params
    );
    if (res) return res;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const api_queryResetPassword = async ({
  userId,
  verifyCode
}: {
  userId: string;
  verifyCode: string;
}) => {
  try {
    const res: any = await axios$.get(
      `${getUrlPrefix()}/auth/userAdmin/queryResetPassword/${userId}/${verifyCode}`
    );
    if (res) return res;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const userLogout = async () => {
  try {
    const res = await axios$.post(`${getUrlPrefix()}/auth/user/logout`);
    return res;
  } catch (e) {
    console.log("e", e);
  }
};

const api_forceUpdatePassword = async (params: any) => {
  try {
    const res: any = await axios$.post(
      `${getUrlPrefix()}/auth/user/forceUpdatePassword`,
      params
    );
    if (res) return res;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

export {
  api_getKaptchaImage,
  api_saveUserSecurityQuestion,
  api_getkaptchaSix,
  api_findByUserName,
  api_validateSecurityQuestion,
  api_updatePasswordByQuestion,
  api_updateUserSecurityQuestion,
  api_resetPassword,
  api_queryResetPassword,
  userLogout,
  api_forceUpdatePassword
};
