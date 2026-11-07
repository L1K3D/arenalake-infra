/**
 * ============================================================================
 * ArenaLake — Mar de Dados 3D (WebGL / Three.js)
 * Simulação 3D em tempo real com malha ondulante de partículas e conexões.
 * GPU-accelerated real-time WebGL canvas background.
 * ============================================================================
 */

let lakeInitialized = false;

function initParticleLake() {
    if (lakeInitialized) return;
    const canvas = document.getElementById('lake-canvas');
    if (!canvas || typeof THREE === 'undefined') return;

    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        canvas.style.display = 'none';
        return;
    }

    lakeInitialized = true;

    // Densidade da malha
    const SEPARATION = 14;
    const AMOUNTX = 220; // 220x220 = 48.400 partículas (ótimo custo-benefício e 60fps)
    const AMOUNTY = 220;
    let camera, scene, renderer, particles, lines;
    let count = 0;
    let animId = null;

    // 1. Câmera
    camera = new THREE.PerspectiveCamera(65, window.innerWidth / window.innerHeight, 1, 10000);
    camera.position.x = 0;
    camera.position.y = 380;
    camera.position.z = 1400;
    camera.rotation.x = -0.38; // Inclinação para baixo

    // 2. Cena e Névoa de horizonte
    scene = new THREE.Scene();
    // Cor da névoa IGUAL à cor do background da marca (#121620)
    scene.fog = new THREE.FogExp2(0x121620, 0.00075);

    // 3. Geometria das Partículas
    const numParticles = AMOUNTX * AMOUNTY;
    const positions = new Float32Array(numParticles * 3);
    const colors = new Float32Array(numParticles * 3);

    // Paleta de Cores oficial ArenaLake
    const cCiano = new THREE.Color(0x00d2ff);   // Rede / fluxo
    const cLaranja = new THREE.Color(0xf39200); // Pontos de destaque
    const cAzulBase = new THREE.Color(0x0a1529);// Fundo profundo

    let i = 0;
    for (let ix = 0; ix < AMOUNTX; ix++) {
        for (let iy = 0; iy < AMOUNTY; iy++) {
            positions[i] = ix * SEPARATION - ((AMOUNTX * SEPARATION) / 2);
            positions[i + 1] = -250; // Altura base
            positions[i + 2] = iy * SEPARATION - ((AMOUNTY * SEPARATION) / 2);

            // Distribuição de cor: maioria azul escuro, 18% ciano, 1.5% laranja
            const rand = Math.random();
            let c = cAzulBase;
            if (rand > 0.985) c = cLaranja;
            else if (rand > 0.82) c = cCiano;

            colors[i] = c.r;
            colors[i + 1] = c.g;
            colors[i + 2] = c.b;
            i += 3;
        }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // Material das partículas com brilho somado (AdditiveBlending)
    const materialParticles = new THREE.PointsMaterial({
        vertexColors: true,
        size: 5.0,
        transparent: true,
        opacity: 0.28,
        blending: THREE.AdditiveBlending,
        depthWrite: false
    });

    particles = new THREE.Points(geometry, materialParticles);
    scene.add(particles);

    // 4. Linhas de Conexão (Malha de dados)
    const numLines = (AMOUNTX - 1) * (AMOUNTY - 1) * 2;
    const indicesLine = new Int32Array(numLines * 2);
    let lineIdx = 0;

    for (let ix = 0; ix < AMOUNTX - 1; ix++) {
        for (let iy = 0; iy < AMOUNTY - 1; iy++) {
            if (Math.random() > 0.88) {
                indicesLine[lineIdx * 2] = ix * AMOUNTY + iy;
                indicesLine[lineIdx * 2 + 1] = (ix + 1) * AMOUNTY + iy;
                lineIdx++;
            }
            if (Math.random() > 0.88) {
                indicesLine[lineIdx * 2] = ix * AMOUNTY + iy;
                indicesLine[lineIdx * 2 + 1] = ix * AMOUNTY + (iy + 1);
                lineIdx++;
            }
        }
    }

    const geometryLine = new THREE.BufferGeometry();
    geometryLine.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometryLine.setIndex(new THREE.BufferAttribute(indicesLine.subarray(0, lineIdx * 2), 1));

    const materialLines = new THREE.LineBasicMaterial({
        color: 0x00d2ff,
        transparent: true,
        opacity: 0.10
    });

    lines = new THREE.LineSegments(geometryLine, materialLines);
    scene.add(lines);

    // 5. Renderizador WebGL
    renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);

    function onWindowResize() {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    }

    window.addEventListener('resize', onWindowResize, { passive: true });

    // 6. Loop de Animação das Ondas
    function animate() {
        animId = requestAnimationFrame(animate);

        const posArray = particles.geometry.attributes.position.array;
        let idx = 1; // Eixo Y
        for (let ix = 0; ix < AMOUNTX; ix++) {
            for (let iy = 0; iy < AMOUNTY; iy++) {
                const wave1 = Math.sin((ix + count) * 0.18) * 20;
                const wave2 = Math.cos((iy + count) * 0.12) * 15;
                const grandSwell = Math.sin((ix + iy + count * 0.4) * 0.04) * 35;
                posArray[idx] = -250 + wave1 + wave2 + grandSwell;
                idx += 3;
            }
        }

        particles.geometry.attributes.position.needsUpdate = true;
        lines.geometry.attributes.position.needsUpdate = true;

        renderer.render(scene, camera);
        count += 0.035;
    }

    animate();

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            cancelAnimationFrame(animId);
        } else {
            animate();
        }
    });
}

// Auto-inicialização inteligente no carregamento da página
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initParticleLake);
} else {
    initParticleLake();
}
