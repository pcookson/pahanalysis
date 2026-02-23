/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        panel: "0 24px 80px -24px rgba(6, 24, 44, 0.55)",
      },
    },
  },
  plugins: [],
};
