import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const isPythonAnywhereBuild = mode === 'pythonanywhere';

  return {
    plugins: [react()],
    base: isPythonAnywhereBuild ? '/static/frontend/' : '/',
    build: isPythonAnywhereBuild
      ? {
          outDir: '../backend/static/frontend',
          emptyOutDir: true,
        }
      : undefined,
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/media': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/static': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  };
});
