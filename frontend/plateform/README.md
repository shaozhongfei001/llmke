# search_agent

检索模型

how to run this repo:

1.clone 仓库 https://github.com/mxm-web-develop/module_dev

```
// 依次执行
npm install
npm run build:lib
cd libs/
npm link
```

2.clone https://github.com/mxm-web-develop/vite_rt

```
// 依次执行
npm install
npm run build:lib
cd libs/
npm link
```

然后在search_agent仓库执行

```
npm unlink gitech_ui gitech_ui_chat
npm link gitech_ui gitech_ui_chat
```

node --max_old_space_size=8192 node_modules/vite/bin/vite.js build --mode production
