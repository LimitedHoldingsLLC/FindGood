const KEY = "findgood.adminKey";

export function getAdminKey(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(KEY);
}

export function setAdminKey(value: string) {
  window.sessionStorage.setItem(KEY, value);
}

export function clearAdminKey() {
  window.sessionStorage.removeItem(KEY);
}
