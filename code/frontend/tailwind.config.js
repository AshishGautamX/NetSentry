/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border, 214.3 31.8% 91.4%))",
        cyber: {
          darker: "#090d16",
          dark: "#0f172a",
          card: "#131c31",
          border: "#1e293b",
          accent: "#2563eb",
          accentHover: "#1d4ed8",
          text: "#f8fafc",
          muted: "#94a3b8"
        }
      }
    },
  },
  plugins: [],
}
