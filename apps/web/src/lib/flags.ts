export type FlagName =
  | "deal_score"
  | "maps"
  | "accounts"
  | "community_verification"
  | "flash_deals"
  | "restaurant_portal"
  | "ai_extraction";

export function isEnabled(flags: Record<string, boolean> | undefined, name: FlagName): boolean {
  return Boolean(flags?.[name]);
}
