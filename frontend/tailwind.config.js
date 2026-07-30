/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#10131A",
        "ink-soft": "#5B6472",
        canvas: "#F7F8FA",
        surface: "#FFFFFF",
        border: "#E4E7EC",
        accent: {
          DEFAULT: "#2F5DD3",
          dark: "#1F44A8",
          soft: "#EAF0FD",
        },
        status: {
          pending: "#8A93A3",
          running: "#2F5DD3",
          success: "#1F9D6B",
          warning: "#C9821E",
          error: "#C4432B",
        },
      },
      fontFamily: {
        display: ["var(--font-space-grotesk)", "sans-serif"],
        body: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};