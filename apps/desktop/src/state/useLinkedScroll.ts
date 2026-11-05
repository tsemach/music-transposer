import { useEffect, type RefObject } from "react";

export function useLinkedScroll(enabled: boolean, first: RefObject<HTMLElement | null>, second: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const top = first.current;
    const bottom = second.current;
    if (!enabled || !top || !bottom) return;
    let driver: HTMLElement = top;

    const follow = () => {
      if (driver === top) bottom.scrollTop = top.scrollTop + top.clientHeight;
      else top.scrollTop = Math.max(0, bottom.scrollTop - top.clientHeight);
    };
    const claim = (element: HTMLElement) => () => {
      driver = element;
    };
    const onScroll = (element: HTMLElement) => () => {
      if (driver === element) follow();
    };

    const bindings = [top, bottom].map((element) => ({
      element,
      claim: claim(element),
      scroll: onScroll(element),
    }));
    for (const { element, claim: onClaim, scroll } of bindings) {
      element.addEventListener("pointerenter", onClaim);
      element.addEventListener("wheel", onClaim, { passive: true });
      element.addEventListener("focusin", onClaim);
      element.addEventListener("scroll", scroll, { passive: true });
    }
    follow();
    return () => {
      for (const { element, claim: onClaim, scroll } of bindings) {
        element.removeEventListener("pointerenter", onClaim);
        element.removeEventListener("wheel", onClaim);
        element.removeEventListener("focusin", onClaim);
        element.removeEventListener("scroll", scroll);
      }
    };
  }, [enabled, first, second]);
}
