import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F3EDE3",
        ink: "#1B1713",
        muted: "#6F675C",
        terracotta: "#C24A1A",
        forest: "#2C4A3E",
        gold: "#B8860B",
        card: "#FFF9F1",
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "Georgia", "serif"],
        sans: ["var(--font-outfit)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 18px 40px -24px rgba(27, 23, 19, 0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
