export const dbConnectStatus = {};

// 根据后端定义自行修改
export enum CONNECT_TYPES {
  NO_CONNECT = 0, //     0: "未连接",
  CONNECTED, //     1: "已连接",
  DISABLED //     2: "不可用",
}

export const dataTypes = {
  INTEGER: "integer",
  STRING: "String"
};

const moniApiRes = (data: any) => {
  return { success: true, data };
};

const databaseList = [
  {
    id: 1,
    name: "giengraph1",
    status: CONNECT_TYPES.CONNECTED,
    dbType: "mysql",
    useName: "root",
    createTime: "2025-03-07 10:04",
    dataDrivePack: "com.mysql.cjjdbc.Driver",
    description: "111这是一段描述这是一段很厉害的描述！这哪里厉害？？？",
    connectUrl:
      "jdbc:mysql://10.64.13.109:3306/giengraph?serverTimezone=Asia/Shanghai&useSSL=true&useUnicode=true&characterEncoding=utf8"
  },
  {
    id: 2,
    name: "giengraph2",
    status: CONNECT_TYPES.CONNECTED,
    dbType: "mysql",
    useName: "root",
    createTime: "2025-03-07 10:04",
    dataDrivePack: "com.mysql.cjjdbc.Driver",
    description: "222这是一段描述这是一段很厉害的描述！",
    connectUrl:
      "jdbc:mysql://10.64.13.109:3306/giengraph?serverTimezone=Asia/Shanghai&useSSL=true&useUnicode=true&characterEncoding=utf8"
  }
];

export const getMockDbDetailData = (id: number) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      const item = databaseList.find((i: any) => i.id === id);
      resolve(moniApiRes(item || databaseList[0]));
    }, 500);
  });
};

export const mockDatabaseList = [
  {
    id: 1,
    name: "giengraph1"
  },
  {
    id: 2,
    name: "giengraph2"
  }
];

const mockTables = [
  "account",
  "bank_transaction",
  "cust_acct",
  "customer",
  "交易流水表",
  "交易流水表1"
];

const mockLocalTables: any = {};
const mockRemoteTables: any = {};

mockDatabaseList.forEach((i: any) => {
  const { id, name } = i;
  mockLocalTables[String(id)] = [];
  mockRemoteTables[String(id)] = [];
});

mockDatabaseList.forEach((i: any, idx: number) => {
  const { id } = i;
  mockTables.forEach((tableName: string, index: number) => {
    if (index !== mockTables.length - 3) {
      mockLocalTables[String(id)].push({
        id: Number(`${id}${index}`),
        tableName: `${tableName}-${id}-${idx}`
      });
    }
    if (index < mockTables.length - 1) {
      mockRemoteTables[String(id)].push({
        id: Number(`${id}${index}`),
        tableName: `${tableName}-${id}-${idx}`
      });
    }
  });
});

export const getLocalTablesByDbId = (id: number) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      const item = mockLocalTables[id];
      resolve(moniApiRes(item || mockLocalTables[1]));
    }, 300);
  });
};

export const getRemoteTablesByDbId = (id: number) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      const item = mockRemoteTables[id];
      resolve(moniApiRes(item || mockRemoteTables[1]));
    }, 300);
  });
};

export const postSyncTables = ({ ids, id }: { ids: number[]; id: number }) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      const _local = mockLocalTables[id] || mockLocalTables[1];
      const _remote = mockRemoteTables[id] || mockRemoteTables[1];
      const _list = [
        ..._local.filter((i: any) => ids.includes(i.id)),
        ..._remote.filter((i: any) => ids.includes(i.id))
      ];
      mockLocalTables[String(id)] = [
        ...ids.map((id) => _list.find((i: any) => i.id === id))
      ];
      resolve(moniApiRes(true));
    }, 300);
  });
};

export const enableTypes = {
  ENABLE: 1,
  DISABLED: 0
};

const mockLocalTableDetail = [
  {
    id: 1,
    name: "account1",
    description: "这是一段描述这是一段很厉害的描述！这是一段相当厉害的描述！",
    properties: [
      {
        id: 1,
        key: "id",
        type: dataTypes.INTEGER,
        description: "数据的唯一标识（主键）",
        enable: enableTypes.ENABLE,
        relations: [
          {
            id: 1,
            databaseName: "giengraph2",
            tableName: "bank_transaction",
            keyName: "uuid"
          }
        ]
      },
      {
        id: 2,
        key: "sys_platform",
        type: dataTypes.STRING,
        description: "数据产生或使用的渠道",
        enable: enableTypes.ENABLE,
        relations: []
      },
      {
        id: 3,
        key: "sys_platform",
        type: dataTypes.STRING,
        description: "用户唯一标识，由系统生成",
        enable: enableTypes.ENABLE,
        relations: []
      },
      {
        id: 7,
        key: "xxxxxx",
        type: dataTypes.STRING,
        description: "",
        enable: enableTypes.DISABLED,
        relations: []
      },
      {
        id: 8,
        key: "xxxxxxxxxxxx",
        type: dataTypes.STRING,
        description: "",
        enable: enableTypes.DISABLED,
        relations: []
      }
    ]
  },
  {
    id: 2,
    name: "account2",
    description: "这是一段描述这是一段很厉害的描述",
    properties: [
      {
        id: 1,
        key: "id2",
        type: dataTypes.INTEGER,
        description: "2数据的唯一标识（主键）",
        enable: enableTypes.ENABLE,
        relations: [
          {
            id: 1,
            databaseName: "giengraph2",
            tableName: "bank_transaction",
            keyName: "uuid"
          }
        ]
      },
      {
        id: 2,
        key: "sys_platform2",
        type: dataTypes.STRING,
        description: "2数据产生或使用的渠道",
        enable: enableTypes.ENABLE,
        relations: []
      },
      {
        id: 3,
        key: "sys_platform2",
        type: dataTypes.STRING,
        description: "2用户唯一标识，由系统生成",
        enable: enableTypes.ENABLE,
        relations: []
      },
      {
        id: 7,
        key: "xxxxxx2",
        type: dataTypes.STRING,
        description: "2",
        enable: enableTypes.DISABLED,
        relations: []
      },
      {
        id: 8,
        key: "xxxxxxxxxxxx2",
        type: dataTypes.STRING,
        description: "2",
        enable: enableTypes.DISABLED,
        relations: []
      }
    ]
  }
];

const mockRemoteTableDetail = [
  {
    id: 1,
    name: "account1",
    description: "这是一段描述这是一段很厉害的描述！这是一段相当厉害的描述！",
    properties: [
      {
        id: 1,
        key: "id",
        type: dataTypes.INTEGER,
        description: "数据的唯一标识（主键）",
        enable: enableTypes.ENABLE,
        relations: [
          {
            id: 1,
            databaseName: "giengraph2",
            tableName: "bank_transaction",
            keyName: "uuid"
          }
        ]
      },
      {
        id: 2,
        key: "sys_platform",
        type: dataTypes.STRING,
        description: "数据产生或使用的渠道",
        enable: enableTypes.ENABLE,
        relations: []
      },
      {
        id: 3,
        key: "sys_platform",
        type: dataTypes.STRING,
        description: "用户唯一标识，由系统生成",
        enable: enableTypes.ENABLE,
        relations: []
      },
      {
        id: 4,
        key: "XXX",
        type: dataTypes.STRING,
        description: "",
        enable: enableTypes.DISABLED,
        relations: []
      },
      {
        id: 5,
        key: "XXXX",
        type: dataTypes.STRING,
        description: "",
        enable: enableTypes.DISABLED,
        relations: []
      },
      {
        id: 6,
        key: "XXXXXXX",
        type: dataTypes.STRING,
        description: "",
        enable: enableTypes.DISABLED,
        relations: []
      }
    ]
  },
  {
    id: 2,
    name: "account2",
    description: "这是一段描述这是一段很厉害的描述",
    properties: [
      {
        id: 1,
        key: "id2",
        type: dataTypes.INTEGER,
        description: "2数据的唯一标识（主键）",
        enable: enableTypes.ENABLE,
        relations: [
          {
            id: 1,
            databaseName: "giengraph2",
            tableName: "bank_transaction",
            keyName: "uuid"
          }
        ]
      },
      {
        id: 2,
        key: "sys_platform2",
        type: dataTypes.STRING,
        description: "2数据产生或使用的渠道",
        enable: enableTypes.ENABLE,
        relations: []
      },
      {
        id: 3,
        key: "sys_platform2",
        type: dataTypes.STRING,
        description: "2用户唯一标识，由系统生成",
        enable: enableTypes.ENABLE,
        relations: []
      },
      {
        id: 7,
        key: "xxxxxx2",
        type: dataTypes.STRING,
        description: "2",
        enable: enableTypes.DISABLED,
        relations: []
      },
      {
        id: 8,
        key: "xxxxxxxxxxxx2",
        type: dataTypes.STRING,
        description: "2",
        enable: enableTypes.DISABLED,
        relations: []
      }
    ]
  }
];

export const getTableDetailById = (id: number) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      const key = id % 2;
      const _localTableInfo = mockLocalTableDetail.find(
        (i: any) => i.id === Number(key) + 1
      );
      const _remoteTableInfo = mockRemoteTableDetail.find(
        (i: any) => i.id === Number(key) + 1
      );

      resolve(
        moniApiRes({
          local: { ..._localTableInfo },
          remote: { ..._remoteTableInfo }
        })
      );
    }, 300);
  });
};
