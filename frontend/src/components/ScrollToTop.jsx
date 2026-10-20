import { useEffect } from "react";
import { useLocation, useNavigationType } from "react-router-dom";

// Start new routes at the top; keep browser back/forward restoration and #anchors intact.
export function ScrollToTop() {
  const { pathname, hash } = useLocation();
  const navType = useNavigationType();
  useEffect(() => {
    if (navType !== "POP" && !hash) {
      window.scrollTo(0, 0);
    }
  }, [pathname, hash, navType]);
  return null;
}
