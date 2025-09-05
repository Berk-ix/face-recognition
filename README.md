<?xml version="1.0" encoding="UTF-8"?>
<!-- glitch-face-rekonnition.svg -->
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="240" viewBox="0 0 900 240">
  <defs>
    <!-- Neon glow -->
    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="b1"/>
      <feMerge>
        <feMergeNode in="b1"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <!-- Distortion noise -->
    <filter id="glitch">
      <feTurbulence id="turb" type="fractalNoise" baseFrequency="0.015" numOctaves="2" seed="3" result="noise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="6" xChannelSelector="R" yChannelSelector="G"/>
      <animate href="#turb" attributeName="seed" dur="1.2s" values="1;9;3;7;2;8;4;6;1" repeatCount="indefinite"/>
      <animate href="#turb" attributeName="baseFrequency" dur="3s" values="0.012;0.02;0.03;0.018;0.012" repeatCount="indefinite"/>
    </filter>

    <!-- Scanline overlay pattern -->
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="2" fill="rgba(255,255,255,0.04)"/>
      <rect y="2" width="4" height="2" fill="rgba(0,0,0,0)"/>
    </pattern>

    <style>
      @keyframes jitter {
        0%   { transform: translate(0,0) }
        20%  { transform: translate(1px,-1px) }
        40%  { transform: translate(-1px,1px) }
        60%  { transform: translate(1.2px,0.6px) }
        80%  { transform: translate(-1.2px,-0.6px) }
        100% { transform: translate(0,0) }
      }
      @keyframes slice {
        0%   { clip-path: inset(0 0 0 0) }
        10%  { clip-path: inset(10% 0 75% 0) }
        20%  { clip-path: inset(60% 0 20% 0) }
        30%  { clip-path: inset(30% 0 50% 0) }
        40%  { clip-path: inset(75% 0 5% 0) }
        50%  { clip-path: inset(5% 0 75% 0) }
        60%  { clip-path: inset(45% 0 35% 0) }
        70%  { clip-path: inset(20% 0 60% 0) }
        80%  { clip-path: inset(65% 0 15% 0) }
        90%  { clip-path: inset(40% 0 40% 0) }
        100% { clip-path: inset(0 0 0 0) }
      }
      @keyframes flicker {
        0%, 100% { opacity: 1 }
        48% { opacity: 0.95 }
        50% { opacity: 0.85 }
        52% { opacity: 0.98 }
      }

      .bg { fill: #0b0d12; }
      .title { font: 800 64px "Segoe UI", "Montserrat", Arial, sans-serif; letter-spacing: 6px; text-transform: uppercase; }
      .base { fill: #eaf7ff; filter: url(#glow); animation: flicker 3.5s infinite; }
      .r    { fill: #ff2a6d; mix-blend-mode: screen; animation: jitter 1.1s infinite linear alternate, slice 2.2s infinite steps(12); }
      .c    { fill: #16fff9; mix-blend-mode: screen; animation: jitter 1.1s infinite linear alternate-reverse, slice 2.0s infinite steps(11); }
      .small { font: 500 16px "Segoe UI", Arial, sans-serif; fill: #a8b3c7; letter-spacing: 2px; }
    </style>
  </defs>

  <!-- Background + scanlines -->
  <rect class="bg" x="0" y="0" width="100%" height="100%"/>
  <rect x="0" y="0" width="100%" height="100%" fill="url(#scan)" opacity="0.4"/>

  <!-- Title group -->
  <g filter="url(#glitch)" transform="translate(60,135)">
    <!-- cyan/red offset layers -->
    <text class="title c" x="0" y="0">FACE REKONNITION</text>
    <text class="title r" x="0" y="0">FACE REKONNITION</text>
    <!-- main layer -->
    <text class="title base" x="0" y="0">FACE REKONNITION</text>

    <!-- subtitle -->
    <text class="small" x="2" y="36">glitch • neon • svg</text>
  </g>
</svg>