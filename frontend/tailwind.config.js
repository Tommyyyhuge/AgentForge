/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // AgentForge brand aliases kept for compatibility with existing UI.
        forge: {
          50:  '#eef2ff',
          100: '#dbe4ff',
          200: '#bac8ff',
          300: '#86a5ff',
          400: '#4a72ff',
          500: '#1a3fff',
          600: '#0b23cc',
          700: '#091aa3',
          800: '#0c1886',
          900: '#101a6e',
          950: '#0a0f48',
        },
        accent: {
          DEFAULT: '#aa3bff',
          light:   '#c084fc',
          muted:   'rgba(170, 59, 255, 0.1)',
        },
        surface: {
          bg: '#0a0a0a',
          panel: '#141414',
          raised: '#181a20',
          border: '#262626',
          light: '#141414',
          dark: '#16171d',
        },
        text: {
          primary: '#f5f5f5',
          secondary: '#a3a3a3',
          muted: '#737373',
        },
        brand: {
          primary: '#4a72ff',
          strong: '#1a3fff',
        },
        semantic: {
          pending: '#eab308',
          planning: '#4a72ff',
          executing: '#8b5cf6',
          completed: '#10b981',
          failed: '#ef4444',
          cancelled: '#a3a3a3',
          warning: '#f59e0b',
          degraded: '#f97316',
          idle: '#a3a3a3',
          busy: '#f59e0b',
          error: '#ef4444',
          thought: '#4a72ff',
          action: '#f59e0b',
          observation: '#22d3ee',
          final: '#10b981',
        },
      },
      fontFamily: {
        sans:  ['system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono:  ['ui-monospace', 'Consolas', 'monospace'],
      },
      fontSize: {
        'display': ['56px', { lineHeight: '1.1' }],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      borderRadius: {
        'forge': '8px',
      },
      boxShadow: {
        'forge': 'rgba(0, 0, 0, 0.1) 0 10px 15px -3px, rgba(0, 0, 0, 0.05) 0 4px 6px -2px',
      },
      animation: {
        'fade-in':    'fadeIn 0.3s ease-out',
        'slide-up':   'slideUp 0.4s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in':   'scaleIn 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%':   { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%':   { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
}
