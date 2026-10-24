import axios$ from "@root/src/apis";
import { getUrlPrefix } from "@root/src/core/helps";

const prefix = `${getUrlPrefix()}/sensitive`;

const getLibraryList = async (params: any) => {
  try {
    const res: any = await axios$.get(
      `${prefix}/library?${new URLSearchParams(params).toString()}`
    );
    resInfo("getLibraryList", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const getLibraryListById = async (params: any) => {
  try {
    const res: any = await axios$.get(`${prefix}/library/${params.id}`);
    resInfo("getLibraryListById", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const createLibrary = async (params: any) => {
  try {
    const res: any = await axios$.post(`${prefix}/library`, params);
    resInfo("createLibrary", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const updateLibrary = async (params: any) => {
  try {
    const res: any = await axios$.put(`${prefix}/library/${params.id}`, params);
    resInfo("updateLibrary", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

const deleteLibrary = async (id: any) => {
  try {
    const res: any = await axios$.delete(`${prefix}/library/${id}`);
    resInfo("deleteLibrary", res);
    const { success, data } = res;
    if (success) return data;
    return false;
  } catch (e) {
    console.log("e", e);
    return false;
  }
};

export {
  getLibraryList,
  createLibrary,
  updateLibrary,
  deleteLibrary,
  getLibraryListById
};

const resInfo = (name: string, res: any) => {
  console.log(`${name}---------->`, res);
};
