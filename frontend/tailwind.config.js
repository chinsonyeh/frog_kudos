/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        frog: {
          50: 'rgb(var(--color-frog-50) / <alpha-value>)',
          100: 'rgb(var(--color-frog-100) / <alpha-value>)',
          200: 'rgb(var(--color-frog-200) / <alpha-value>)',
          300: 'rgb(var(--color-frog-300) / <alpha-value>)',
          400: 'rgb(var(--color-frog-400) / <alpha-value>)',
          500: 'rgb(var(--color-frog-500) / <alpha-value>)',
          600: 'rgb(var(--color-frog-600) / <alpha-value>)',
          700: 'rgb(var(--color-frog-700) / <alpha-value>)',
          800: 'rgb(var(--color-frog-800) / <alpha-value>)',
          900: 'rgb(var(--color-frog-900) / <alpha-value>)',
        },
      },
    },
  },
  plugins: [],
}
