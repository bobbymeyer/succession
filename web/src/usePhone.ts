import { useEffect, useState } from "react";

/** A phone held upright: the table is laid out to fit one screen. */
export const PHONE = "(max-width: 600px)";

export function usePhone(): boolean {
  const [phone, setPhone] = useState(() => window.matchMedia?.(PHONE).matches ?? false);
  useEffect(() => {
    const m = window.matchMedia?.(PHONE);
    if (!m) return;
    const change = () => setPhone(m.matches);
    m.addEventListener("change", change);
    return () => m.removeEventListener("change", change);
  }, []);
  return phone;
}
