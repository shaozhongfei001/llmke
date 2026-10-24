import { Helmet } from "react-helmet";
import { useLocation } from "react-router-dom";
import { RouteItem } from "@/router/types";
import root from "@/router/config";
import React from "react";

// Helper function to find the matched route for nested routes
function findRoute(
  routes: RouteItem[],
  pathname: string
): RouteItem | undefined {
  for (const route of routes) {
    if (pathname.startsWith(route.path)) {
      if (pathname === route.path) {
        return route;
      } else {
        const nestedPath = pathname
          .slice(route.path.length)
          .replace(/^\/+/, "");
        if (route.children) return findRoute(route.children, nestedPath);
      }
    }
  }
  return undefined;
}

const DynamicHelmet: React.FC = () => {
  const location = useLocation();

  // Sample global meta information (if needed)
  const defaultMetaInfo = {
    // title: '中电金信',
    title: "",
    description: "默认描述信息"
  };

  // Find the matched route and its meta information
  const matchedRoute = findRoute(root, location.pathname);
  const metaInfo = matchedRoute?.meta || defaultMetaInfo;

  return (
    <>
      {/* Global default meta information */}
      <Helmet>
        <title>{metaInfo.title || defaultMetaInfo.title}</title>
        {Object.entries(metaInfo).map(([key, value]) => (
          <meta key={key} name={key} content={value} />
        ))}
      </Helmet>
    </>
  );
};

export default DynamicHelmet;
