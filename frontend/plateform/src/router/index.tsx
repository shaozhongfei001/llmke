import { Navigate, RouteObject, useRoutes } from "react-router-dom";
import { RouteItem } from "./types";
import { ReactElement } from "react";
import root from "./config";
import React from "react";
import DynamicHelmet from "./DynamicHelmet";
import { useRoutesWithMiddleware } from "react-router-middleware-plus";

const Placeholder = () => <>404</>;

function prepareRoutes(routes: RouteItem[], extraProps = {}): RouteItem[] {
  // process children routes in the map function
  const preparedRoutes = routes.map((route) => {
    const routeWithExtraProps = { ...route, ...extraProps };
    // check if the route has children
    if (route.children) {
      routeWithExtraProps.children = prepareRoutes(route.children, extraProps);
    }
    if (route.index) {
      // If it is, set the path to an empty string
      routeWithExtraProps.path = "";
    } else {
      route.index = false;
    }

    if (route.element) {
      routeWithExtraProps.element = React.cloneElement(
        route.element as ReactElement,
        extraProps
      );
    } else {
      routeWithExtraProps.element = <Placeholder />;
    }
    return routeWithExtraProps;
  });

  return preparedRoutes;
}

const preparedRoutes = prepareRoutes(root);

export function MyRoutes() {
  const routes = useRoutesWithMiddleware(preparedRoutes as RouteObject[]);
  return routes ? (
    <>
      <DynamicHelmet />
      {routes}
    </>
  ) : (
    <Navigate to="/not-found" />
  );
}
