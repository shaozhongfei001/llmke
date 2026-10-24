import HomePage from "@root/src/pages/HomePage";
import LoginPage from "@root/src/pages/Login";
import { Suspense, lazy } from "react";
import Demo from "@root/src/pages/Demo";
import { systemRoutes } from "./routes";
import IntelligentChat from "@root/src/pages/HomePage/IntelligentChat";
import Writing from "@root/src/pages/HomePage/Writing";
import { Spin } from "antd";
import NotFound from "@root/src/pages/others/NotFound";
const Legal = lazy(() => import("@root/src/pages/others/Legal"));
import Module from "@root/src/pages/HomePage/Writing/Module";

const Indicators = lazy(
  () => import("@root/src/pages/HomePage/Writing/Indicators")
);

const Articulation = lazy(
  () => import("@root/src/pages/HomePage/Writing/Indicators/Articulation")
);

const Configuration = lazy(
  () => import("@root/src/components/KnowledgeBaseZh/Configuration/index")
);

const ChatsConfiguration = lazy(
  () =>
    import(
      "@root/src/pages/HomePage/IntelligentChat/Setting/Configuration/index"
    )
);

const KnowledgeAnalyBlock = lazy(
  () => import("@root/src/components/KnowledgeBaseZh/KnowledgeAnalyBlock/index")
);
const KnowledgeAnalyGraph = lazy(
  () => import("@root/src/components/KnowledgeBaseZh/KnowledgeAnalyGraph/index")
);
const KnowledgeAnalyVideo = lazy(
  () => import("@root/src/components/KnowledgeBaseZh/KnowledgeAnalyVideo/index")
);
const FAQ = lazy(
  () => import("@root/src/components/KnowledgeBaseZh/FAQ/index")
);

const SettingPage = lazy(
  () => import("@root/src/pages/HomePage/IntelligentChat/Setting")
);

const SettingDetailPage = lazy(
  () => import("@root/src/pages/HomePage/IntelligentChat/Setting/SettingDetail")
);

const AIChatsPage = lazy(
  () => import("@root/src/pages/HomePage/IntelligentChat/AIChat")
);

const AIChatComparisonPage = lazy(
  () => import("@root/src/pages/HomePage/IntelligentChat/AIChatComparison")
);

const FeedbackPage = lazy(
  () => import("@root/src/pages/HomePage/IntelligentChat/Feedback")
);

// const KnowledgeBaseManagePage = lazy(
//   () => import("@root/src/pages/HomePage/IntelligentChat/KnowledgeBaseManager")
// );

const KnowledgeBaseManager = lazy(
  () => import("@root/src/pages/HomePage/IntelligentChat/KnowledgeBase")
);

const Detail = lazy(
  () => import("@root/src/components/KnowledgeBaseZh/Detail")
);
const ResourceDetail = lazy(
  () =>
    import(
      "@root/src/pages/HomePage/Writing/ResourceM/compoments/ResourceDetail"
    )
);

const DatabaseDetail = lazy(
  () => import("@root/src/pages/HomePage/Writing/DbManage/detail")
);

const AssistantConfig = lazy(
  () =>
    import(
      "@root/src/pages/HomePage/IntelligentChat/Setting/SettingDetail/config.tsx"
    )
);

// const KnowledgeBaseDetailPage = lazy(
//   () =>
//     import(
//       "@root/src/pages/HomePage/IntelligentChat/KnowledgeBaseManager/KnowledgeBaseDetail"
//     )
// );

const DocWritingListPage = lazy(
  () => import("@root/src/pages/HomePage/Writing/DocWriting/index")
);

const DocWritingDetailPage = lazy(
  () => import("@root/src/pages/HomePage/Writing/DocWriting/Writing/index")
);

const DocWritingHistoryM = lazy(
  () => import("@root/src/pages/HomePage/Writing/HistoryM")
);

const DocWritingResourceM = lazy(
  () => import("@root/src/pages/HomePage/Writing/ResourceM/index")
);

const DocWritingTemplateM = lazy(
  () => import("@root/src/pages/HomePage/Writing/TemplateM")
);

const EditTemplate = lazy(
  () => import("@root/src/pages/HomePage/Writing/EditTemplate")
);

const EditSegmentedTemplate = lazy(
  () => import("@root/src/pages/HomePage/Writing/EditSegmentedTemplate")
);
const KnowledgeSearch = lazy(
  () => import("@/pages/HomePage/IntelligentChat/KnowledgeSearch")
);
const contentStyle: React.CSSProperties = {
  padding: 50,
  background: "rgba(0, 0, 0, 0.05)",
  borderRadius: 4
};
// 章节组件
const ChapterModule = lazy(
  () => import("@/pages/HomePage/Writing/Module/ChapterModule")
);
const AnalyzeModule = lazy(
  () => import("@/pages/HomePage/Writing/Module/AnalyzeModule")
);
const AnalyzeDetail = lazy(
  () => import("@/pages/HomePage/Writing/Module/AnalyzeDetail")
);

const getSuspenceWrap = (el: React.ReactNode) => {
  return (
    <Suspense
      fallback={
        <div className="w-full h-full flex justify-center items-center">
          <Spin tip="加载中……" size="large">
            <div className="w-[200px]"></div>
          </Spin>
        </div>
      }
    >
      {el}
    </Suspense>
  );
};
const SensitiveList = lazy(
  () => import("@root/src/pages/HomePage/Writing/SensitiveWords/index.tsx")
);
const SensitiveDetail = lazy(
  () => import("@root/src/pages/HomePage/Writing/SensitiveWords/detail.tsx")
);
const SensitiveWords = lazy(
  () => import("@root/src/pages/HomePage/IntelligentChat/SensitiveWords/index")
);
const SensitiveWordsDetail = lazy(
  () =>
    import(
      "@root/src/pages/HomePage/IntelligentChat/SensitiveWords/sensitiveDetail"
    )
);

const ExtractRes = lazy(
  () => import("@root/src/pages/HomePage/Writing/ResourceM/ExtractRes")
);

const MdTestDemo = lazy(() => import("@/pages/Demo/MdTestDemo"));

const DatabasePage = lazy(
  () => import("@root/src/pages/HomePage/IntelligentChat/Database/index.tsx")
);

const DatabaseId = lazy(
  () => import("@root/src/pages/HomePage/IntelligentChat/Database/id.tsx")
);

const DatabaseTableId = lazy(
  () => import("@root/src/pages/HomePage/IntelligentChat/Database/data.tsx")
);

//除了主页面，其他页面使用lazy
const root = [
  {
    path: "/login",
    element: <LoginPage />
  },
  {
    path: "/legal",
    element: getSuspenceWrap(<Legal />)
  },
  {
    path: "/",
    element: <HomePage />,
    meta: {
      title: "首页"
    },
    children: [
      {
        path: "chats",
        element: getSuspenceWrap(<IntelligentChat />),
        children: [
          {
            path: "main",
            element: getSuspenceWrap(<AIChatsPage />)
          },
          {
            path: "comparison",
            element: getSuspenceWrap(<AIChatComparisonPage />)
          },
          // {
          //   path: "main/legacy",
          //   element: getSuspenceWrap(<ChatsPage />)
          // },
          // {
          //   path: "main",
          //   element: getSuspenceWrap(<ChatsPage />)
          // },
          {
            path: "knowledgeBase",
            element: getSuspenceWrap(<KnowledgeBaseManager />)
          },
          {
            path: "knowledgeBase/:id",
            element: getSuspenceWrap(<Detail />)
          },
          {
            path: "knowledgeBase/configuration/:id",
            element: getSuspenceWrap(<Configuration kbInfo={{}} />)
          },
          {
            path: "knowledgeBase/KnowledgeAnalyBlock/:id/:fileId",
            element: getSuspenceWrap(<KnowledgeAnalyBlock />)
          },
          {
            path: "knowledgeBase/KnowledgeAnalyVideo/:id/:fileId",
            element: getSuspenceWrap(<KnowledgeAnalyVideo />)
          },
          {
            path: "knowledgeBase/KnowledgeAnalyGraph/:id",
            element: getSuspenceWrap(<KnowledgeAnalyGraph />)
          },
          {
            path: "knowledgeBase/:knowledgeBaseId/faq/:id",
            element: getSuspenceWrap(<FAQ />)
          },
          // {
          //   path: "knowledgeBaseZh",
          //   element: getSuspenceWrap(<KnowledgeBaseManageZh />),
          // },
          {
            path: "database",
            element: <DatabasePage />,
            meta: {
              title: "数据库"
            }
          },
          {
            path: "database/:dbId",
            element: <DatabaseId />,
            meta: {
              title: "数据库详情"
            }
          },
          {
            path: "database/:dbId/table/:fileId",
            element: <DatabaseTableId />,
            meta: {
              title: "数据表详情"
            }
          },
          {
            path: "setting",
            element: getSuspenceWrap(<SettingPage />)
          },
          {
            path: "setting/edit/:id",
            element: getSuspenceWrap(<SettingDetailPage />)
          },
          {
            path: "setting/config",
            element: getSuspenceWrap(<AssistantConfig />)
          },
          {
            path: "setting/config/:id",
            element: getSuspenceWrap(<AssistantConfig />)
          },
          {
            path: "setting/config/share/:id",
            element: getSuspenceWrap(<AssistantConfig isShare={true} />)
          },
          {
            path: "setting/config/view/:id",
            element: getSuspenceWrap(<AssistantConfig disabled={true} />)
          },
          {
            path: "setting/chatsConfiguration/:id",
            element: getSuspenceWrap(<ChatsConfiguration />)
          },
          {
            path: "setting/create",
            element: getSuspenceWrap(<SettingDetailPage />)
          },
          {
            path: "feedback",
            element: getSuspenceWrap(<FeedbackPage />)
          },
          {
            path: "sensitiveWords",
            element: getSuspenceWrap(<SensitiveWords />)
          },
          {
            path: "sensitiveWords/detail/:id",
            element: getSuspenceWrap(<SensitiveWordsDetail />)
          },
          {
            path: "sensitiveWords/add/:id",
            element: getSuspenceWrap(<SensitiveWordsDetail />)
          },
          {
            path: "knowledgeSearch",
            element: getSuspenceWrap(<KnowledgeSearch />)
          }
        ]
      },
      {
        path: "docWriting",
        element: getSuspenceWrap(<Writing />),
        children: [
          {
            path: "main",
            element: getSuspenceWrap(<DocWritingListPage />)
          },
          {
            path: "docs/:id",
            element: getSuspenceWrap(<DocWritingDetailPage />)
          },
          {
            path: "docs/:id/:editorType",
            element: getSuspenceWrap(<DocWritingDetailPage />)
          },
          {
            path: "template",
            element: getSuspenceWrap(<DocWritingTemplateM />)
          },
          // {
          //   path: "template/:id",
          //   element: getSuspenceWrap(<EditTemplate />)
          // },
          {
            path: "template/:id",
            element: getSuspenceWrap(<EditTemplate />)
          },
          {
            path: "template/segment/:id",
            element: getSuspenceWrap(<EditSegmentedTemplate />)
          },
          {
            path: "sensitiveWords",
            element: getSuspenceWrap(<SensitiveList />)
          },
          {
            path: "sensitiveWords/detail/:detailId",
            element: getSuspenceWrap(<SensitiveDetail />)
          },
          {
            path: "sensitiveWords/add/:detailId",
            element: getSuspenceWrap(<SensitiveDetail />)
          },
          {
            path: "template/version/:version/:id",
            element: getSuspenceWrap(<EditTemplate />)
          },
          {
            path: "template/version/segment/:version/:id",
            element: getSuspenceWrap(<EditSegmentedTemplate />)
          },
          {
            path: "resource",
            element: getSuspenceWrap(<DocWritingResourceM />)
          },
          {
            path: "resource/:id",
            element: getSuspenceWrap(<ResourceDetail />)
          },
          {
            path: "resource/db/:id",
            element: getSuspenceWrap(<DatabaseDetail />)
          },
          {
            path: "resource/KnowledgeAnalyBlock/:id/:fileId",
            element: getSuspenceWrap(<KnowledgeAnalyBlock isCec={true} />)
          },
          {
            path: "resource/indicatorExtractRes/:id/:fileId",
            element: getSuspenceWrap(<ExtractRes />)
          },

          {
            path: "history",
            element: getSuspenceWrap(<DocWritingHistoryM />)
          },
          {
            path: "component",
            element: getSuspenceWrap(<Module />),
            children: [
              {
                path: "chapter",
                element: getSuspenceWrap(<ChapterModule />)
              },
              {
                path: "analyze",
                element: getSuspenceWrap(<AnalyzeModule />)
              },
              {
                path: "analyze/:id",
                element: getSuspenceWrap(<AnalyzeDetail />)
              }
            ]
          },
          {
            path: "indicator",
            element: getSuspenceWrap(<Indicators />),
            children: [
              {
                path: "articulation",
                element: getSuspenceWrap(<Articulation />)
              }
            ]
          }
        ]
      },
      //...managerRoutes,
      ...systemRoutes
    ]
  },
  {
    path: "/not-found",
    element: <NotFound />
  },
  {
    path: "/demo",
    element: <Demo />
  },
  {
    path: "mdDemo",
    element: getSuspenceWrap(<MdTestDemo />)
  }
];

export default root;
