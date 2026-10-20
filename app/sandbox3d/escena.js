// Vista 3D del simulador: la estrella, su zona habitable y el planeta, con Three.js.
// Mientras se arrastra un control todo se calcula aquí mismo (mi regla, el ESI y el modelo, que llega desde
// Python como sus árboles). Al soltar el control se le avisa a Python para que actualice el resto de la página.

const LUZ_MIN = 0.05;
const LUZ_MAX = 4.0;
const POSICIONES = 1000; // el control de luz va de 0 a 1000 en escala logarítmica
const REGLA = { conservadora: [0.356, 1.107], optimista: [0.32, 1.776] }; // la zona del Sol, como en gold
// Kopparapu et al. (2014), planeta de una masa terrestre: Seff = S0 + a·T + b·T² + c·T³ + d·T⁴ con T = Teff − 5780 K
const KOPPARAPU = {
  venusReciente: [1.776, 2.136e-4, 2.533e-8, -1.332e-11, -3.097e-15],
  invernaderoDesbocado: [1.107, 1.332e-4, 1.580e-8, -8.308e-12, -1.931e-15],
  maximoInvernadero: [0.356, 6.171e-5, 1.698e-9, -3.198e-12, -5.575e-16],
  marteTemprano: [0.32, 5.547e-5, 1.526e-9, -2.874e-12, -5.011e-16],
};
const ASPECTOS = {
  templado: 'Rocoso, con temperatura templada',
  helado: 'Rocoso y helado',
  desierto: 'Rocoso y muy caliente',
  lava: 'Rocoso y abrasador',
  neptuno: 'Tipo Neptuno, con envoltura de gas',
  gigante: 'Gigante gaseoso',
};
const ATMOSFERAS = {
  templado: '#6FB6FF', helado: '#CFE8FF', desierto: '#FFB36B', lava: '#FF6A3A', neptuno: '#7FE0FF', gigante: '#FFD9A0',
};
const NUMERO = new Intl.NumberFormat('en-US');
const THREE_VERSION = '0.170.0';

// ---------------------------------------------------------------------------------------------------------------
// Cálculos (los mismos que calculos.py y gold; se exportan para probarlos fuera del navegador)
// ---------------------------------------------------------------------------------------------------------------

export function probabilidad(modelo, radio, luz, temp) {
  if (!modelo) return null;
  const valores = { radio_tierras: radio, insolacion_tierras: luz, temp_estrella_k: temp };
  const x = modelo.variables.map((nombre) => valores[nombre]);
  let suma = modelo.base;
  for (const arbol of modelo.arboles) {
    let i = 0;
    while (arbol[i].length > 1) {
      const nodo = arbol[i];
      i = x[nodo[0]] <= nodo[1] ? nodo[2] : nodo[3];
    }
    suma += arbol[i][0];
  }
  return 1 / (1 + Math.exp(-suma));
}

export function esi(radio, luz) {
  return 1 - Math.sqrt(0.5 * (((luz - 1) / (luz + 1)) ** 2 + ((radio - 1) / (radio + 1)) ** 2));
}

export function segunRegla(radio, luz) {
  if (luz >= REGLA.conservadora[0] && luz <= REGLA.conservadora[1] && radio >= 0.5 && radio <= 1.6) return 'conservador';
  if (luz >= REGLA.optimista[0] && luz <= REGLA.optimista[1] && radio <= 2.5) return 'optimista';
  return 'no';
}

export function aspecto(radio, luz) {
  if (radio > 6) return 'gigante';
  if (radio > 1.6) return 'neptuno';
  if (luz > 25) return 'lava';
  if (luz > REGLA.optimista[1]) return 'desierto';
  return luz >= REGLA.optimista[0] ? 'templado' : 'helado';
}

function seff(coef, temp) {
  const t = Math.min(7200, Math.max(2600, temp)) - 5780;
  return coef[0] + coef[1] * t + coef[2] * t ** 2 + coef[3] * t ** 3 + coef[4] * t ** 4;
}

/** La zona habitable de una estrella de esa temperatura, en luz recibida (Tierra = 1): [menos luz, más luz]. */
export function zonaHabitable(temp) {
  return {
    optimista: [seff(KOPPARAPU.marteTemprano, temp), seff(KOPPARAPU.venusReciente, temp)],
    conservadora: [seff(KOPPARAPU.maximoInvernadero, temp), seff(KOPPARAPU.invernaderoDesbocado, temp)],
  };
}

/** Color aproximado de un cuerpo negro (sRGB de 0 a 1), según Tanner Helland. */
export function colorEstrella(temp) {
  const t = temp / 100;
  let r, g, b;
  if (t <= 66) {
    r = 255;
    g = 99.4708025861 * Math.log(t) - 161.1195681661;
    b = t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307;
  } else {
    r = 329.698727446 * (t - 60) ** -0.1332047592;
    g = 288.1221695283 * (t - 60) ** -0.0755148492;
    b = 255;
  }
  return [r, g, b].map((v) => Math.min(255, Math.max(0, v)) / 255);
}

function claseEstrella(temp) {
  if (temp < 3900) return 'enana roja';
  if (temp < 5300) return 'enana naranja';
  if (temp < 6000) return 'como el Sol';
  return 'blanco amarilla';
}

/** Radio aproximado de una estrella de la secuencia principal (Sol = 1): L ≈ (T/5778)^7 y Stefan-Boltzmann. */
function radioSolar(temp) {
  const luminosidad = (temp / 5778) ** 7;
  return Math.sqrt(luminosidad) * (5778 / temp) ** 2;
}

export function porcentaje(p) {
  if (p < 0.005) return '<1%';
  return p >= 0.995 ? '>99%' : `${Math.round(p * 100)}%`;
}

const luzDePosicion = (pos) => LUZ_MIN * (LUZ_MAX / LUZ_MIN) ** (pos / POSICIONES);
const posicionDeLuz = (luz) => Math.round((POSICIONES * Math.log(luz / LUZ_MIN)) / Math.log(LUZ_MAX / LUZ_MIN));
const limitar = (v, min, max) => Math.min(max, Math.max(min, v));

function renombrar(nombre) {
  if (nombre.startsWith('Tu planeta')) return nombre;
  return nombre === 'Tierra' ? 'Tu planeta' : `Tu planeta (a partir de ${nombre})`;
}

// ---------------------------------------------------------------------------------------------------------------
// Texturas procedurales de los planetas (ruido de valor en 3D, sin costuras en la esfera)
// ---------------------------------------------------------------------------------------------------------------

function azarConSemilla(semilla) {
  let s = semilla >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function crearRuido(semilla) {
  const azar = azarConSemilla(semilla);
  const perm = new Uint8Array(512);
  const base = Array.from({ length: 256 }, (_, i) => i);
  for (let i = 255; i > 0; i--) {
    const j = Math.floor(azar() * (i + 1));
    [base[i], base[j]] = [base[j], base[i]];
  }
  for (let i = 0; i < 512; i++) perm[i] = base[i & 255];
  const valores = Float32Array.from({ length: 256 }, () => azar());
  const h = (x, y, z) => valores[perm[perm[perm[x & 255] + (y & 255)] + (z & 255)]];
  const suave = (t) => t * t * (3 - 2 * t);
  const ruido = (x, y, z) => {
    const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
    const u = suave(x - xi), v = suave(y - yi), w = suave(z - zi);
    const a = h(xi, yi, zi) + (h(xi + 1, yi, zi) - h(xi, yi, zi)) * u;
    const b = h(xi, yi + 1, zi) + (h(xi + 1, yi + 1, zi) - h(xi, yi + 1, zi)) * u;
    const c = h(xi, yi, zi + 1) + (h(xi + 1, yi, zi + 1) - h(xi, yi, zi + 1)) * u;
    const d = h(xi, yi + 1, zi + 1) + (h(xi + 1, yi + 1, zi + 1) - h(xi, yi + 1, zi + 1)) * u;
    const e = a + (b - a) * v;
    return e + (c + (d - c) * v - e) * w;
  };
  return (x, y, z, octavas) => {
    let amplitud = 0.5, frecuencia = 1, suma = 0, total = 0;
    for (let o = 0; o < octavas; o++) {
      suma += amplitud * ruido(x * frecuencia, y * frecuencia, z * frecuencia);
      total += amplitud;
      amplitud *= 0.5;
      frecuencia *= 2.03;
    }
    return suma / total;
  };
}

const poner = (d, i, r, g, b, a = 255) => { d[i] = r; d[i + 1] = g; d[i + 2] = b; d[i + 3] = a; };
const mezcla = (d, i, c1, c2, t) => {
  const k = limitar(t, 0, 1);
  poner(d, i, c1[0] + (c2[0] - c1[0]) * k, c1[1] + (c2[1] - c1[1]) * k, c1[2] + (c2[2] - c1[2]) * k);
};

const PINTORES = {
  templado(fbm, x, y, z, lat, mapa, i, _emision, nubes) {
    const n = fbm(x * 1.7 + 3.1, y * 1.7, z * 1.7, 6);
    const polo = Math.abs(lat) > 0.86 - 0.1 * fbm(x * 4 + 9, y * 4, z * 4, 3);
    if (polo) poner(mapa, i, 236, 242, 248);
    else if (n < 0.53) mezcla(mapa, i, [44, 132, 200], [8, 32, 78], ((0.53 - n) / 0.2) ** 0.7);
    else {
      const h = (n - 0.53) / 0.25;
      if (h < 0.06) poner(mapa, i, 200, 188, 142);
      else if (h < 0.4) mezcla(mapa, i, [58, 134, 80], [94, 146, 76], (h - 0.06) / 0.34);
      else if (h < 0.72) mezcla(mapa, i, [120, 128, 80], [134, 108, 80], (h - 0.4) / 0.32);
      else mezcla(mapa, i, [142, 130, 118], [236, 240, 244], (h - 0.72) / 0.28);
    }
    const c = fbm(x * 2.4 + 41, y * 3.2, z * 2.4, 5);
    const a = limitar((c - 0.5) / 0.2, 0, 1);
    poner(nubes, i, 255, 255, 255, a * a * 240);
  },
  helado(fbm, x, y, z, _lat, mapa, i) {
    const n = fbm(x * 2.2 + 9, y * 2.2, z * 2.2, 6);
    mezcla(mapa, i, [246, 250, 253], [150, 186, 214], (n - 0.36) / 0.32);
    const grieta = Math.abs(fbm(x * 5 + 2, y * 5, z * 5, 3) - 0.5);
    if (grieta < 0.014) { mapa[i] *= 0.7; mapa[i + 1] *= 0.8; mapa[i + 2] *= 0.88; }
  },
  desierto(fbm, x, y, z, _lat, mapa, i) {
    const n = fbm(x * 2 + 5, y * 2, z * 2, 6);
    mezcla(mapa, i, [236, 194, 128], [176, 110, 56], (n - 0.32) / 0.4);
    const dunas = 0.93 + 0.07 * Math.sin(y * 26 + n * 10);
    mapa[i] *= dunas; mapa[i + 1] *= dunas; mapa[i + 2] *= dunas;
    if (n > 0.64) mezcla(mapa, i, [mapa[i], mapa[i + 1], mapa[i + 2]], [104, 66, 38], (n - 0.64) / 0.12);
  },
  lava(fbm, x, y, z, _lat, mapa, i, emision) {
    const n = fbm(x * 2.4 + 13, y * 2.4, z * 2.4, 6);
    mezcla(mapa, i, [64, 34, 24], [22, 11, 9], (n - 0.3) / 0.4);
    const g = Math.abs(fbm(x * 3.2 + 77, y * 3.2, z * 3.2, 5) - 0.5);
    const grieta = limitar(1 - g / 0.05, 0, 1);
    poner(emision, i, 255 * grieta, 70 * grieta + 90 * grieta ** 3, 20 * grieta ** 2);
  },
  neptuno(fbm, x, y, z, _lat, mapa, i) {
    const t = fbm(x * 1.4 + 3, y * 1.4, z * 1.4, 4);
    const banda = 0.5 + 0.5 * Math.sin((y * 6.5 + (t - 0.5) * 2.4) * Math.PI);
    mezcla(mapa, i, [188, 234, 248], [36, 116, 172], banda);
    if (fbm(x * 6 + 1, y * 6, z * 6, 3) > 0.7) { mapa[i] += 28; mapa[i + 1] += 28; mapa[i + 2] += 24; }
  },
  gigante(fbm, x, y, z, _lat, mapa, i) {
    const t = fbm(x * 1.3 + 8, y * 1.3, z * 1.3, 4);
    const banda = 0.5 + 0.5 * Math.sin((y * 9 + (t - 0.5) * 2.6) * Math.PI);
    mezcla(mapa, i, [244, 224, 188], [166, 108, 66], banda);
  },
};
const SEMILLAS = { templado: 11, helado: 23, desierto: 37, lava: 41, neptuno: 53, gigante: 67 };

function pintarPlaneta(tipo, ancho = 512, alto = 256) {
  const fbm = crearRuido(SEMILLAS[tipo]);
  const mapa = new Uint8ClampedArray(ancho * alto * 4);
  const emision = tipo === 'lava' ? new Uint8ClampedArray(ancho * alto * 4) : null;
  const nubes = tipo === 'templado' ? new Uint8ClampedArray(ancho * alto * 4) : null;
  const pintor = PINTORES[tipo];
  for (let y = 0; y < alto; y++) {
    const lat = (0.5 - (y + 0.5) / alto) * Math.PI;
    const cl = Math.cos(lat), sl = Math.sin(lat);
    for (let x = 0; x < ancho; x++) {
      const lon = ((x + 0.5) / ancho) * Math.PI * 2;
      pintor(fbm, cl * Math.cos(lon), sl, cl * Math.sin(lon), sl, mapa, (y * ancho + x) * 4, emision, nubes);
    }
  }
  return { mapa, emision, nubes, ancho, alto };
}

function lienzoCon(datos, ancho, alto) {
  const lienzo = document.createElement('canvas');
  lienzo.width = ancho;
  lienzo.height = alto;
  lienzo.getContext('2d').putImageData(new ImageData(datos, ancho, alto), 0, 0);
  return lienzo;
}

function lienzoRadial(tamano, paradas) {
  const lienzo = document.createElement('canvas');
  lienzo.width = lienzo.height = tamano;
  const ctx = lienzo.getContext('2d');
  const gradiente = ctx.createRadialGradient(tamano / 2, tamano / 2, 0, tamano / 2, tamano / 2, tamano / 2);
  for (const [pos, alfa] of paradas) gradiente.addColorStop(pos, `rgba(255,255,255,${alfa})`);
  ctx.fillStyle = gradiente;
  ctx.fillRect(0, 0, tamano, tamano);
  return lienzo;
}

// ---------------------------------------------------------------------------------------------------------------
// Shaders
// ---------------------------------------------------------------------------------------------------------------

const RUIDO_GLSL = /* glsl */ `
  float hash(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
  float ruido(vec3 x) {
    vec3 i = floor(x); vec3 f = fract(x); f = f * f * (3.0 - 2.0 * f);
    return mix(mix(mix(hash(i), hash(i + vec3(1, 0, 0)), f.x), mix(hash(i + vec3(0, 1, 0)), hash(i + vec3(1, 1, 0)), f.x), f.y),
               mix(mix(hash(i + vec3(0, 0, 1)), hash(i + vec3(1, 0, 1)), f.x), mix(hash(i + vec3(0, 1, 1)), hash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
  }
  float fbm(vec3 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * ruido(p); p *= 2.07; a *= 0.5; } return s; }
`;

const ESTRELLA_VERTICE = /* glsl */ `
  varying vec3 vNormal; varying vec3 vPos;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    vPos = position;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const ESTRELLA_FRAGMENTO = /* glsl */ `
  uniform vec3 uColor; uniform float uTiempo;
  varying vec3 vNormal; varying vec3 vPos;
  ${RUIDO_GLSL}
  void main() {
    float mu = clamp(dot(normalize(vNormal), vec3(0.0, 0.0, 1.0)), 0.0, 1.0);
    float limbo = 0.45 + 0.55 * pow(mu, 0.55);
    vec3 p = normalize(vPos) * 3.4;
    float granos = fbm(p + vec3(uTiempo * 0.05, uTiempo * 0.03, -uTiempo * 0.04));
    float manchas = smoothstep(0.64, 0.8, fbm(p * 0.55 + 17.0 + uTiempo * 0.01));
    vec3 color = uColor * (0.62 + 0.62 * granos) * limbo * (1.0 - 0.32 * manchas);
    color += uColor * pow(mu, 5.0) * 0.18;
    gl_FragColor = vec4(color * 0.92, 1.0);
    #include <colorspace_fragment>
  }
`;

const ATMOSFERA_VERTICE = /* glsl */ `
  varying vec3 vNormalMundo; varying vec3 vPosMundo;
  void main() {
    vNormalMundo = normalize(mat3(modelMatrix) * normal);
    vec4 posicion = modelMatrix * vec4(position, 1.0);
    vPosMundo = posicion.xyz;
    gl_Position = projectionMatrix * viewMatrix * posicion;
  }
`;

const ATMOSFERA_FRAGMENTO = /* glsl */ `
  uniform vec3 uColor;
  varying vec3 vNormalMundo; varying vec3 vPosMundo;
  void main() {
    vec3 n = normalize(vNormalMundo);
    vec3 v = normalize(cameraPosition - vPosMundo);
    float borde = pow(clamp(-dot(n, v) / 0.42, 0.0, 1.0), 1.7);
    float dia = clamp(dot(n, normalize(-vPosMundo)) * 0.85 + 0.35, 0.06, 1.0);
    float a = borde * dia;
    gl_FragColor = vec4(uColor * a * 1.35, a);
    #include <colorspace_fragment>
  }
`;

const DISCO_VERTICE = /* glsl */ `
  varying vec2 vXY;
  void main() {
    vXY = position.xy;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const DISCO_FRAGMENTO = /* glsl */ `
  uniform float uEscala; uniform float uRadioDisco; uniform float uTiempo; uniform float uOrbita;
  uniform vec2 uOptimista; uniform vec2 uConservadora; uniform vec2 uRegla;
  uniform vec3 uVerde; uniform vec3 uAcento;
  varying vec2 vXY;
  float banda(float r, vec2 lim, float s) { return smoothstep(lim.x - s, lim.x + s, r) * (1.0 - smoothstep(lim.y - s, lim.y + s, r)); }
  float linea(float r, float r0, float pixeles) { float w = fwidth(r) * pixeles; return 1.0 - smoothstep(0.0, w, abs(r - r0)); }
  void main() {
    float rd = length(vXY);
    float r = rd / uEscala;
    float angulo = atan(vXY.y, vXY.x);
    float latido = 0.86 + 0.14 * sin(uTiempo * 0.9 - r * 7.0);
    float a = (banda(r, uOptimista, 0.04) * 0.1 + banda(r, uConservadora, 0.03) * 0.22) * latido;
    a += (linea(r, uConservadora.x, 1.3) + linea(r, uConservadora.y, 1.3)) * 0.28;
    vec3 color = uVerde;
    float guion = step(0.45, fract(angulo * 40.0 / 6.2831853));
    float regla = max(linea(r, uRegla.x, 1.3), linea(r, uRegla.y, 1.3)) * guion * 0.55;
    color = mix(color, vec3(0.91, 0.94, 1.0), regla / max(a + regla, 1e-4));
    a += regla;
    float cuadricula = (1.0 - smoothstep(0.0, fwidth(r) * 1.1, abs(r - floor(r * 2.0 + 0.5) / 2.0))) * 0.05;
    color = mix(color, vec3(0.55, 0.62, 0.75), cuadricula / max(a + cuadricula, 1e-4));
    a += cuadricula * step(0.3, r);
    float orbita = linea(r, uOrbita, 1.7) * 0.75;
    color = mix(color, uAcento, orbita / max(a + orbita, 1e-4));
    a += orbita;
    a *= 1.0 - smoothstep(0.8, 1.0, rd / uRadioDisco);
    gl_FragColor = vec4(color, clamp(a, 0.0, 1.0));
    #include <colorspace_fragment>
  }
`;

// ---------------------------------------------------------------------------------------------------------------
// Carga de Three.js: desde la misma app (app/static) y, si falla, desde un CDN con la misma versión
// ---------------------------------------------------------------------------------------------------------------

async function cargarThree() {
  const local = `${window.location.origin}/app/static/three/`;
  try {
    const THREE = await import(`${local}three.module.min.js`);
    const { OrbitControls } = await import(`${local}OrbitControls.js`);
    return { THREE, OrbitControls };
  } catch (errorLocal) {
    console.warn('Vista 3D: no se pudo cargar Three.js desde la app, uso el CDN.', errorLocal);
    const cdn = `https://cdn.jsdelivr.net/npm/three@${THREE_VERSION}`;
    const THREE = await import(`${cdn}/+esm`);
    const { OrbitControls } = await import(`${cdn}/examples/jsm/controls/OrbitControls.js/+esm`);
    return { THREE, OrbitControls };
  }
}

// ---------------------------------------------------------------------------------------------------------------
// La escena 3D
// ---------------------------------------------------------------------------------------------------------------

const RADIO_DISCO = 64;
const escalaPara = (orbita) => 22 / Math.max(2.45, orbita * 1.12); // la zona habitable siempre cabe en el cuadro
const radioEstrellaVisual = (temp) => 1.05 + 0.85 * limitar(radioSolar(temp), 0.12, 1.6);
const radioPlanetaVisual = (radio) => 0.62 + 0.36 * radio;

class Escena3D {
  constructor(THREE, OrbitControls, contenedor, etiquetas, alInteractuar) {
    this.T = THREE;
    this.contenedor = contenedor;
    this.etiquetas = etiquetas;
    this.lento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.texturas = new Map();
    this.desechables = [];

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.08;
    contenedor.appendChild(this.renderer.domElement);

    this.escena = new THREE.Scene();
    this.camara = new THREE.PerspectiveCamera(40, 1, 0.1, 4000);
    this.camara.position.set(0, 19, 34);
    this.controles = new OrbitControls(this.camara, this.renderer.domElement);
    Object.assign(this.controles, {
      enableDamping: true, dampingFactor: 0.06, enablePan: false, rotateSpeed: 0.6, zoomSpeed: 0.8,
      minDistance: 6, maxDistance: 150, minPolarAngle: 0.1 * Math.PI, maxPolarAngle: 0.62 * Math.PI,
      autoRotate: !this.lento, autoRotateSpeed: 0.3,
    });
    this.controles.addEventListener('start', () => {
      this.controles.autoRotate = false;
      clearTimeout(this.reanudar);
      alInteractuar();
    });
    this.controles.addEventListener('end', () => {
      clearTimeout(this.reanudar);
      if (!this.lento) this.reanudar = setTimeout(() => { this.controles.autoRotate = true; }, 7000);
    });
    // La rueda sola sigue bajando la página; con Ctrl (o pellizcando el trackpad) acerca la vista
    this.alRueda = (evento) => { this.controles.enableZoom = evento.ctrlKey || evento.metaKey; };
    this.renderer.domElement.addEventListener('wheel', this.alRueda, { capture: true, passive: true });

    this.texturaBrillo = this.registrar(new THREE.CanvasTexture(
      lienzoRadial(256, [[0, 1], [0.16, 0.62], [0.42, 0.16], [1, 0]])));
    this.texturaPunto = this.registrar(new THREE.CanvasTexture(lienzoRadial(64, [[0, 1], [0.35, 0.5], [1, 0]])));
    this.crearCielo();
    this.crearEstrella();
    this.crearDisco();
    this.crearPlaneta();
    // Un poco de luz de relleno para que el lado de noche no quede negro del todo
    this.escena.add(new THREE.AmbientLight(0x8090b8, 0.9));
    this.luz = new THREE.PointLight(0xffffff, 3.4, 0, 0);
    this.escena.add(this.luz);

    this.actual = null;
    this.objetivo = null;
    this.angulo = 2.2;
    this.tiempo = 0;
    this.reloj = new THREE.Clock();
    this.punto = new THREE.Vector3();
    this.redimensionar();
    this.observadorTamano = new ResizeObserver(() => this.redimensionar());
    this.observadorTamano.observe(contenedor);
    this.observadorVista = new IntersectionObserver(([entrada]) => this.animar(entrada.isIntersecting));
    this.observadorVista.observe(contenedor);
    this.animar(true);
    this.precalentar();
  }

  registrar(recurso) {
    this.desechables.push(recurso);
    return recurso;
  }

  crearCielo() {
    const T = this.T;
    const capa = (cantidad, tamano, brillo, semilla) => {
      const azar = azarConSemilla(semilla);
      const posiciones = new Float32Array(cantidad * 3);
      const colores = new Float32Array(cantidad * 3);
      for (let i = 0; i < cantidad; i++) {
        const u = azar() * 2 - 1, giro = azar() * Math.PI * 2, r = 900 + azar() * 600, s = Math.sqrt(1 - u * u);
        posiciones.set([r * s * Math.cos(giro), r * u, r * s * Math.sin(giro)], i * 3);
        const tono = azar(), b = brillo * (0.35 + 0.65 * azar() ** 2);
        const [cr, cg, cb] = tono < 0.16 ? [1, 0.84, 0.7] : tono < 0.42 ? [0.76, 0.85, 1] : [1, 1, 1];
        colores.set([cr * b, cg * b, cb * b], i * 3);
      }
      const geometria = this.registrar(new T.BufferGeometry());
      geometria.setAttribute('position', new T.Float32BufferAttribute(posiciones, 3));
      geometria.setAttribute('color', new T.Float32BufferAttribute(colores, 3));
      const material = this.registrar(new T.PointsMaterial({
        size: tamano, sizeAttenuation: false, vertexColors: true, map: this.texturaPunto, transparent: true,
        depthWrite: false, blending: T.AdditiveBlending, toneMapped: false,
      }));
      return new T.Points(geometria, material);
    };
    this.cielo = new T.Group();
    this.cielo.add(capa(2600, 2.2, 0.75, 7), capa(180, 4.2, 1, 19));
    this.escena.add(this.cielo);
  }

  crearEstrella() {
    const T = this.T;
    this.uEstrella = { uColor: { value: new T.Color(1, 1, 1) }, uTiempo: { value: 0 } };
    this.estrella = new T.Mesh(
      this.registrar(new T.SphereGeometry(1, 64, 48)),
      this.registrar(new T.ShaderMaterial({
        uniforms: this.uEstrella, vertexShader: ESTRELLA_VERTICE, fragmentShader: ESTRELLA_FRAGMENTO, toneMapped: false,
      })),
    );
    // La corona es un anillo de luz que empieza en el borde de la estrella, así no le tapa la superficie
    this.texturaCorona = this.registrar(new T.CanvasTexture(
      lienzoRadial(256, [[0, 0], [0.17, 0], [0.205, 0.85], [0.3, 0.34], [0.55, 0.08], [1, 0]])));
    this.halos = [[5.2, 0.95, this.texturaCorona], [12, 0.26, this.texturaBrillo], [30, 0.08, this.texturaBrillo]]
      .map(([escala, opacidad, textura]) => {
      const material = this.registrar(new T.SpriteMaterial({
        map: textura, color: 0xffffff, transparent: true, opacity: opacidad, depthWrite: false,
        blending: T.AdditiveBlending, toneMapped: false,
      }));
      const halo = new T.Sprite(material);
      halo.userData.escala = escala;
      return halo;
    });
    this.escena.add(this.estrella, ...this.halos);
  }

  crearDisco() {
    const T = this.T;
    this.uDisco = {
      uEscala: { value: 9 }, uRadioDisco: { value: RADIO_DISCO }, uTiempo: { value: 0 }, uOrbita: { value: 1 },
      uOptimista: { value: new T.Vector2(0.75, 1.77) }, uConservadora: { value: new T.Vector2(0.95, 1.68) },
      uRegla: { value: new T.Vector2(1 / Math.sqrt(REGLA.conservadora[1]), 1 / Math.sqrt(REGLA.conservadora[0])) },
      uVerde: { value: new T.Color('#3DDC97') }, uAcento: { value: new T.Color('#7AA2FF') },
    };
    const disco = new T.Mesh(
      this.registrar(new T.CircleGeometry(RADIO_DISCO, 180)),
      this.registrar(new T.ShaderMaterial({
        uniforms: this.uDisco, vertexShader: DISCO_VERTICE, fragmentShader: DISCO_FRAGMENTO, transparent: true,
        depthWrite: false, side: T.DoubleSide, toneMapped: false,
      })),
    );
    disco.rotation.x = -Math.PI / 2;
    this.escena.add(disco);
  }

  crearPlaneta() {
    const T = this.T;
    this.grupo = new T.Group();
    this.inclinacion = new T.Group();
    this.inclinacion.rotation.z = 0.41; // como la Tierra, unos 23°
    this.materialPlaneta = this.registrar(new T.MeshStandardMaterial({ roughness: 0.88, metalness: 0, emissive: 0xffffff,
      emissiveIntensity: 0 }));
    this.planeta = new T.Mesh(this.registrar(new T.SphereGeometry(1, 96, 64)), this.materialPlaneta);
    this.materialNubes = this.registrar(new T.MeshStandardMaterial({ transparent: true, depthWrite: false, roughness: 1 }));
    this.nubes = new T.Mesh(this.registrar(new T.SphereGeometry(1.018, 72, 48)), this.materialNubes);
    this.uAtmosfera = { uColor: { value: new T.Color(ATMOSFERAS.templado) } };
    const atmosfera = new T.Mesh(
      this.registrar(new T.SphereGeometry(1.1, 64, 48)),
      this.registrar(new T.ShaderMaterial({
        uniforms: this.uAtmosfera, vertexShader: ATMOSFERA_VERTICE, fragmentShader: ATMOSFERA_FRAGMENTO,
        side: T.BackSide, blending: T.AdditiveBlending, transparent: true, depthWrite: false, toneMapped: false,
      })),
    );
    this.inclinacion.add(this.planeta, this.nubes);
    this.grupo.add(this.inclinacion, atmosfera);
    this.escena.add(this.grupo);
    this.tipo = null;
    this.ponerAspecto('templado');
  }

  texturasDe(tipo) {
    if (!this.texturas.has(tipo)) {
      const T = this.T;
      const { mapa, emision, nubes, ancho, alto } = pintarPlaneta(tipo);
      const crear = (datos, color) => {
        const textura = this.registrar(new T.CanvasTexture(lienzoCon(datos, ancho, alto)));
        if (color) textura.colorSpace = T.SRGBColorSpace;
        textura.anisotropy = 4;
        return textura;
      };
      this.texturas.set(tipo, {
        mapa: crear(mapa, true),
        emision: emision ? crear(emision, true) : null,
        nubes: nubes ? crear(nubes, true) : null,
      });
    }
    return this.texturas.get(tipo);
  }

  precalentar() {
    // Pinta los demás aspectos cuando el navegador está libre, así cambiar de aspecto es instantáneo
    const pendientes = Object.keys(PINTORES).filter((tipo) => !this.texturas.has(tipo));
    const siguiente = () => {
      if (this.destruida || !pendientes.length) return;
      this.texturasDe(pendientes.shift());
      (window.requestIdleCallback || setTimeout)(siguiente);
    };
    (window.requestIdleCallback || setTimeout)(siguiente);
  }

  ponerAspecto(tipo) {
    if (tipo === this.tipo) return;
    const texturas = this.texturasDe(tipo);
    this.materialPlaneta.map = texturas.mapa;
    this.materialPlaneta.emissiveMap = texturas.emision || this.materialPlaneta.emissiveMap;
    this.materialPlaneta.emissiveIntensity = texturas.emision ? 2.2 : 0;
    this.materialPlaneta.needsUpdate = true;
    this.nubes.visible = Boolean(texturas.nubes);
    if (texturas.nubes) this.materialNubes.map = texturas.nubes;
    this.materialNubes.needsUpdate = true;
    this.uAtmosfera.uColor.value.set(ATMOSFERAS[tipo]);
    this.tipo = tipo;
  }

  fijar(estado) {
    const zona = zonaHabitable(estado.temp);
    const orbita = 1 / Math.sqrt(estado.luz);
    this.objetivo = {
      escala: escalaPara(orbita),
      orbita,
      optimista: [1 / Math.sqrt(zona.optimista[1]), 1 / Math.sqrt(zona.optimista[0])],
      conservadora: [1 / Math.sqrt(zona.conservadora[1]), 1 / Math.sqrt(zona.conservadora[0])],
      radioEstrella: radioEstrellaVisual(estado.temp),
      radioPlaneta: radioPlanetaVisual(estado.radio),
      color: colorEstrella(estado.temp),
    };
    if (!this.actual) this.actual = structuredClone(this.objetivo);
    this.ponerAspecto(aspecto(estado.radio, estado.luz));
  }

  redimensionar() {
    const ancho = this.contenedor.clientWidth || 1, alto = this.contenedor.clientHeight || 1;
    this.renderer.setSize(ancho, alto, false);
    this.camara.aspect = ancho / alto;
    this.camara.updateProjectionMatrix();
    this.ancho = ancho;
    this.alto = alto;
  }

  animar(activo) {
    if (this.destruida) return;
    this.reloj.getDelta();
    this.renderer.setAnimationLoop(activo ? () => this.cuadro() : null);
  }

  acercar(dt) {
    const k = 1 - Math.exp(-dt * 5);
    const a = this.actual, o = this.objetivo;
    for (const clave of ['escala', 'orbita', 'radioEstrella', 'radioPlaneta']) a[clave] += (o[clave] - a[clave]) * k;
    for (const clave of ['optimista', 'conservadora', 'color']) {
      a[clave] = a[clave].map((v, i) => v + (o[clave][i] - v) * k);
    }
  }

  cuadro() {
    const dt = Math.min(this.reloj.getDelta(), 0.05);
    this.tiempo += dt;
    if (!this.actual) { this.renderer.render(this.escena, this.camara); return; }
    this.acercar(dt);
    const a = this.actual;
    const ritmo = this.lento ? 0.35 : 1;

    // La estrella: color, tamaño y halos
    this.uEstrella.uTiempo.value = this.tiempo;
    this.uEstrella.uColor.value.setRGB(a.color[0], a.color[1], a.color[2], this.T.SRGBColorSpace);
    this.estrella.scale.setScalar(a.radioEstrella);
    this.estrella.rotation.y += dt * 0.04 * ritmo;
    for (const halo of this.halos) {
      halo.material.color.copy(this.uEstrella.uColor.value);
      halo.scale.setScalar(a.radioEstrella * halo.userData.escala);
    }
    this.luz.color.copy(this.uEstrella.uColor.value);

    // El disco con las zonas y la órbita
    this.uDisco.uEscala.value = a.escala;
    this.uDisco.uTiempo.value = this.tiempo;
    this.uDisco.uOrbita.value = a.orbita;
    this.uDisco.uOptimista.value.set(a.optimista[0], a.optimista[1]);
    this.uDisco.uConservadora.value.set(a.conservadora[0], a.conservadora[1]);

    // El planeta en su órbita (más lento mientras más lejos, como dice Kepler)
    const radioOrbita = Math.max(a.orbita * a.escala, a.radioEstrella + a.radioPlaneta + 0.8);
    this.angulo += dt * limitar(0.3 / a.orbita ** 1.5, 0.05, 0.85) * ritmo;
    this.grupo.position.set(Math.cos(this.angulo) * radioOrbita, 0, Math.sin(this.angulo) * radioOrbita);
    this.grupo.scale.setScalar(a.radioPlaneta);
    this.planeta.rotation.y += dt * 0.22 * ritmo;
    this.nubes.rotation.y += dt * 0.27 * ritmo;
    this.cielo.rotation.y += dt * 0.003 * ritmo;

    this.controles.update(dt);
    this.renderer.render(this.escena, this.camara);
    this.moverEtiquetas(a, radioOrbita);
  }

  ubicar(elemento, x, y, z, dy = 0) {
    this.punto.set(x, y, z).project(this.camara);
    const visible = this.punto.z < 1 && Math.abs(this.punto.x) < 1.1 && Math.abs(this.punto.y) < 1.1;
    elemento.style.visibility = visible ? 'visible' : 'hidden';
    if (!visible) return;
    const px = (this.punto.x * 0.5 + 0.5) * this.ancho;
    const py = (-this.punto.y * 0.5 + 0.5) * this.alto + dy;
    elemento.style.transform = `translate3d(${px.toFixed(1)}px, ${py.toFixed(1)}px, 0) translate(-50%, -50%)`;
  }

  moverEtiquetas(a, radioOrbita) {
    const e = this.etiquetas;
    this.ubicar(e.estrella, 0, -a.radioEstrella * 1.5 - 1.2, 0, 14);
    const zona = ((a.conservadora[0] + a.conservadora[1]) / 2) * a.escala;
    const angZona = -0.72;
    this.ubicar(e.zona, Math.cos(angZona) * zona, 0, Math.sin(angZona) * zona);
    const regla = a.escala / Math.sqrt(REGLA.conservadora[0]);
    const angRegla = 2.45;
    this.ubicar(e.regla, Math.cos(angRegla) * regla, 0, Math.sin(angRegla) * regla, -12);
    const p = this.grupo.position;
    this.ubicar(e.planeta, p.x, p.y + a.radioPlaneta * 1.25 + 0.6, p.z, -12);
  }

  destruir() {
    this.destruida = true;
    clearTimeout(this.reanudar);
    this.renderer.setAnimationLoop(null);
    this.observadorTamano.disconnect();
    this.observadorVista.disconnect();
    this.renderer.domElement.removeEventListener('wheel', this.alRueda, { capture: true });
    this.controles.dispose();
    for (const recurso of this.desechables) recurso.dispose();
    this.renderer.dispose();
    this.renderer.forceContextLoss();
    this.renderer.domElement.remove();
  }
}

// ---------------------------------------------------------------------------------------------------------------
// El componente: controles, veredicto y la conexión con Python
// ---------------------------------------------------------------------------------------------------------------

function gradienteTemperatura() {
  const paradas = [2500, 3200, 4000, 5000, 5800, 7000].map((temp, i, lista) => {
    const [r, g, b] = colorEstrella(temp).map((v) => Math.round(v * 255));
    return `rgb(${r}, ${g}, ${b}) ${((i / (lista.length - 1)) * 100).toFixed(0)}%`;
  });
  return `linear-gradient(90deg, ${paradas.join(', ')})`;
}

function gradienteLuz(temp) {
  // Pinta en el control de luz dónde queda la zona habitable de esta estrella
  const zona = zonaHabitable(temp);
  const pos = (s) => (limitar(posicionDeLuz(limitar(s, LUZ_MIN, LUZ_MAX)), 0, POSICIONES) / POSICIONES * 100).toFixed(1);
  const base = 'rgba(140, 154, 179, 0.22)', opt = 'rgba(61, 220, 151, 0.38)', cons = 'rgba(61, 220, 151, 0.85)';
  const [o0, o1] = zona.optimista.map(pos), [c0, c1] = zona.conservadora.map(pos);
  return `linear-gradient(90deg, ${base} 0%, ${base} ${o0}%, ${opt} ${o0}%, ${opt} ${c0}%, ${cons} ${c0}%, `
    + `${cons} ${c1}%, ${opt} ${c1}%, ${opt} ${o1}%, ${base} ${o1}%, ${base} 100%)`;
}

class Sandbox {
  constructor(raiz) {
    this.raiz = raiz;
    const $ = (selector) => raiz.querySelector(selector);
    this.el = {
      caja: $('.sbx'), lienzo: $('.sbx__lienzo'), nombre: $('.nombre'), aspecto: $('.aspecto'), pista: $('.sbx__pista'),
      aviso: $('.sbx__aviso'), anillo: $('.anillo__valor'), anilloTexto: $('.anillo__texto'),
      titulo: $('.veredicto__titulo'), chipRegla: $('.chip--regla'), chipAcuerdo: $('.chip--acuerdo'),
      datos: $('.veredicto__datos'), radio: $('input[name="radio"]'), luz: $('input[name="luz"]'),
      temp: $('input[name="temp"]'),
      valores: { radio: $('[data-valor="radio"]'), luz: $('[data-valor="luz"]'), temp: $('[data-valor="temp"]') },
      etiquetas: {
        estrella: $('.etq--estrella'), nombreEstrella: $('.etq__nombre'), detalleEstrella: $('.etq__detalle'),
        zona: $('.etq--zona'), regla: $('.etq--regla'), planeta: $('.etq--planeta'),
      },
    };
    this.circunferencia = 2 * Math.PI * 34;
    this.el.anillo.style.strokeDasharray = `${this.circunferencia}`;
    this.el.temp.style.setProperty('--pista', gradienteTemperatura());
    this.el.radio.style.setProperty('--pista',
      'linear-gradient(90deg, rgba(122, 162, 255, 0.55) 0%, rgba(122, 162, 255, 0.55) 35%, rgba(140, 154, 179, 0.25) 35%, rgba(140, 154, 179, 0.25) 100%)');
    for (const nombre of ['radio', 'luz', 'temp']) {
      this.el[nombre].addEventListener('input', () => this.alMover(nombre));
      this.el[nombre].addEventListener('change', () => this.alSoltar());
    }
    this.estado = null;
    this.version = undefined;
    this.modelo = null;
    this.enviar = null;
    this.escena = null;
    this.iniciar3d();
  }

  async iniciar3d() {
    try {
      const { THREE, OrbitControls } = await cargarThree();
      if (this.cerrado) return;
      this.escena = new Escena3D(THREE, OrbitControls, this.el.lienzo, this.el.etiquetas, () => this.ocultarPista());
      if (this.estado) this.escena.fijar(this.estado);
      this.el.caja.dataset.estado = 'listo';
    } catch (error) {
      console.error('Vista 3D:', error);
      this.el.caja.dataset.estado = 'error';
      this.el.aviso.textContent = 'No se pudo cargar la vista 3D en este navegador. Los controles y el veredicto del '
        + 'modelo siguen funcionando.';
    }
  }

  ocultarPista() {
    this.el.pista.dataset.oculta = '';
  }

  actualizar(data) {
    clearTimeout(this.cierre);
    this.modelo = data?.modelo ?? null;
    this.el.caja.dataset.modelo = this.modelo ? 'si' : 'no';
    if (data?.planeta && data.version !== this.version) {
      this.version = data.version;
      const p = data.planeta;
      this.estado = {
        nombre: String(p.nombre ?? 'Tu planeta'),
        estrella: p.estrella ? String(p.estrella) : null,
        radio: limitar(Number(p.radio), 0.3, 4),
        luz: limitar(Number(p.luz), LUZ_MIN, LUZ_MAX),
        temp: limitar(Math.round(Number(p.temp) / 10) * 10, 2500, 7000),
      };
      this.el.radio.value = this.estado.radio;
      this.el.luz.value = posicionDeLuz(this.estado.luz);
      this.el.temp.value = this.estado.temp;
    }
    if (this.estado) this.pintar();
  }

  alMover(control) {
    if (!this.estado) return;
    this.estado = {
      ...this.estado,
      nombre: renombrar(this.estado.nombre),
      estrella: control === 'temp' ? null : this.estado.estrella,
      radio: Number(this.el.radio.value),
      luz: luzDePosicion(Number(this.el.luz.value)),
      temp: Number(this.el.temp.value),
    };
    this.pintar();
  }

  alSoltar() {
    clearTimeout(this.envio);
    this.envio = setTimeout(() => {
      const { nombre, estrella, radio, luz, temp } = this.estado;
      this.enviar?.('planeta', { nombre, estrella, radio, luz, temp });
    }, 60);
  }

  pintar() {
    const { nombre, estrella, radio, luz, temp } = this.estado;
    const tipo = aspecto(radio, luz);
    const regla = segunRegla(radio, luz);
    const prob = probabilidad(this.modelo, radio, luz, temp);
    const tempPlaneta = 255 * luz ** 0.25;

    this.el.nombre.textContent = nombre;
    this.el.aspecto.textContent = `${ASPECTOS[tipo]} · ilustración`;
    this.el.chipRegla.textContent = regla === 'no' ? 'Mi regla: no' : `Mi regla: sí (${regla})`;
    this.el.chipRegla.className = `chip chip--regla${regla === 'no' ? '' : ' chip--si'}`;
    if (prob === null) {
      this.el.titulo.textContent = 'Modelo no disponible';
      this.el.anilloTexto.textContent = '';
      this.el.chipAcuerdo.hidden = true;
    } else {
      const habitable = prob >= 0.5;
      const coinciden = habitable === (regla !== 'no');
      this.el.anillo.style.strokeDashoffset = `${this.circunferencia * (1 - prob)}`;
      this.el.anilloTexto.textContent = porcentaje(prob);
      this.el.titulo.textContent = habitable ? 'Habitable' : 'No habitable';
      this.el.chipAcuerdo.hidden = false;
      this.el.chipAcuerdo.textContent = coinciden ? 'Coinciden' : 'No coinciden';
      this.el.chipAcuerdo.className = `chip chip--acuerdo ${coinciden ? 'chip--si' : 'chip--alerta'}`;
    }
    this.el.datos.textContent = `ESI ${esi(radio, luz).toFixed(3)} · ${NUMERO.format(Math.round(tempPlaneta))} K `
      + `(${NUMERO.format(Math.round(tempPlaneta - 273.15))} °C)`;

    this.el.valores.radio.textContent = `${radio.toFixed(2)} × Tierra`;
    this.el.valores.luz.textContent = `${luz.toFixed(2)} × Tierra`;
    this.el.valores.temp.textContent = `${NUMERO.format(temp)} K · ${claseEstrella(temp)}`;
    this.el.luz.style.setProperty('--pista', gradienteLuz(temp));

    const e = this.el.etiquetas;
    e.nombreEstrella.textContent = estrella || (temp === 5780 ? 'El Sol' : 'Su estrella');
    e.detalleEstrella.textContent = `${NUMERO.format(temp)} K · ${claseEstrella(temp)}`;
    e.planeta.textContent = nombre;
    this.escena?.fijar(this.estado);
  }

  programarCierre() {
    // Streamlit puede llamar a la limpieza antes de volver a montar: se espera un momento antes de destruir
    clearTimeout(this.cierre);
    this.cierre = setTimeout(() => this.cerrar(), 1500);
  }

  cerrar() {
    this.cerrado = true;
    clearTimeout(this.envio);
    this.escena?.destruir();
    instancias.delete(this.raiz);
  }
}

const instancias = new WeakMap();

export default function (component) {
  const { parentElement, data, setStateValue } = component;
  let sandbox = instancias.get(parentElement);
  if (!sandbox) {
    sandbox = new Sandbox(parentElement);
    instancias.set(parentElement, sandbox);
  }
  sandbox.enviar = setStateValue;
  sandbox.actualizar(data);
  return () => sandbox.programarCierre();
}
