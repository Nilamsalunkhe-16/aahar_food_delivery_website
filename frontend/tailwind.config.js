/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        aahar: {
          50: '#eefbf5',
          100: '#d7f5e6',
          200: '#afe8cc',
          300: '#78d5ad',
          400: '#43bd8a',
          500: '#159a69',
          600: '#0c8058',
          700: '#086548',
          800: '#07513a',
          900: '#064332'
        }
      },
      boxShadow: {
        soft: '0 12px 35px rgba(6,67,50,.08)'
      }
    }
  },
  plugins: []
}
