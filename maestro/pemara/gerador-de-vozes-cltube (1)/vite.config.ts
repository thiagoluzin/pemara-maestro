import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    const maestroStudioUrl = env.MAESTRO_STUDIO_URL || 'http://127.0.0.1:8029';
    return {
      server: {
        port: 3000,
        host: '0.0.0.0',
        proxy: {
          '/api/editor': {
            target: maestroStudioUrl,
            changeOrigin: true,
          },
        },
      },
      plugins: [react()],
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        }
      }
    };
});
