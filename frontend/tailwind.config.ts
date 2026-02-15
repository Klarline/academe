import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        sage: {
          50: '#F8FAF9',
          100: '#EBF4DD',
          200: '#D4E7C5',
          300: '#B8D8A8',
          400: '#90AB8B',
          500: '#5A7863',
          600: '#4A6352',
          700: '#3B4E42',
          800: '#2D3A32',
          900: '#1F2722',
        },
        dark: {
          DEFAULT: '#3B4953',
          50: '#F8F9FA',
          100: '#E9ECEF',
          200: '#DEE2E6',
          300: '#CED4DA',
          400: '#ADB5BD',
          500: '#6C757D',
          600: '#495057',
          700: '#3B4953',
          800: '#2D3640',
          900: '#1A1F26',
        },
        background: {
          DEFAULT: '#F8FAFC',
        }
      },
      fontFamily: {
        playfair: ['"Playfair Display"', 'serif'],
        sans: ['system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
