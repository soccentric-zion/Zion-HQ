import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // Dev-only convenience: allow reaching this server by LAN IP or
    // mDNS hostname (e.g. http://pabi.local:5173), not just localhost --
    // Vite 5+ blocks unrecognized Host headers by default (DNS-rebinding
    // protection). Never do this for a server exposed beyond a trusted LAN.
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Forwards X-Forwarded-Host/-Proto/-For so the API can see which
        // origin the browser actually used (localhost, LAN IP, or an mDNS
        // hostname) -- needed to build a matching OIDC redirect_uri per
        // request instead of hardcoding one (see app/routers/auth.py).
        xfwd: true,
        ws: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})
