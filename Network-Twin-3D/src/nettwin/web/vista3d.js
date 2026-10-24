/*
  PT-PT: Núcleo 3D partilhado pelas vistas: renderizador, câmara, luzes,
         ambiente (reflexos), brilho (bloom), selecção com o rato,
         enquadramento animado e o ciclo de animação (tráfego nos cabos,
         LEDs a piscar).

         As vistas (rede, edifício, bastidor) só acrescentam objectos ao
         grupo `world` e registam o que é clicável em `pickables`.

  EN-UK: 3D core shared by the views: renderer, camera, lights, environment
         (reflections), bloom, mouse picking, animated framing and the
         animation loop (cable traffic, blinking LEDs). Views only add
         objects to `world` and register clickables in `pickables`.

  Created by Redfox using Claude
*/

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/OrbitControls.js';
import { CSS2DRenderer } from 'three/addons/CSS2DRenderer.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { blinkers } from './modelos.js';

export class Viewer {
  constructor(stage, canvas, labelsEl) {
    this.stage = stage;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;

    this.labels = new CSS2DRenderer({ element: labelsEl });
    this.scene = new THREE.Scene();
    this.scene.background = gradientTexture();
    // PT-PT: Ambiente para reflexos: é o que faz o metal parecer metal.
    // EN-UK: Environment for reflections: what makes metal look like metal.
    this.scene.environment = new THREE.PMREMGenerator(this.renderer).fromScene(new RoomEnvironment(), 0.04).texture;
    this.scene.environmentIntensity = 0.55;

    this.camera = new THREE.PerspectiveCamera(42, 1, 0.02, 2000);
    this.camera.position.set(0, 18, 38);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.maxPolarAngle = Math.PI * 0.495;

    this.scene.add(new THREE.HemisphereLight(0xdfe6ff, 0x1a1c20, 0.9));
    this.sun = new THREE.DirectionalLight(0xffffff, 1.6);
    this.sun.position.set(30, 60, 40);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.bias = -0.0004;
    this.scene.add(this.sun, this.sun.target);

    this.world = new THREE.Group();
    this.scene.add(this.world);
    this.ground = new THREE.GridHelper(600, 300, 0x262a30, 0x1b1d21);
    this.ground.position.y = -6;
    this.scene.add(this.ground);

    this.composer = new EffectComposer(this.renderer);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    this.bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.5, 0.4, 0.96);
    this.composer.addPass(this.bloom);
    this.composer.addPass(new OutputPass());
    this.useBloom = true;

    this.pickables = [];
    this.particles = [];
    this.tween = null;
    this.showFlow = true;
    this.onPick = () => {};
    this.onHover = () => {};
    this.onGroundClick = null;   // usado pelo "mover bastidor"
    this.timer = new THREE.Timer();
    this.blinkClock = 0;

    new ResizeObserver(() => this.resize()).observe(stage);
    this.resize();
    this._wirePointer();
    requestAnimationFrame((t) => this._animate(t));
  }

  resize() {
    const { clientWidth: w, clientHeight: h } = this.stage;
    this.renderer.setSize(w, h, false);
    this.composer.setSize(w, h);
    this.labels.setSize(w, h);
    this.camera.aspect = w / Math.max(h, 1);
    this.camera.updateProjectionMatrix();
  }

  /** PT-PT: Esvazia o mundo e liberta a memória da GPU. / EN-UK: Clears the world, freeing GPU memory. */
  clear() {
    for (const child of [...this.world.children]) {
      this.world.remove(child);
      child.traverse((o) => {
        if (o.isCSS2DObject) o.element.remove();
        if (o.geometry && !o.geometry.userData.shared) o.geometry.dispose();
        if (o.material) {
          for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
            if (m.userData.shared) continue;
            if (m.map && !m.map.userData.cached) m.map.dispose();
            m.dispose();
          }
        }
      });
    }
    this.pickables = [];
    this.particles = [];
  }

  /**
   * PT-PT: Ajusta a sombra do sol ao tamanho do que está desenhado — uma
   *        sombra de 600 m para um bastidor de 2 m sairia em blocos.
   * EN-UK: Fits the sun's shadow to what is drawn.
   */
  fitShadow() {
    const box = new THREE.Box3().setFromObject(this.world);
    if (box.isEmpty()) return;
    const c = box.getCenter(new THREE.Vector3());
    const r = Math.max(box.getSize(new THREE.Vector3()).length() / 2, 2);
    const cam = this.sun.shadow.camera;
    cam.left = -r; cam.right = r; cam.top = r; cam.bottom = -r; cam.near = 0.5; cam.far = r * 6;
    cam.updateProjectionMatrix();
    this.sun.position.copy(c).add(new THREE.Vector3(r * 0.6, r * 1.6, r));
    this.sun.target.position.copy(c);
  }

  /**
   * PT-PT: Enquadra objectos (ou tudo) com uma animação curta. A distância
   *        vem da esfera envolvente e do campo de visão mais apertado.
   * EN-UK: Frames objects (or everything) with a short animation.
   */
  fit(objects = null, { dir = new THREE.Vector3(0.2, 0.45, 1), margin = 1, shift = null } = {}) {
    const box = new THREE.Box3();
    for (const o of objects ?? this.world.children.filter((c) => !c.isCSS2DObject)) box.expandByObject(o);
    if (box.isEmpty()) return;
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    if (shift) sphere.center.add(shift);
    const vfov = THREE.MathUtils.degToRad(this.camera.fov);
    const hfov = 2 * Math.atan(Math.tan(vfov / 2) * this.camera.aspect);
    const dist = Math.max((sphere.radius / Math.sin(Math.min(vfov, hfov) / 2)) * margin, 0.8);
    this.tween = {
      fromPos: this.camera.position.clone(),
      toPos: sphere.center.clone().add(dir.clone().normalize().multiplyScalar(dist)),
      fromTarget: this.controls.target.clone(),
      toTarget: sphere.center.clone(),
      // PT-PT: Pelo relógio real, não pelo dt de cada frame: com poucos FPS
      //        (PC fraco, renderização por software) o dt é limitado e a
      //        animação arrastava-se segundos.
      // EN-UK: By wall clock, not per-frame dt: at low FPS dt is clamped and
      //        the animation dragged on for seconds.
      start: performance.now(),
      duration: 450,
    };
  }

  addPickable(object) {
    object.traverse((o) => { if (o.isMesh) this.pickables.push(o); });
  }

  // ---------------------------------------------------------------------
  // PT-PT: Rato. / EN-UK: Pointer.
  // ---------------------------------------------------------------------

  _wirePointer() {
    const el = this.renderer.domElement;
    const ray = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let downAt = null;
    const hit = (e) => {
      const r = el.getBoundingClientRect();
      pointer.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(pointer, this.camera);
      const visible = this.pickables.filter((o) => isVisible(o));
      return ray.intersectObjects(visible, false)[0] ?? null;
    };
    el.addEventListener('pointerdown', (e) => { downAt = [e.clientX, e.clientY]; });
    el.addEventListener('pointerup', (e) => {
      if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 4) return;
      const h = hit(e);
      if (this.onGroundClick && h?.object.userData.ground) {
        this.onGroundClick(h.point, h.object.userData.ground);
        return;
      }
      this.onPick(h ? h.object.userData.pick ?? null : null, h);
    });
    el.addEventListener('pointermove', (e) => {
      const h = hit(e);
      const pick = h?.object.userData.pick;
      el.style.cursor = this.onGroundClick ? (h?.object.userData.ground ? 'crosshair' : 'not-allowed') : pick ? 'pointer' : 'default';
      this.onHover(pick ?? null);
    });
  }

  // ---------------------------------------------------------------------
  // PT-PT: Animação. / EN-UK: Animation.
  // ---------------------------------------------------------------------

  _animate(t) {
    requestAnimationFrame((tt) => this._animate(tt));
    this.timer.update(t);
    const dt = Math.min(this.timer.getDelta(), 0.05);
    if (this.tween) {
      const tw = this.tween;
      const p = Math.min(1, (performance.now() - tw.start) / tw.duration);
      const k = 1 - Math.pow(1 - p, 3);
      this.camera.position.lerpVectors(tw.fromPos, tw.toPos, k);
      this.controls.target.lerpVectors(tw.fromTarget, tw.toTarget, k);
      if (p >= 1) this.tween = null;
    }
    for (const p of this.particles) {
      p.visible = this.showFlow && isVisible(p.parent ?? p);
      if (!p.visible) continue;
      p.userData.t = (p.userData.t + dt * p.userData.speed) % 1;
      p.position.copy(p.userData.curve.getPointAt(p.userData.t));
    }
    // PT-PT: LEDs: a cada ~120 ms, ~12 % das portas activas trocam de estado,
    //        como tráfego a sério (não um pisca-pisca sincronizado).
    // EN-UK: LEDs: every ~120 ms ~12 % of active ports flip, like real traffic.
    this.blinkClock += dt;
    if (this.blinkClock > 0.12) {
      this.blinkClock = 0;
      for (const mesh of blinkers) {
        const { active, color, dim } = mesh.userData.blink;
        if (!active || !isVisible(mesh)) continue;
        for (let k = 0; k < Math.max(1, active * 0.12); k++) {
          const i = Math.floor(Math.random() * active);
          mesh.setColorAt(i, Math.random() < 0.5 ? dim : color);
        }
        mesh.instanceColor.needsUpdate = true;
      }
    }
    this.controls.update();
    if (this.useBloom) this.composer.render();
    else this.renderer.render(this.scene, this.camera);
    this.labels.render(this.scene, this.camera);
  }
}

export function isVisible(o) {
  for (let n = o; n; n = n.parent) if (n.visible === false) return false;
  return true;
}

/**
 * PT-PT: Guarda a opacidade base para o "esmaecer" ser reversível.
 * EN-UK: Keeps the base opacity so dimming is reversible.
 */
export function remember(object) {
  object.traverse((o) => {
    for (const m of o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : []) {
      if (m.userData.baseOpacity === undefined) {
        m.userData.baseOpacity = m.opacity;
        m.userData.baseTransparent = m.transparent;
      }
    }
  });
  return object;
}

export function setDim(object, dim) {
  object.traverse((o) => {
    for (const m of o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : []) {
      if (m.userData.baseOpacity === undefined || m.userData.shared) continue;
      m.transparent = dim ? true : m.userData.baseTransparent;
      m.opacity = m.userData.baseOpacity * (dim ? 0.12 : 1);
      m.depthWrite = !dim && m.userData.baseTransparent !== true;
    }
  });
}

function gradientTexture() {
  const c = document.createElement('canvas');
  c.width = 4; c.height = 256;
  const g = c.getContext('2d');
  const grad = g.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0, '#1d2433');
  grad.addColorStop(0.55, '#131519');
  grad.addColorStop(1, '#0d0e11');
  g.fillStyle = grad;
  g.fillRect(0, 0, 4, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
