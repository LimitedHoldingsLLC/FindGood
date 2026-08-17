const KEY = "findgood.adminToken";

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(KEY);
}

export function setAdminToken(value: string) {
  window.sessionStorage.setItem(KEY, value);
}

export function clearAdminToken() {
  window.sessionStorage.removeItem(KEY);
}
