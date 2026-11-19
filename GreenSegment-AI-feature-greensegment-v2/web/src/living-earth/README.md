# Living Earth — independent visual prototype

Open **http://127.0.0.1:5173/living-earth-preview.html** after starting Vite:

```powershell
# From the project root; FastAPI is not needed.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\project.ps1 frontend
```

The existing app remains at `/`. This preview has a separate HTML entry point, React root and scoped stylesheet. It does not import App.jsx, the app stylesheet, maps, charts, APIs or Gemini. Vite's only routing/build change is adding the second HTML entry to `rollupOptions.input`.

## Rendering

- Three.js WebGL2, imported only by this page. The renderer and GLTFLoader are loaded asynchronously.
- True SphereGeometry Earth, radius 1.3; a separate, slightly larger cloud sphere and a restrained Fresnel atmospheric shell.
- Axial tilt 0.18 radians. Surface rotation uses elapsed active time at `2π / 60` radians/second. Clouds rotate 2.5% faster. No automated camera zoom; resizing only fits the composition to the container.
- A genuine anatomical `generic-fixed-hand` GLB, 1,360 vertices / 2,314 triangles. Fixed pose, graphite physical material. The model's highest point is below the globe's lowest point, leaving a 0.30 scene-unit gap.
- Directional/hemisphere lighting, restrained teal fill, and 60 low-opacity particles (22 on mobile). No bloom, post-processing pipeline, orbit rings or star field.
- On mobile: 1K day texture, no normal-map request, fewer sphere segments, 22 particles, pixel ratio capped at 1.25 (desktop 1.75).

## Motion and lifecycle

The Pause and Particles buttons support keyboard/touch and expose `aria-pressed`. `prefers-reduced-motion` produces a static composition and disables the resume control; changing that preference is handled live.

There is one requestAnimationFrame loop. It stops while paused, out of view, in a hidden tab, or after context loss. On resumption it continues from the last active angle, avoiding catch-up jumps. ResizeObserver, IntersectionObserver, visibility listeners, geometries, materials, textures, renderer and late-loading assets are cleaned up on disposal.

If WebGL2 is unavailable, asset loading fails, or the WebGL context is lost, a local static render (`scene-poster.webp`) replaces the canvas. Content remains available. Context restoration resumes the existing scene.

## Assets and quality limits

Sources, exact download URLs, modifications and licenses are recorded in `../../public/living-earth/CREDITS.md`. The hand's MIT notice and Three.js MIT notice are included there as separate files.

This is a semirealistic sculpture study, not a photorealistic hand scan. The lightweight model lacks detailed skin folds, fingernails, a long forearm and a custom supporting-palm sculpt. For production close-ups, commission or license a higher-detail hand/forearm in the approved pose and replace the GLB at the `prepareHand` integration boundary. Keep its source/license notice and adjust the pose/bounds there; do not substitute primitive fingers.

Textures are 1K–2K visual composites. Higher-quality rendering would benefit from a licensed custom hand, additional art direction, and device-GPU measurements. The prototype does not imply that its Earth textures represent emissions data.

## Checks

```powershell
cd web
npm.cmd run build
```

With Vite dev or preview running, browser checks are:

```powershell
# From the project root. Override LIVING_EARTH_UI_URL or MARKET_CHROME if needed.
.\.venv\Scripts\python.exe tests\ui_living_earth.py
```

The tests inspect 1440/1024/768/390/320px layouts, real 3D rotation, pause/particles, reduced motion, WebGL fallback/context recovery, visibility handling and isolation from the existing application. Browser screenshots and measured results are written to `.local/living-earth/`; the test renderer uses headless Chrome's software WebGL and does not establish real-device GPU performance.

Hidden `data-*` attributes on the scene host expose rotation, rendering state, resource state and quality for evaluating this prototype; they are not analytical data.
