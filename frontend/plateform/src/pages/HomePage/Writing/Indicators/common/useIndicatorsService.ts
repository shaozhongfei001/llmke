import axios$ from "@root/src/apis";

const prefix = "/cecProxy/dw";

const apiPath = {
  indicatorCategory: "/indicator/category",
  indicator: "/indicator"
};

const paramSerialize = (params: any) => {
  const list: Array<string> = [];
  Object.keys(params).forEach((key) => {
    if (params[key]) {
      list.push(`${key}=${params[key]}`);
    }
  });
  return list.length ? `?${list.join("&")}` : "";
};

// 获取指标分类树
export const getIndicatorCategory = (params: any = {}) => {
  const _params = {
    // full: true,
    // canApply: false,
    ...params
  };
  return new Promise((resolve, reject) => {
    axios$
      .get(`${prefix}${apiPath.indicatorCategory}${paramSerialize(_params)}`)
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

export const editIndicatorCategory = (data: any = {}) => {
  const id = data.id;
  delete data.id;
  return new Promise((resolve, reject) => {
    axios$
      .put(`${prefix}${apiPath.indicatorCategory}/${id}`, {
        ...data
      })
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

export const addIndicatorCategory = (data: any = {}) => {
  return new Promise((resolve, reject) => {
    axios$
      .post(`${prefix}${apiPath.indicatorCategory}`, {
        ...data
      })
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

export const deleteIndicatorCategory = (id: string) => {
  return new Promise((resolve, reject) => {
    axios$
      .delete(`${prefix}${apiPath.indicatorCategory}/${id}`)
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

// 获取指标分类树
export const getIndicatorTree = (params: any = {}) => {
  return new Promise((resolve, reject) => {
    axios$
      .get(`${prefix}${apiPath.indicator}${paramSerialize(params)}`)
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

export const addIndicator = (data: any) => {
  return new Promise((resolve, reject) => {
    axios$
      .post(`${prefix}${apiPath.indicator}`, { ...data })
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

export const editIndicator = (data: any) => {
  const id = data.id;
  delete data.id;
  return new Promise((resolve, reject) => {
    axios$
      .put(`${prefix}${apiPath.indicator}/${id}`, { ...data })
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

export const deleteIndicator = (id: string) => {
  return new Promise((resolve, reject) => {
    axios$
      .delete(`${prefix}${apiPath.indicator}/${id}`)
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

export const copyIndicator = (id: string) => {
  return new Promise((resolve, reject) => {
    axios$
      .get(`${prefix}${apiPath.indicator}/${id}/copy`)
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

export const moveIndicator = (data: any) => {
  const id = data.id;
  delete data.id;
  return new Promise((resolve, reject) => {
    axios$
      .post(`${prefix}${apiPath.indicator}/${id}/move`, { ...data })
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

export const getIndicatorDetail = (id: string) => {
  return new Promise((resolve, reject) => {
    axios$
      .get(`${prefix}${apiPath.indicator}/${id}`)
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

// 获取勾稽校验列表
export const getIndicatorCheck = (params: any) => {
  return new Promise((resolve, reject) => {
    axios$
      .get(`${prefix}${apiPath.indicator}/check${paramSerialize(params)}`)
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

// 修改或新增勾稽校验数据
export const saveIndicatorCheck = (data: any) => {
  return new Promise((resolve, reject) => {
    axios$
      .post(`${prefix}${apiPath.indicator}/check`, { ...data })
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};

export const deleteIndicatorCheck = (id: string) => {
  return new Promise((resolve, reject) => {
    axios$
      .delete(`${prefix}${apiPath.indicator}/check/${id}`)
      .then((res: any) => {
        const { data, success, errorMsg } = res;
        if (success && data) {
          resolve(data);
        } else {
          reject(errorMsg);
        }
      })
      .catch((e) => {
        const { message } = e;
        reject(message);
      });
  });
};
