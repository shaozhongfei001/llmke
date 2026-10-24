import { useEffect } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

function Writing() {
  const location = useLocation();
  const navigator = useNavigate();
  useEffect(() => {
    if (
      location.pathname === "/docWriting" ||
      location.pathname === "docWriting"
    ) {
      navigator("/docWriting/main");
    }
  }, [location]);
  return <Outlet />;
}

export default Writing;
