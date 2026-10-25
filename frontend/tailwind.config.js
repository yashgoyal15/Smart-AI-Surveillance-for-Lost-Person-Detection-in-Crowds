/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // custom colors used across the dashboard for status badges
        "brand-green": "#10b981",
        "brand-amber": "#f59e0b",
      },
    },
  },
  plugins: [],
};
