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
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "build:css": "tailwindcss -i ./src/input.css -o ./public/style.css",
    "build:js": "esbuild src/main.tsx --bundle --loader:.tsx=tsx --outfile=public/bundle.js --sourcemap",
    "build": "npm run build:css && npm run build:js"
  },
  "dependencies": {
    "express": "^4.19.2",
    "helmet": "^7.1.0",
    "compression": "^1.7.4",
    "express-rate-limit": "^7.2.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "dotenv": "^16.4.5",
    "ogl": "^1.0.11"
  },
  "devDependencies": {
    "esbuild": "^0.28.1",
    "tailwindcss": "^3.4.13",
    "typescript": "^5.6.2",
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0"
  }
}"""

TAILWIND_CONFIG = """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./public/index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: { bg: "#000000" },
      fontFamily: { anton: ["Anton", "Arial", "sans-serif"] },
    },
  },
  plugins: [],
};
"""

INPUT_CSS = """@tailwind base;
@tailwind components;
@tailwind utilities;
@layer base {
  html, body { @apply bg-black text-white m-0 p-0 h-full overflow-x-hidden; }
}
"""

SERVER_JS = """require('dotenv').config();
const express = require('express');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const app = express();
app.set('trust proxy',1);
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
app.use(express.static('/var/www/russi/public', { index: 'index.html', dotfiles: 'deny', setHeaders: (res) => res.setHeader('X-Content-Type-Options','nosniff') }));
app.use((req,res) => res.status(404).send('Not found'));
const PORT = process.env.PORT || 4000;
app.listen(PORT, '127.0.0.1', () => console.log(`RUSSI listening on 127.0.0.1:${PORT}`));
"""

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RUSSI</title>
<meta name="robots" content="noindex, nofollow">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<div id="root"></div>
<script src="/bundle.js" defer></script>
</body>
</html>"""

MAIN_TSX = """import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
const container = document.getElementById('root');
if (container) {
  console.log('React: montaggio su #root');
  createRoot(container).render(<App />);
} else {
  console.error('React: #root non trovato!');
}
"""

APP_TSX = """import React from 'react';
import Galaxy from './Galaxy';
export default function App() {
  console.log('App renderizzato');
  return (
    <div className="relative min-h-screen w-full">
      <div className="fixed inset-0 -z-10">
        <Galaxy
          mouseRepulsion
          mouseInteraction
          density={1}
          glowIntensity={0.3}
          saturation={0}
          hueShift={140}
          twinkleIntensity={0.3}
          rotationSpeed={0.1}
          repulsionStrength={2}
          autoCenterRepulsion={0}
          starSpeed={0.5}
          speed={1}
          transparent={false}
        />
      </div>
      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-6 py-16">
        <h1 className="font-anton text-white text-center leading-none text-[3rem] md:text-[7rem] lg:text-[9rem]">
          I RUSSI
        </h1>
      </main>
    </div>
  );
}
"""

GALAXY_TSX = """import React from 'react';
import { Renderer, Program, Mesh, Color, Triangle } from 'ogl';
import { useEffect, useRef } from 'react';

const vertexShader = `
attribute vec2 uv;
attribute vec2 position;

varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = vec4(position, 0, 1);
}
`;

// Fragment shader modificato: se non ci sono stelle, mostra un blu scuro (fallback)
const fragmentShader = `
precision highp float;

uniform float uTime;
uniform vec3 uResolution;
uniform vec2 uFocal;
uniform vec2 uRotation;
uniform float uStarSpeed;
uniform float uDensity;
uniform float uHueShift;
uniform float uSpeed;
uniform vec2 uMouse;
uniform float uGlowIntensity;
uniform float uSaturation;
uniform bool uMouseRepulsion;
uniform float uTwinkleIntensity;
uniform float uRotationSpeed;
uniform float uRepulsionStrength;
uniform float uMouseActiveFactor;
uniform float uAutoCenterRepulsion;
uniform bool uTransparent;

varying vec2 vUv;

#define NUM_LAYER 4.0
#define STAR_COLOR_CUTOFF 0.2
#define MAT45 mat2(0.7071, -0.7071, 0.7071, 0.7071)
#define PERIOD 3.0

float Hash21(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

float tri(float x) {
  return abs(fract(x) * 2.0 - 1.0);
}

float tris(float x) {
  float t = fract(x);
  return 1.0 - smoothstep(0.0, 1.0, abs(2.0 * t - 1.0));
}

float trisn(float x) {
  float t = fract(x);
  return 2.0 * (1.0 - smoothstep(0.0, 1.0, abs(2.0 * t - 1.0))) - 1.0;
}

vec3 hsv2rgb(vec3 c) {
  vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
  vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

float Star(vec2 uv, float flare) {
  float d = length(uv);
  float m = (0.05 * uGlowIntensity) / d;
  float rays = smoothstep(0.0, 1.0, 1.0 - abs(uv.x * uv.y * 1000.0));
  m += rays * flare * uGlowIntensity;
  uv *= MAT45;
  rays = smoothstep(0.0, 1.0, 1.0 - abs(uv.x * uv.y * 1000.0));
  m += rays * 0.3 * flare * uGlowIntensity;
  m *= smoothstep(1.0, 0.2, d);
  return m;
}

vec3 StarLayer(vec2 uv) {
  vec3 col = vec3(0.0);

  vec2 gv = fract(uv) - 0.5; 
  vec2 id = floor(uv);

  for (int y = -1; y <= 1; y++) {
    for (int x = -1; x <= 1; x++) {
      vec2 offset = vec2(float(x), float(y));
      vec2 si = id + vec2(float(x), float(y));
      float seed = Hash21(si);
      float size = fract(seed * 345.32);
      float glossLocal = tri(uStarSpeed / (PERIOD * seed + 1.0));
      float flareSize = smoothstep(0.9, 1.0, size) * glossLocal;

      float red = smoothstep(STAR_COLOR_CUTOFF, 1.0, Hash21(si + 1.0)) + STAR_COLOR_CUTOFF;
      float blu = smoothstep(STAR_COLOR_CUTOFF, 1.0, Hash21(si + 3.0)) + STAR_COLOR_CUTOFF;
      float grn = min(red, blu) * seed;
      vec3 base = vec3(red, grn, blu);
      
      float hue = atan(base.g - base.r, base.b - base.r) / (2.0 * 3.14159) + 0.5;
      hue = fract(hue + uHueShift / 360.0);
      float sat = length(base - vec3(dot(base, vec3(0.299, 0.587, 0.114)))) * uSaturation;
      float val = max(max(base.r, base.g), base.b);
      base = hsv2rgb(vec3(hue, sat, val));

      vec2 pad = vec2(tris(seed * 34.0 + uTime * uSpeed / 10.0), tris(seed * 38.0 + uTime * uSpeed / 30.0)) - 0.5;

      float star = Star(gv - offset - pad, flareSize);
      vec3 color = base;

      float twinkle = trisn(uTime * uSpeed + seed * 6.2831) * 0.5 + 1.0;
      twinkle = mix(1.0, twinkle, uTwinkleIntensity);
      star *= twinkle;
      
      col += star * size * color;
    }
  }

  return col;
}

void main() {
  vec2 focalPx = uFocal * uResolution.xy;
  vec2 uv = (vUv * uResolution.xy - focalPx) / uResolution.y;

  vec2 mouseNorm = uMouse - vec2(0.5);
  
  if (uAutoCenterRepulsion > 0.0) {
    vec2 centerUV = vec2(0.0, 0.0);
    float centerDist = length(uv - centerUV);
    vec2 repulsion = normalize(uv - centerUV) * (uAutoCenterRepulsion / (centerDist + 0.1));
    uv += repulsion * 0.05;
  } else if (uMouseRepulsion) {
    vec2 mousePosUV = (uMouse * uResolution.xy - focalPx) / uResolution.y;
    float mouseDist = length(uv - mousePosUV);
    vec2 repulsion = normalize(uv - mousePosUV) * (uRepulsionStrength / (mouseDist + 0.1));
    uv += repulsion * 0.05 * uMouseActiveFactor;
  } else {
    vec2 mouseOffset = mouseNorm * 0.1 * uMouseActiveFactor;
    uv += mouseOffset;
  }

  float autoRotAngle = uTime * uRotationSpeed;
  mat2 autoRot = mat2(cos(autoRotAngle), -sin(autoRotAngle), sin(autoRotAngle), cos(autoRotAngle));
  uv = autoRot * uv;

  uv = mat2(uRotation.x, -uRotation.y, uRotation.y, uRotation.x) * uv;

  vec3 col = vec3(0.0);

  for (float i = 0.0; i < 1.0; i += 1.0 / NUM_LAYER) {
    float depth = fract(i + uStarSpeed * uSpeed);
    float scale = mix(20.0 * uDensity, 0.5 * uDensity, depth);
    float fade = depth * smoothstep(1.0, 0.9, depth);
    col += StarLayer(uv * scale + i * 453.32) * fade;
  }

  // FALLBACK: se col è zero (nessuna stella), mostra blu scuro per debug
  if (length(col) < 0.001) {
    col = vec3(0.01, 0.01, 0.05);
  }

  if (uTransparent) {
    float alpha = length(col);
    alpha = smoothstep(0.0, 0.3, alpha);
    alpha = min(alpha, 1.0);
    gl_FragColor = vec4(col, alpha);
  } else {
    gl_FragColor = vec4(col, 1.0);
  }
}
`;

interface GalaxyProps {
  focal?: [number, number];
  rotation?: [number, number];
  starSpeed?: number;
  density?: number;
  hueShift?: number;
  disableAnimation?: boolean;
  speed?: number;
  mouseInteraction?: boolean;
  glowIntensity?: number;
  saturation?: number;
  mouseRepulsion?: boolean;
  twinkleIntensity?: number;
  rotationSpeed?: number;
  repulsionStrength?: number;
  autoCenterRepulsion?: number;
  transparent?: boolean;
}

export default function Galaxy({
  focal = [0.5, 0.5],
  rotation = [1.0, 0.0],
  starSpeed = 0.5,
  density = 1,
  hueShift = 140,
  disableAnimation = false,
  speed = 1.0,
  mouseInteraction = true,
  glowIntensity = 0.3,
  saturation = 0.0,
  mouseRepulsion = true,
  repulsionStrength = 2,
  twinkleIntensity = 0.3,
  rotationSpeed = 0.1,
  autoCenterRepulsion = 0,
  transparent = true,
  ...rest
}: GalaxyProps) {
  const ctnDom = useRef<HTMLDivElement>(null);
  const targetMousePos = useRef({ x: 0.5, y: 0.5 });
  const smoothMousePos = useRef({ x: 0.5, y: 0.5 });
  const targetMouseActive = useRef(0.0);
  const smoothMouseActive = useRef(0.0);

  useEffect(() => {
    console.log('Galaxy: useEffect avviato');
    if (!ctnDom.current) {
      console.error('Galaxy: ctnDom.current è null');
      return;
    }
    const ctn = ctnDom.current;
    let renderer, gl, program, mesh, animateId;

    try {
      renderer = new Renderer({
        alpha: transparent,
        premultipliedAlpha: false
      });
      gl = renderer.gl;
    } catch (err) {
      console.error('Galaxy: errore creazione Renderer:', err);
      return;
    }

    if (transparent) {
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.clearColor(0, 0, 0, 0);
    } else {
      gl.clearColor(0, 0, 0, 1);
    }

    function resize() {
      const scale = 1;
      const w = ctn.offsetWidth;
      const h = ctn.offsetHeight;
      console.log(`Galaxy: resize -> width=${w}, height=${h}`);
      renderer.setSize(w * scale, h * scale);
      if (program) {
        program.uniforms.uResolution.value = new Color(
          gl.canvas.width,
          gl.canvas.height,
          gl.canvas.width / gl.canvas.height
        );
      }
    }

    // Forza resize dopo il mount (con ritardi)
    setTimeout(resize, 50);
    setTimeout(resize, 200);

    window.addEventListener('resize', resize, false);

    const geometry = new Triangle(gl);
    program = new Program(gl, {
      vertex: vertexShader,
      fragment: fragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uResolution: {
          value: new Color(gl.canvas.width, gl.canvas.height, gl.canvas.width / gl.canvas.height)
        },
        uFocal: { value: new Float32Array(focal) },
        uRotation: { value: new Float32Array(rotation) },
        uStarSpeed: { value: starSpeed },
        uDensity: { value: density },
        uHueShift: { value: hueShift },
        uSpeed: { value: speed },
        uMouse: {
          value: new Float32Array([smoothMousePos.current.x, smoothMousePos.current.y])
        },
        uGlowIntensity: { value: glowIntensity },
        uSaturation: { value: saturation },
        uMouseRepulsion: { value: mouseRepulsion },
        uTwinkleIntensity: { value: twinkleIntensity },
        uRotationSpeed: { value: rotationSpeed },
        uRepulsionStrength: { value: repulsionStrength },
        uMouseActiveFactor: { value: 0.0 },
        uAutoCenterRepulsion: { value: autoCenterRepulsion },
        uTransparent: { value: transparent }
      }
    });

    mesh = new Mesh(gl, { geometry, program });

    function update(t: number) {
      animateId = requestAnimationFrame(update);
      if (!disableAnimation) {
        program.uniforms.uTime.value = t * 0.001;
        program.uniforms.uStarSpeed.value = (t * 0.001 * starSpeed) / 10.0;
      }

      const lerpFactor = 0.05;
      smoothMousePos.current.x += (targetMousePos.current.x - smoothMousePos.current.x) * lerpFactor;
      smoothMousePos.current.y += (targetMousePos.current.y - smoothMousePos.current.y) * lerpFactor;

      smoothMouseActive.current += (targetMouseActive.current - smoothMouseActive.current) * lerpFactor;

      program.uniforms.uMouse.value[0] = smoothMousePos.current.x;
      program.uniforms.uMouse.value[1] = smoothMousePos.current.y;
      program.uniforms.uMouseActiveFactor.value = smoothMouseActive.current;

      renderer.render({ scene: mesh });
    }
    animateId = requestAnimationFrame(update);
    ctn.appendChild(gl.canvas);
    console.log('Galaxy: canvas aggiunto al DOM');

    function handleMouseMove(e: MouseEvent) {
      const rect = ctn.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = 1.0 - (e.clientY - rect.top) / rect.height;
      targetMousePos.current = { x, y };
      targetMouseActive.current = 1.0;
    }

    function handleMouseLeave() {
      targetMouseActive.current = 0.0;
    }

    if (mouseInteraction) {
      ctn.addEventListener('mousemove', handleMouseMove);
      ctn.addEventListener('mouseleave', handleMouseLeave);
    }

    return () => {
      cancelAnimationFrame(animateId);
      window.removeEventListener('resize', resize);
      if (mouseInteraction) {
        ctn.removeEventListener('mousemove', handleMouseMove);
        ctn.removeEventListener('mouseleave', handleMouseLeave);
      }
      if (gl.canvas.parentElement === ctn) {
        ctn.removeChild(gl.canvas);
      }
      gl.getExtension('WEBGL_lose_context')?.loseContext();
    };
  }, [
    focal,
    rotation,
    starSpeed,
    density,
    hueShift,
    disableAnimation,
    speed,
    mouseInteraction,
    glowIntensity,
    saturation,
    mouseRepulsion,
    twinkleIntensity,
    rotationSpeed,
    repulsionStrength,
    autoCenterRepulsion,
    transparent
  ]);

  return <div ref={ctnDom} className="w-full h-full relative" {...rest} />;
}
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
    print("🚀 Avvio setup RUSSI con Galaxy (OGL) - con FALLBACK e RESIZE FORZATO")

    # Rimuovi vecchia cartella
    if os.path.exists(PROJECT_ROOT):
        shutil.rmtree(PROJECT_ROOT)
        print("✅ Vecchia cartella rimossa.")

    # Crea utente se non esiste
    try:
        subprocess.run(["id", SERVICE_USER], check=True, capture_output=True)
        print(f"✅ Utente {SERVICE_USER} già esistente.")
    except:
        run(f"useradd --system --no-create-home --shell /usr/sbin/nologin {SERVICE_USER}")

    # Scrivi tutti i file
    write(os.path.join(PROJECT_ROOT, "package.json"), PACKAGE_JSON)
    write(os.path.join(PROJECT_ROOT, "server.js"), SERVER_JS)
    write(os.path.join(PROJECT_ROOT, "public", "index.html"), INDEX_HTML)
    write(os.path.join(PROJECT_ROOT, "tailwind.config.js"), TAILWIND_CONFIG)
    write(os.path.join(PROJECT_ROOT, "src", "input.css"), INPUT_CSS)
    write(os.path.join(PROJECT_ROOT, "src", "App.tsx"), APP_TSX)
    write(os.path.join(PROJECT_ROOT, "src", "main.tsx"), MAIN_TSX)
    write(os.path.join(PROJECT_ROOT, "src", "Galaxy.tsx"), GALAXY_TSX)

    # Installa e builda come root
    run("npm install", cwd=PROJECT_ROOT)
    run("npm run build", cwd=PROJECT_ROOT)

    bundle = os.path.join(PROJECT_ROOT, "public", "bundle.js")
    if not os.path.exists(bundle) or os.path.getsize(bundle)==0:
        print("❌ bundle.js non generato!")
        sys.exit(1)
    print(f"✅ Bundle generato: {bundle} ({os.path.getsize(bundle)} byte)")

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

    # Rimuovi vecchi file Nginx (giveaway)
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
    print("✅ Background Galaxy (OGL) con fallback blu scuro.")
    print("📌 Apri la console del browser (F12) per vedere i log delle dimensioni del canvas.")

if __name__ == "__main__":
    main()
