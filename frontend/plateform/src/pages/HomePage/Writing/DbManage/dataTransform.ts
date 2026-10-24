import dayjs from "dayjs";

const dbTypes: any = {
  0: "mysql",
  1: "mongo"
};
export const transformDbDetail = (data: any) => {
  //      {
  //     "id": 5,
  //     "name": "performance_schema",
  //     "account": "root",
  //     "password": "Gientech!2024",
  //     "type": 0,
  //     "driver": "com.mysql.cj.jdbc.Driver",
  //     "address": "127.0.0.1:3306",
  //     "creatorId": "1000",
  //     "modifiedBy": "1000",
  //     "gmtCreate": "2025-03-21 17:46:56",
  //     "gmtModified": "2025-03-21 17:46:56",
  //     "status": 1,
  //     "tables": [
  //         {
  //             "id": 12,
  //             "dbId": 5,
  //             "name": "accounts",
  //             "description": "",
  //             "enableStatus": 1,
  //             "ddlInfo": "CREATE TABLE `accounts` (\n  `USER` char(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,\n  `HOST` char(255) CHARACTER SET ascii COLLATE ascii_general_ci DEFAULT NULL,\n  `CURRENT_CONNECTIONS` bigint NOT NULL,\n  `TOTAL_CONNECTIONS` bigint NOT NULL,\n  UNIQUE KEY `ACCOUNT` (`USER`,`HOST`)\n) ENGINE=PERFORMANCE_SCHEMA DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci",
  //             "creatorId": "1000",
  //             "modifiedBy": "1000",
  //             "gmtCreate": "2025-03-21 17:46:56",
  //             "gmtModified": "2025-03-21 17:46:56",
  //             "status": 1
  //         }
  //     ]
  // }
  if (!data) {
    return {};
  }
  const {
    id,
    name,
    account,
    password,
    type,
    driver,
    address,
    creatorId,
    modifiedBy,
    gmtCreate,
    gmtModified,
    status,
    tables,
    description
  } = data;
  return {
    ...data,
    id,
    name,
    dbType: dbTypes[type],
    useName: account,
    createTime: gmtCreate ? dayjs(gmtCreate).format("YYYY-MM-DD HH:mm") : "--",
    dataDrivePack: driver,
    description: description || "--",
    connectUrl: address
  };
};

export const transformLocalTableList = (data: any) => {
  const { tables } = data;
  if (!tables) {
    return [];
  }
  return tables;
};

export const getQueryOnlineParams = (data: any) => {
  if (!data) {
    return {};
  }
  return {
    account: data?.account,
    address: data?.address,
    driver: data?.driver,
    id: data?.id,
    password: data?.password,
    type: data?.type
  };
};
