import React, { Suspense, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import { detectWebGLSupport } from '../webgl';
import { WebGLFallback } from './WebGLFallback';
import { CameraController } from './CameraController';
import { EngineModel } from './EngineModel';

const SceneLoader: React.FC = () => (
  <Html center>
    <div className="flex flex-col items-center justify-center p-4 bg-slate-900/90 border border-slate-700 rounded-lg shadow-xl text-slate-200">
      <div className="w-6 h-6 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mb-2" />
      <span className="text-xs font-mono font-medium">Loading 3D Digital Twin...</span>
    </div>
  </Html>
);

export const EngineScene: React.FC = () => {
  const webglSupport = useMemo(() => detectWebGLSupport(), []);

  if (!webglSupport.supported) {
    return <WebGLFallback errorMessage={webglSupport.errorMessage} />;
  }

  return (
    <div className="relative w-full h-full min-h-[480px] bg-slate-950 overflow-hidden select-none">
      <Canvas
        camera={{ position: [0.55, 0.4, 0.55], fov: 42, near: 0.05, far: 20 }}
        shadows
        gl={{
          antialias: true,
          powerPreference: 'high-performance',
        }}
      >
        <color attach="background" args={['#030712']} />

        {/* Technical Lighting Setup */}
        <ambientLight intensity={0.7} color="#94a3b8" />
        <directionalLight
          position={[2.0, 3.5, 2.5]}
          intensity={1.3}
          castShadow
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
          shadow-camera-near={0.5}
          shadow-camera-far={8}
          shadow-camera-left={-0.6}
          shadow-camera-right={0.6}
          shadow-camera-top={0.6}
          shadow-camera-bottom={-0.6}
        />
        <directionalLight position={[-2.5, 1.5, -2.0]} intensity={0.6} color="#38bdf8" />
        <directionalLight position={[0, -2.0, -1.0]} intensity={0.3} color="#64748b" />

        {/* Ground Reference Grid */}
        <gridHelper
          args={[1.2, 24, '#1e293b', '#0f172a']}
          position={[0, -0.16, 0]}
        />

        <Suspense fallback={<SceneLoader />}>
          <EngineModel />
          <CameraController />
        </Suspense>
      </Canvas>
    </div>
  );
};
