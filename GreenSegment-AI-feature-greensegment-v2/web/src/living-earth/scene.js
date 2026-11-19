import {
  ACESFilmicToneMapping, AdditiveBlending, Box3, BufferGeometry, Color, DirectionalLight,
  Float32BufferAttribute, Group, HemisphereLight, Mesh, MeshPhongMaterial, MeshPhysicalMaterial,
  PerspectiveCamera, PointLight, Points, Scene, ShaderMaterial, SphereGeometry, SRGBColorSpace,
  TextureLoader, Vector2, Vector3, WebGLRenderer,
} from 'three';

const ASSETS = '/living-earth/';
export const ROTATION_PERIOD = 60;
const RADIANS_PER_SECOND = Math.PI * 2 / ROTATION_PERIOD;
const INITIAL_ANGLE = -1.65;
const EARTH_RADIUS = 1.3;
const EARTH_Y = 1.15;

function disposeObject(object) {
  const geometries = new Set(), materials = new Set(), textures = new Set();
  object.traverse((node) => {
    if (node.geometry) geometries.add(node.geometry);
    for (const material of Array.isArray(node.material) ? node.material : [node.material]) {
      if (!material) continue;
      materials.add(material);
      for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
    }
  });
  textures.forEach((texture) => texture.dispose());
  materials.forEach((material) => material.dispose());
  geometries.forEach((geometry) => geometry.dispose());
}

function makeAtmosphere() {
  return new Mesh(new SphereGeometry(EARTH_RADIUS * 1.026, 64, 40), new ShaderMaterial({
    transparent: true, depthWrite: false, blending: AdditiveBlending,
    vertexShader: `varying vec3 n; varying vec3 view;
      void main() { vec4 p = modelViewMatrix * vec4(position, 1.); n = normalize(normalMatrix * normal);
        view = normalize(-p.xyz); gl_Position = projectionMatrix * p; }`,
    fragmentShader: `varying vec3 n; varying vec3 view;
      void main() { float rim = pow(1. - max(dot(normalize(n), normalize(view)), 0.), 3.5);
        gl_FragColor = vec4(.16, .48, .62, rim * .24); }`,
  }));
}

function makeParticles() {
  const positions = [], seeds = [];
  // Stable distribution; these are environmental motes, not city/emissions data.
  let seed = 29;
  const random = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
  for (let i = 0; i < 60; i++) {
    positions.push((random() - .5) * 6.2, (random() - .5) * 5.4, (random() - .5) * 4.5);
    seeds.push(random() * 12);
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new Float32BufferAttribute(positions, 3));
  geometry.setAttribute('seed', new Float32BufferAttribute(seeds, 1));
  return new Points(geometry, new ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { time: { value: 0 }, pixelRatio: { value: 1 } },
    vertexShader: `attribute float seed; uniform float time; uniform float pixelRatio; varying float alpha;
      void main() { vec3 p = position; p.x += sin(time * .12 + seed) * .10;
        p.y += sin(time * .08 + seed * 2.) * .17; vec4 mv = modelViewMatrix * vec4(p, 1.);
        gl_Position = projectionMatrix * mv; gl_PointSize = (1.8 + mod(seed, 1.8)) * pixelRatio;
        alpha = .15 + mod(seed, 1.) * .22; }`,
    fragmentShader: `varying float alpha;
      void main() { float r = length(gl_PointCoord - .5); float soft = 1. - smoothstep(.06, .5, r);
        gl_FragColor = vec4(.72, .89, .81, soft * soft * alpha); }`,
  }));
}

function prepareHand(model) {
  // The licensed hand is a single anatomical mesh. Only its material and whole-object pose change.
  const graphite = new MeshPhysicalMaterial({ color: '#4a5b62', roughness: .74, metalness: .1, clearcoat: .02 });
  model.traverse((node) => {
    if (!node.isMesh) return;
    const original = Array.isArray(node.material) ? node.material : [node.material];
    original.forEach((material) => material?.dispose());
    node.material = graphite;
    node.layers.enable(1);
  });
  const palmUp = new Group();
  palmUp.rotation.z = Math.PI / 2;
  palmUp.add(model);
  const tilt = new Group();
  tilt.rotation.x = .55;
  tilt.add(palmUp);
  const hand = new Group();
  hand.rotation.y = -.2;
  hand.add(tilt);
  hand.scale.setScalar(16.5);
  hand.updateMatrixWorld(true);
  const bounds = new Box3().setFromObject(hand);
  const center = bounds.getCenter(new Vector3());
  hand.position.set(.12 - center.x, -.45 - bounds.max.y, .15 - center.z);
  return hand;
}

export function createLivingEarthScene(host, initialPreferences) {
  const { onMode } = initialPreferences;
  let preferences = initialPreferences;
  let disposed = false, ready = false, contextLost = false, intersecting = true;
  let frame = null, previousTime = null, activeSeconds = 0, frameCount = 0;
  const textures = new Set();
  const scene = new Scene();
  const renderer = new WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'low-power' });
  renderer.setClearColor(0x071a18, 0);
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.domElement.setAttribute('aria-hidden', 'true');
  host.appendChild(renderer.domElement);
  host.dataset.sceneStatus = 'loading';
  host.dataset.rotationPeriod = String(ROTATION_PERIOD);
  const camera = new PerspectiveCamera(37, 1, .1, 50);
  camera.layers.enable(1);
  const smallAtStart = window.innerWidth <= 600;
  const earthAxis = new Group();
  earthAxis.position.y = EARTH_Y;
  earthAxis.rotation.z = .18;
  scene.add(earthAxis);
  const earthMaterial = new MeshPhongMaterial({ color: '#ffffff', specular: '#22343e', shininess: 20, normalScale: new Vector2(.45, .45) });
  const earth = new Mesh(new SphereGeometry(EARTH_RADIUS, smallAtStart ? 48 : 80, smallAtStart ? 32 : 48), earthMaterial);
  earth.rotation.y = INITIAL_ANGLE;
  earthAxis.add(earth);
  const atmosphere = makeAtmosphere();
  earthAxis.add(atmosphere);
  const clouds = new Mesh(new SphereGeometry(EARTH_RADIUS * 1.009, 48, 32), new MeshPhongMaterial({
    color: '#f0f5f7', transparent: true, opacity: .39, depthWrite: false, shininess: 1,
  }));
  clouds.visible = false;
  earthAxis.add(clouds);
  const particles = makeParticles();
  scene.add(particles);
  scene.add(new HemisphereLight('#c7e0df', '#10271c', .85));
  const sun = new DirectionalLight('#fff4e5', 2.6);
  sun.position.set(-4, 4, 6);
  scene.add(sun);
  const rim = new DirectionalLight('#4b9ba2', 1.3);
  rim.position.set(3, 1, -3);
  scene.add(rim);
  const palmLight = new PointLight('#75dfbd', .65, 5, 2);
  palmLight.position.set(0, -.1, 1.3);
  palmLight.layers.set(1);
  scene.add(palmLight);

  function render() {
    if (disposed || contextLost) return;
    renderer.render(scene, camera);
    host.dataset.earthAngle = earth.rotation.y.toFixed(6);
    host.dataset.renderCount = String(++frameCount);
    host.dataset.drawCalls = String(renderer.info.render.calls);
  }
  function shouldAnimate() {
    return ready && !disposed && !contextLost && !preferences.paused && !preferences.reduced
      && intersecting && document.visibilityState === 'visible';
  }
  function tick(now) {
    frame = null;
    if (!shouldAnimate()) { previousTime = null; return; }
    if (previousTime !== null) activeSeconds += (now - previousTime) / 1000;
    previousTime = now;
    earth.rotation.y = INITIAL_ANGLE + activeSeconds * RADIANS_PER_SECOND;
    clouds.rotation.y = earth.rotation.y * 1.025 + .25;
    particles.material.uniforms.time.value = activeSeconds;
    render();
    frame = requestAnimationFrame(tick);
  }
  function synchronize() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null; previousTime = null;
    if (disposed || !ready) return;
    particles.visible = preferences.particles;
    host.dataset.motion = preferences.reduced ? 'reduced' : preferences.paused ? 'paused' : shouldAnimate() ? 'running' : 'suspended';
    render();
    if (shouldAnimate()) frame = requestAnimationFrame(tick);
  }
  function resize() {
    if (disposed) return;
    const { width, height } = host.getBoundingClientRect();
    if (!width || !height) return;
    const small = window.innerWidth <= 600;
    const ratio = Math.min(window.devicePixelRatio || 1, small ? 1.25 : 1.75);
    renderer.setPixelRatio(ratio);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.position.set(0, 1, Math.max(7.8, 3.8 / (camera.aspect * 2 * Math.tan(37 * Math.PI / 360))));
    camera.lookAt(0, .1, 0);
    camera.updateProjectionMatrix();
    particles.geometry.setDrawRange(0, small ? 22 : 60);
    particles.material.uniforms.pixelRatio.value = ratio;
    host.dataset.quality = small ? 'mobile' : 'desktop';
    host.dataset.pixelRatio = String(ratio);
    if (ready) render();
  }
  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(host);
  const intersectionObserver = new IntersectionObserver(([entry]) => { intersecting = entry.isIntersecting; synchronize(); }, { threshold: .03 });
  intersectionObserver.observe(host);
  const visibilityChanged = () => synchronize();
  document.addEventListener('visibilitychange', visibilityChanged);
  const lost = (event) => { event.preventDefault(); contextLost = true; host.dataset.sceneStatus = 'fallback'; synchronize(); onMode('fallback'); };
  const restored = () => { contextLost = false; if (ready) { host.dataset.sceneStatus = 'ready'; onMode('ready'); synchronize(); } };
  renderer.domElement.addEventListener('webglcontextlost', lost);
  renderer.domElement.addEventListener('webglcontextrestored', restored);
  resize();

  function dispose() {
    if (disposed) return;
    disposed = true;
    if (frame !== null) cancelAnimationFrame(frame);
    resizeObserver.disconnect(); intersectionObserver.disconnect();
    document.removeEventListener('visibilitychange', visibilityChanged);
    renderer.domElement.removeEventListener('webglcontextlost', lost);
    renderer.domElement.removeEventListener('webglcontextrestored', restored);
    disposeObject(scene);
    textures.forEach((texture) => texture.dispose());
    renderer.dispose(); renderer.forceContextLoss(); renderer.domElement.remove();
  }
  const loader = new TextureLoader();
  function loadTexture(name, color = false) {
    return loader.loadAsync(ASSETS + name).then((texture) => {
      if (disposed) { texture.dispose(); return null; }
      textures.add(texture);
      if (color) texture.colorSpace = SRGBColorSpace;
      texture.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy());
      return texture;
    });
  }
  const day = loadTexture(smallAtStart ? 'earth-day-1024.webp' : 'earth-day-2048.jpg', true).then((texture) => {
    if (disposed) return;
    earthMaterial.map = texture; earthMaterial.needsUpdate = true;
  });
  const hand = import('three/addons/loaders/GLTFLoader.js').then(({ GLTFLoader }) => new GLTFLoader().loadAsync(ASSETS + 'hand-left.glb')).then((gltf) => {
    if (disposed) { disposeObject(gltf.scene); return; }
    const mesh = prepareHand(gltf.scene);
    scene.add(mesh);
    mesh.updateMatrixWorld(true);
    host.dataset.handTop = new Box3().setFromObject(mesh).max.y.toFixed(3);
    host.dataset.earthBottom = (EARTH_Y - EARTH_RADIUS).toFixed(3);
    host.dataset.handLoaded = 'true';
  });
  // Optional texture failures leave the base Earth usable.
  loadTexture('earth-clouds-1024.webp').then((texture) => {
    if (disposed || !texture) return;
    clouds.material.alphaMap = texture; clouds.material.needsUpdate = true; clouds.visible = true;
    if (ready) render();
  }).catch(() => {});
  loadTexture('earth-specular-1024.webp').then((texture) => {
    if (disposed || !texture) return;
    earthMaterial.specularMap = texture; earthMaterial.needsUpdate = true; if (ready) render();
  }).catch(() => {});
  if (!smallAtStart) loadTexture('earth-normal-1024.webp').then((texture) => {
    if (disposed || !texture) return;
    earthMaterial.normalMap = texture; earthMaterial.needsUpdate = true; if (ready) render();
  }).catch(() => {});
  Promise.all([day, hand]).then(() => {
    if (disposed) return;
    ready = true; host.dataset.sceneStatus = 'ready'; onMode('ready'); synchronize();
  }).catch(() => { if (!disposed) { host.dataset.sceneStatus = 'fallback'; onMode('fallback'); dispose(); } });
  return {
    setPreferences(next) { preferences = { ...preferences, ...next }; synchronize(); },
    dispose,
  };
}
