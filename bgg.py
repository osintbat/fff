#!/usr/bin/env python3
import os, sys, subprocess, json, shutil

PROJECT_ROOT = "/var/www/russi"
CERTS_DIR = "/var/www/giveaway/certs"
NGINX_AVAILABLE = "/etc/nginx/sites-available/russi.conf"
NGINX_ENABLED = "/etc/nginx/sites-enabled/russi.conf"
SERVICE_PATH = "/etc/systemd/system/russi.service"
SERVICE_USER = "russiapp"
DOMAIN = "brokebase.com"

PACKAGE_JSON = """{
  "name": "russi",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.19.2",
    "helmet": "^7.1.0",
    "compression": "^1.7.4",
    "express-rate-limit": "^7.2.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "dotenv": "^16.4.5",
    "three": "^0.170.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@types/three": "^0.170.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.6.2",
    "vite": "^5.4.8"
  }
}"""

VITE_CONFIG = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'public',
    sourcemap: true,
    minify: false,
  },
  server: {
    port: 4000,
  },
});
"""

TS_CONFIG = """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
"""

INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>RUSSI</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Anton&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

MAIN_TSX = """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

const root = document.getElementById('root');
if (root) {
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}
"""

INDEX_CSS = """@tailwind base;
@tailwind components;
@tailwind utilities;
@layer base {
  html, body { @apply bg-black text-white m-0 p-0 h-full overflow-hidden; }
}
#root { @apply h-full; }
"""

APP_TSX = """import React from 'react';
import StarField from './StarField';

export default function App() {
  return (
    <div className="relative h-screen w-full">
      <div className="absolute inset-0 -z-10">
        <StarField />
      </div>
      <div className="flex items-center justify-center h-full px-6 py-16">
        <h1 className="font-anton text-white text-center leading-none text-[3rem] md:text-[7rem] lg:text-[9rem]">
          I RUSSI
        </h1>
      </div>
    </div>
  );
}
"""

STARFIELD_TSX = """import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function StarField() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({
      alpha: false,
      antialias: true,
    });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 1);
    container.appendChild(renderer.domElement);

    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, 'rgba(255,255,255,1)');
    gradient.addColorStop(0.2, 'rgba(255,255,255,0.9)');
    gradient.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 64, 64);
    const texture = new THREE.CanvasTexture(canvas);

    const starCount = 4000;
    const positions = new Float32Array(starCount * 3);
    const colors = new Float32Array(starCount * 3);
    const sizes = new Float32Array(starCount);

    for (let i = 0; i < starCount; i++) {
      const radius = 25 + Math.random() * 45;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos((Math.random() * 2) - 1);
      positions[i*3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i*3+1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i*3+2] = radius * Math.cos(phi);
      const brightness = 0.5 + Math.random() * 0.5;
      const colorChoice = Math.random();
      if (colorChoice < 0.33) {
        colors[i*3] = 0.8 * brightness;
        colors[i*3+1] = 0.9 * brightness;
        colors[i*3+2] = 1.0 * brightness;
      } else if (colorChoice < 0.66) {
        colors[i*3] = 1.0 * brightness;
        colors[i*3+1] = 0.8 * brightness;
        colors[i*3+2] = 0.7 * brightness;
      } else {
        colors[i*3] = 0.9 * brightness;
        colors[i*3+1] = 0.9 * brightness;
        colors[i*3+2] = 1.0 * brightness;
      }
      sizes[i] = 0.3 + Math.random() * 0.8;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

    const material = new THREE.PointsMaterial({
      size: 0.5,
      map: texture,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      transparent: true,
      vertexColors: true,
      sizeAttenuation: true,
      opacity: 0.95,
    });

    const stars = new THREE.Points(geometry, material);
    scene.add(stars);

    const bgStarCount = 2000;
    const bgPositions = new Float32Array(bgStarCount * 3);
    for (let i = 0; i < bgStarCount; i++) {
      const radius = 60 + Math.random() * 40;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos((Math.random() * 2) - 1);
      bgPositions[i*3] = radius * Math.sin(phi) * Math.cos(theta);
      bgPositions[i*3+1] = radius * Math.sin(phi) * Math.sin(theta);
      bgPositions[i*3+2] = radius * Math.cos(phi);
    }
    const bgGeometry = new THREE.BufferGeometry();
    bgGeometry.setAttribute('position', new THREE.BufferAttribute(bgPositions, 3));
    const bgMaterial = new THREE.PointsMaterial({
      color: 0x444466,
      size: 0.15,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });
    const bgStars = new THREE.Points(bgGeometry, bgMaterial);
    scene.add(bgStars);

    camera.position.z = 30;

    let frameId = 0;
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      stars.rotation.y += 0.0003;
      stars.rotation.x += 0.0001;
      bgStars.rotation.y += 0.0002;
      bgStars.rotation.x += 0.00005;
      renderer.render(scene, camera);
    };
    animate();

    const resize = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', resize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', resize);
      container.removeChild(renderer.domElement);
      renderer.dispose();
      geometry.dispose();
      material.dispose();
      bgGeometry.dispose();
      bgMaterial.dispose();
      texture.dispose();
    };
  }, []);

  return <div ref={containerRef} className="w-full h-full" />;
}
"""

SERVER_JS = """import express from 'express';
import helmet from 'helmet';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import { fileURLToPath } from 'url';
import path from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.set('trust proxy', 1);
app.disable('x-powered-by');

app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
      imgSrc: ["'self'", "data:"],
      connectSrc: ["'self'"],
      fontSrc: ["'self'", "https://fonts.gstatic.com"],
      objectSrc: ["'none'"],
      baseUri: ["'self'"],
      frameAncestors: ["'none'"],
      formAction: ["'none'"],
      upgradeInsecureRequests: [],
    },
  },
  hsts: { maxAge: 63072000, includeSubDomains: true, preload: true },
  referrerPolicy: { policy: 'no-referrer' },
  permissionsPolicy: { features: { geolocation: ["'none'"], microphone: ["'none'"], camera: ["'none'"] } },
  crossOriginResourcePolicy: { policy: 'same-origin' },
}));

app.use(compression());
app.use(rateLimit({ windowMs: 60*1000, max: 120 }));

app.use(express.static(path.join(__dirname, 'public'), {
  index: 'index.html',
  dotfiles: 'deny',
  setHeaders: (res) => res.setHeader('X-Content-Type-Options', 'nosniff'),
}));

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

const PORT = process.env.PORT || 4000;
app.listen(PORT, '127.0.0.1', () => {
  console.log(`✅ RUSSI server running on http://127.0.0.1:${PORT}`);
});
"""

# -------------------- FUNZIONI DI SETUP --------------------
def run(cmd, cwd=None, check=True):
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if check and result.returncode != 0:
        print(f"❌ Comando fallito: {cmd}")
        sys.exit(1)
    return result.returncode

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"✅ Scritto: {path}")

def main():
    if os.geteuid() != 0:
        print("❌ Esegui con sudo.")
        sys.exit(1)
    print("🚀 Avvio setup RUSSI - Campo stellare 3D con glow")

    if os.path.exists(PROJECT_ROOT):
        shutil.rmtree(PROJECT_ROOT)
        print("✅ Vecchia cartella rimossa.")

    try:
        subprocess.run(["id", SERVICE_USER], check=True, capture_output=True)
        print(f"✅ Utente {SERVICE_USER} già esistente.")
    except:
        run(f"useradd --system --no-create-home --shell /usr/sbin/nologin {SERVICE_USER}")

    write(os.path.join(PROJECT_ROOT, "package.json"), PACKAGE_JSON)
    write(os.path.join(PROJECT_ROOT, "vite.config.ts"), VITE_CONFIG)
    write(os.path.join(PROJECT_ROOT, "tsconfig.json"), TS_CONFIG)
    write(os.path.join(PROJECT_ROOT, "index.html"), INDEX_HTML)
    write(os.path.join(PROJECT_ROOT, "server.js"), SERVER_JS)
    write(os.path.join(PROJECT_ROOT, "src", "main.tsx"), MAIN_TSX)
    write(os.path.join(PROJECT_ROOT, "src", "index.css"), INDEX_CSS)
    write(os.path.join(PROJECT_ROOT, "src", "App.tsx"), APP_TSX)
    write(os.path.join(PROJECT_ROOT, "src", "StarField.tsx"), STARFIELD_TSX)

    run("npm install", cwd=PROJECT_ROOT)
    run("npm run build", cwd=PROJECT_ROOT)

    if not os.path.exists(os.path.join(PROJECT_ROOT, "public", "index.html")):
        print("❌ Build fallita")
        sys.exit(1)
    print("✅ Build completata")

    run(f"chown -R {SERVICE_USER}:{SERVICE_USER} {PROJECT_ROOT}")
    run(f"find {PROJECT_ROOT} -type d -exec chmod 755 {{}} \\;")
    run(f"find {PROJECT_ROOT} -type f -exec chmod 644 {{}} \\;")

    service = f"""[Unit]
Description=RUSSI single page site
After=network.target
[Service]
Type=simple
User={SERVICE_USER}
Group={SERVICE_USER}
WorkingDirectory={PROJECT_ROOT}
ExecStart=/usr/bin/node {PROJECT_ROOT}/server.js
Environment=PORT=4000
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={PROJECT_ROOT}
LimitNOFILE=4096
MemoryMax=256M
[Install]
WantedBy=multi-user.target
"""
    write(SERVICE_PATH, service)
    run("systemctl daemon-reload")
    run("systemctl enable russi")
    run("systemctl restart russi")

    old_conf = "/etc/nginx/sites-available/giveaway.conf"
    old_en = "/etc/nginx/sites-enabled/giveaway.conf"
    if os.path.islink(old_en) or os.path.exists(old_en):
        os.remove(old_en)
        print(f"✅ Rimosso {old_en}")
    if os.path.exists(old_conf):
        os.remove(old_conf)
        print(f"✅ Rimosso {old_conf}")

    nginx_conf = f"""server {{
    listen 80; listen [::]:80;
    server_name {DOMAIN} www.{DOMAIN};
    return 301 https://$host$request_uri;
}}
server {{
    listen 443 ssl; listen [::]:443 ssl;
    server_name {DOMAIN} www.{DOMAIN};
    ssl_certificate {CERTS_DIR}/cert.pem;
    ssl_certificate_key {CERTS_DIR}/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    client_max_body_size 256k;
    access_log /var/log/nginx/russi_access.log;
    error_log /var/log/nginx/russi_error.log;
    location / {{
        proxy_pass http://127.0.0.1:4000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }}
    location ~ /\\.(env|git) {{ deny all; return 404; }}
}}"""
    write(NGINX_AVAILABLE, nginx_conf)
    if not os.path.islink(NGINX_ENABLED):
        os.symlink(NGINX_AVAILABLE, NGINX_ENABLED)
        print(f"✅ Symlink creato: {NGINX_ENABLED}")

    run("nginx -t")
    run("systemctl reload nginx")

    print(f"\n✅ Sito RUSSI live su https://{DOMAIN}")
    print("✅ Campo stellare 3D con glow")
    print("✅ Titolo 'I RUSSI' centrato perfettamente")

if __name__ == "__main__":
    main()
