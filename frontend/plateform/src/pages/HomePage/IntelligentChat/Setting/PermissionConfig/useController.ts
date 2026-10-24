import { useEffect, useState } from "react";
import { getGroups } from "./service";

const UseConfigController = () => {
  const [tabKey, setTabKey] = useState("2");
  const tabChange = (key: string) => {
    setTabKey(key);
  };

  return { tabKey, tabChange };
};
export default UseConfigController;
