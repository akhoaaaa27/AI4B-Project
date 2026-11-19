# Shared Earth video background

`earth_smooth_loop_preview_2x_upscaled.mp4` is the active, user-provided clip. It is 1472 × 828 (16:9), 14 seconds, H.264/AVC (`avc1`) at 25 fps (350 frames), with no audio track. It is 5,271,556 bytes. SHA-256: `2eed43347a8741e3cc95cd7111d8a5be668bd4e4dd660237388bfe0333e58c86`. Its filename gives the upgrade a distinct cache URL. The app serves the supplied file as-is.

The previous smooth-loop video, `earth_smooth_loop_preview.mp4`, is kept for rollback:

- Actual resolution: **736 × 414**, 16:9. This is **not native 2560 × 1440/QHD**.
- Duration: **14.0 seconds**.
- Video: **H.264/AVC (`avc1`), 25 fps, 350 frames**.
- Audio: **no audio track**; the HTML element is also muted.
- Size: **1,458,134 bytes**.
- SHA-256: `31b088d11a7fe2ef6c313194fe1ec964f59ce4eb7048c8fa9c462268516d8285`.
- `earth-smooth-loop-poster.webp`: the first decoded frame of the previous smooth-loop clip, 736 × 414. The app continues using this WebP for static fallback and reduced motion.
- Original `earth.mp4` and `earth-poster.webp` are retained. The original remains 848,908 bytes, 16 seconds; SHA-256: `e89f402e6c8329476150c87cbf84adf88b3c16c3df186d70c8d1d1fe8e0b5734`.

The component `web/src/components/VideoBackground.jsx` mounts once inside App's root layout, before the sidebar and page content. Page/filter changes leave the video DOM node and its playback position intact. Native `autoPlay`, `muted`, `loop` and `playsInline` handle playback; there is no animation timer, custom loop, new visible control or per-page video.

The fixed background fills the viewport, including the area beneath the sidebar. Existing opaque sidebar/card backgrounds remain opaque and cover the video where those components are drawn. `isolation: isolate` on the app shell keeps the decorative negative-z layer above the document backdrop and behind existing UI. `pointer-events: none` prevents it intercepting input. Portrait viewports use `object-position: 20% center` to retain the Earth's curved edge as much as possible; `object-fit: cover` preserves proportions and necessarily crops a landscape clip on tall screens.

Reduced motion shows the poster without mounting/requesting the video. Load failures and rejected playback promises also fall back to the poster. Existing fallback page color remains available if neither media asset loads. A preference change back to normal motion mounts the video again; ordinary app navigation does not remount it.

## Source limits and future replacement

For the previous 736 × 414 clip, Chrome headless observed three consecutive natural loops at normal speed (1,050 presented frames): no black frames, playback errors or pause events. Boundary presentation gaps were approximately 33–67 ms, with three native `waiting` events. First/last-frame average RGB difference for that clip was about 2.59/255 versus 8.05/255 for the original. These are historical measurements for the previous clip.

For a future source replacement, use a distinct filename, update the two media constants in `VideoBackground.jsx`, and regenerate a matching poster. No page/layout restructuring or caching-policy changes are required. Update these metadata notes accordingly.

This change does not recolor text, cards or sidebar, add contrast overlays, or restyle layouts. Contrast against the moving background is reserved for the later UI redesign. The independent `living-earth-preview.html` retains its own scene because it does not use App's main layout.
