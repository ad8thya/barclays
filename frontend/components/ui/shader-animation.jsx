"use client";

import { useRef, useEffect } from "react";
import * as THREE from "three";

export default function ShaderAnimation() {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: false });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    const vertexShader = `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = vec4(position, 1.0);
      }
    `;

    const fragmentShader = `
      precision mediump float;
      uniform float uTime;
      uniform vec2 uResolution;
      varying vec2 vUv;

      float noise(vec2 p) {
        return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
      }

      float smoothNoise(vec2 p) {
        vec2 i = floor(p);
        vec2 f = fract(p);
        f = f * f * (3.0 - 2.0 * f);
        float a = noise(i);
        float b = noise(i + vec2(1.0, 0.0));
        float c = noise(i + vec2(0.0, 1.0));
        float d = noise(i + vec2(1.0, 1.0));
        return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
      }

      float fbm(vec2 p) {
        float value = 0.0;
        float amplitude = 0.5;
        for (int i = 0; i < 6; i++) {
          value += amplitude * smoothNoise(p);
          p *= 2.0;
          amplitude *= 0.5;
        }
        return value;
      }

      void main() {
        vec2 uv = vUv;
        float aspect = uResolution.x / uResolution.y;
        uv.x *= aspect;

        float t = uTime * 0.08;

        float n1 = fbm(uv * 2.0 + vec2(t, t * 0.7));
        float n2 = fbm(uv * 3.0 - vec2(t * 0.5, t * 0.3));
        float n3 = fbm(uv * 1.5 + vec2(n1, n2) + t * 0.2);

        vec3 deepNavy = vec3(0.031, 0.051, 0.102);
        vec3 electricBlue = vec3(0.231, 0.510, 0.965);
        vec3 darkBlue = vec3(0.067, 0.094, 0.188);

        float blend = n3 * 0.4 + n1 * 0.3;
        vec3 color = mix(deepNavy, darkBlue, blend);
        color += electricBlue * n2 * 0.06;
        color += vec3(0.02) * smoothNoise(uv * 8.0 + t);

        float vignette = 1.0 - length((vUv - 0.5) * 1.4);
        vignette = smoothstep(0.0, 0.7, vignette);
        color *= vignette * 0.9 + 0.1;

        gl_FragColor = vec4(color, 1.0);
      }
    `;

    const uniforms = {
      uTime: { value: 0 },
      uResolution: { value: new THREE.Vector2(container.clientWidth, container.clientHeight) },
    };

    const material = new THREE.ShaderMaterial({ vertexShader, fragmentShader, uniforms });
    const geometry = new THREE.PlaneGeometry(2, 2);
    scene.add(new THREE.Mesh(geometry, material));

    let frameId;
    const clock = new THREE.Clock();

    function animate() {
      uniforms.uTime.value = clock.getElapsedTime();
      renderer.render(scene, camera);
      frameId = requestAnimationFrame(animate);
    }
    animate();

    function onResize() {
      const w = container.clientWidth;
      const h = container.clientHeight;
      renderer.setSize(w, h);
      uniforms.uResolution.value.set(w, h);
    }
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      geometry.dispose();
      material.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: "absolute",
        inset: 0,
        zIndex: 0,
        overflow: "hidden",
      }}
    />
  );
}
