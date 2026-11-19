# Living Earth — asset credits

All files are served locally. The preview makes no runtime requests to asset CDNs, NASA, external fonts, FastAPI or Gemini.

## Earth textures

- Author/publisher: **Solar System Scope / INOVE**.
- Source and license declaration: https://www.solarsystemscope.com/textures/
- License: **Creative Commons Attribution 4.0 International (CC BY 4.0)**: https://creativecommons.org/licenses/by/4.0/
- The publisher describes the Earth maps as adjusted composites based on NASA imagery / Blue Marble and other geographical data. These are visual reference textures, not current weather or EDGAR emissions data.
- Retrieved: **2026-11-13**.

| Local asset | Original URL | Changes |
| --- | --- | --- |
| `earth-day-2048.jpg` | https://www.solarsystemscope.com/textures/download/2k_earth_daymap.jpg | Original 2048 × 1024 JPEG |
| `earth-day-1024.webp` | Same day map | Resized to 1024 × 512, WebP quality 88 for mobile |
| `earth-clouds-1024.webp` | https://www.solarsystemscope.com/textures/download/2k_earth_clouds.jpg | Grayscale, resized to 1024 × 512, WebP quality 86 |
| `earth-normal-1024.webp` | https://www.solarsystemscope.com/textures/download/2k_earth_normal_map.tif | Resized to 1024 × 512, lossless WebP |
| `earth-specular-1024.webp` | https://www.solarsystemscope.com/textures/download/2k_earth_specular_map.tif | Grayscale, resized to 1024 × 512, WebP quality 88 |

Credit when reusing: **Earth textures by Solar System Scope / INOVE, CC BY 4.0, based on NASA imagery; resized/converted for the GreenSegment AI Living Earth prototype.** No NASA or asset-publisher endorsement is implied.

## Hand

`hand-left.glb`: Immersive Web / WebXR Input Profiles, `generic-fixed-hand`, MIT, copyright (c) 2019 Amazon.

- Model: https://github.com/immersive-web/webxr-input-profiles/tree/main/packages/assets/profiles/generic-fixed-hand
- Complete license: `HAND-LICENSE.txt`.
- Provenance and geometry limitations: `HAND-SOURCE.md`.
- Modifications in the scene: whole-model pose, scale and graphite material. No anatomical mesh was assembled from primitives.

## Renderer and original scene

- **Three.js 0.187.0**, MIT: https://github.com/mrdoob/three.js. License copied to `THREE-LICENSE.txt`.
- GLTFLoader is included in Three.js; no additional rendering framework is installed.
- `scene-poster.webp` is a static render of this prototype, made from the same credited Earth textures and hand model. Attribution and their respective licenses continue to apply to this derivative image.
- Forest gradients, atmospheric shader, floating-particle shader, layout and material setup are authored in the project. No Dribbble image, stock hand photograph or unverified model is used.
