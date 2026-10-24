import { useEffect } from "react";
import { useDispatch } from "react-redux";
import {
  Outlet,
  useLoaderData,
  useLocation,
  useNavigate,
} from "react-router-dom";
let curLocation: any = "";
function IntelligentChat() {
  const location = useLocation();
  const dispatch = useDispatch();
  const navigator = useNavigate();
  useEffect(() => {
    if (location.pathname === "/chats" || location.pathname === "chats") {
      navigator("/chats/main");
    }
    dispatch.global.SET_PREV_ROUTE(curLocation);
    curLocation = location;
  }, [location]);
  return <Outlet />;
}

export default IntelligentChat;
