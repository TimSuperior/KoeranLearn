/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172026",
        panel: "#f7f8f5",
        line: "#d9ded6",
        leaf: "#276749",
        sky: "#2563eb",
        sun: "#b7791f",
        coral: "#c2410c"
      },
      borderRadius: {
        app: "8px"
      }
    }
  },
  plugins: []
};
