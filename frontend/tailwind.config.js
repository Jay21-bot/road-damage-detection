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
        surveillance: {
          900: '#0a0d14',
          800: '#111827',
          700: '#1f2937',
          600: '#374151',
          accent: '#00e676',
          damage: '#ff2a55',
          object: '#00e5ff'
        }
      }
    },
  },
  plugins: [],
}
