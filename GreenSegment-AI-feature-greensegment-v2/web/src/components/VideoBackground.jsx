import React, { memo, useEffect, useRef, useState } from 'react';

const VIDEO_SOURCE = '/media/earth_smooth_loop_preview_2x_upscaled.mp4';
const POSTER_SOURCE = '/media/earth-smooth-loop-poster.webp';

function VideoBackground() {
  const videoRef = useRef(null);
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => {
      setReducedMotion(preference.matches);
      if (!preference.matches) setFailed(false);
    };
    preference.addEventListener('change', update);
    return () => preference.removeEventListener('change', update);
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || reducedMotion || failed) return;
    let cancelled = false;
    video.muted = true;
    // Native looping owns playback. This effect never depends on page/filter state.
    video.play()?.catch((error) => {
      if (!cancelled && error.name !== 'AbortError') setFailed(true);
    });
    return () => { cancelled = true; video.pause(); };
  }, [reducedMotion, failed]);

  return <div className="video-background" aria-hidden="true">
    <img className="video-background-poster" src={POSTER_SOURCE} alt="" draggable="false"/>
    {!reducedMotion && !failed && <video ref={videoRef} src={VIDEO_SOURCE} poster={POSTER_SOURCE}
      autoPlay muted loop playsInline preload="auto" tabIndex={-1} disablePictureInPicture
      onError={() => setFailed(true)}/>}
  </div>;
}

export default memo(VideoBackground);
