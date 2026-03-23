/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 莫兰迪灰蓝色系 - 高级简约配色
        primary: {
          50: '#F5F7FA',
          100: '#E8EDF4',
          200: '#D4DEEB',
          300: '#BCC8D9',
          400: '#A8B5C9',
          500: '#8B9BB4',
          600: '#6E7F9F',
          700: '#5A6B8A',
          800: '#4A5A75',
          900: '#3D4A61',
        },
        gradient: {
          from: '#A8B5C9',
          to: '#C4CDD9',
        },
        // 莫兰迪状态色 - 柔和不刺眼
        success: {
          50: '#F0F7F4',
          100: '#E0F0E8',
          200: '#C3E3D4',
          300: '#9CD1B8',
          400: '#72BE9C',
          500: '#52AB84',
          600: '#3E966E',
          700: '#327D5C',
          800: '#2B6650',
          900: '#265646',
        },
        warning: {
          50: '#FEF9F0',
          100: '#FDF2E0',
          200: '#FBE5C3',
          300: '#F8D49C',
          400: '#F5C172',
          500: '#F2AB52',
          600: '#E9963E',
          700: '#D87B2F',
          800: '#C26628',
          900: '#A85624',
        },
        danger: {
          50: '#FEF5F5',
          100: '#FDE8E8',
          200: '#FBD1D1',
          300: '#F8B0B0',
          400: '#F58A8A',
          500: '#F26B6B',
          600: '#E94E4E',
          700: '#D13A3A',
          800: '#BB3232',
          900: '#A32B2B',
        },
        info: {
          50: '#F0F5F9',
          100: '#E0EBF4',
          200: '#C3D9EB',
          300: '#9CC1DF',
          400: '#72A9D3',
          500: '#5292C8',
          600: '#3E7DB3',
          700: '#32669A',
          800: '#2B5584',
          900: '#264870',
        },
      },
      boxShadow: {
        'soft': '0 2px 8px rgba(107, 114, 128, 0.08)',
        'soft-hover': '0 4px 12px rgba(107, 114, 128, 0.12)',
        'elegant': '0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.06)',
        'elegant-hover': '0 4px 6px rgba(0, 0, 0, 0.05), 0 2px 4px rgba(0, 0, 0, 0.08)',
      },
      borderRadius: {
        'none': '0',
      },
    },
  },
  plugins: [],
}
