import React, { useRef, useState } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import { useTwinStore } from '../../../stores/useTwinStore';
import { advanceCrankAngle } from '../kinematics';
import { CrankshaftAssembly } from './CrankshaftAssembly';
import { PistonAssembly } from './PistonAssembly';
import { CylinderAssembly } from './CylinderAssembly';
import { TurbochargerAssembly } from './TurbochargerAssembly';
import { IntakeExhaustAssembly } from './IntakeExhaustAssembly';

export const EngineModel: React.FC = () => {
  const masterGroupRef = useRef<THREE.Group>(null);
  const crankAngleRef = useRef<number>(0.0);
  const [currentCrankAngle, setCurrentCrankAngle] = useState<number>(0.0);

  const {
    telemetry,
    visualRpmMultiplier,
    isPaused,
    wireframe,
    visualizationMode,
    explodedDistance,
    showLabels,
    selectedCylinder,
    setSelectedCylinder,
  } = useTwinStore();

  // Crank offsets along Z axis for cylinders 1-4
  const zOffsets = [0.06, 0.02, -0.02, -0.06];

  useFrame((_, delta) => {
    if (!isPaused && telemetry.rpm > 0) {
      const nextAngle = advanceCrankAngle(
        crankAngleRef.current,
        telemetry.rpm,
        delta,
        visualRpmMultiplier
      );
      crankAngleRef.current = nextAngle;
      // Update state for components that subscribe to the continuous rotation
      setCurrentCrankAngle(nextAngle);
    }
  });

  const explodedSumpY = -explodedDistance * 0.06;

  return (
    <group ref={masterGroupRef} name="EngineRoot" position={[0, 0, 0]}>
      {/* ============================================================== */}
      {/* CENTRAL CRANKCASE CASTING                                     */}
      {/* ============================================================== */}
      <group name="Crankcase">
        {/* Main Center Tunnel */}
        <mesh position={[0, 0, 0]} castShadow receiveShadow>
          <boxGeometry args={[0.13, 0.11, 0.27]} />
          <meshStandardMaterial
            color="#475569"
            metalness={0.7}
            roughness={0.4}
            wireframe={wireframe || visualizationMode === 'CUTAWAY'}
            transparent={visualizationMode === 'CUTAWAY'}
            opacity={visualizationMode === 'CUTAWAY' ? 0.3 : 1.0}
          />
        </mesh>

        {/* Cylinder Bank Mounting Flanges (Left & Right) */}
        <mesh position={[-0.07, 0, 0]} castShadow>
          <boxGeometry args={[0.015, 0.12, 0.24]} />
          <meshStandardMaterial color="#64748b" metalness={0.7} roughness={0.3} wireframe={wireframe} />
        </mesh>
        <mesh position={[0.07, 0, 0]} castShadow>
          <boxGeometry args={[0.015, 0.12, 0.24]} />
          <meshStandardMaterial color="#64748b" metalness={0.7} roughness={0.3} wireframe={wireframe} />
        </mesh>

        {/* Crankcase Stiffening Ribs */}
        {[-0.08, 0, 0.08].map((z, idx) => (
          <mesh key={idx} position={[0, 0.058, z]} castShadow>
            <boxGeometry args={[0.11, 0.008, 0.012]} />
            <meshStandardMaterial color="#334155" metalness={0.8} roughness={0.3} />
          </mesh>
        ))}
      </group>

      {/* ============================================================== */}
      {/* CRANKSHAFT ROTATING ASSEMBLY                                  */}
      {/* ============================================================== */}
      <CrankshaftAssembly crankAngle={currentCrankAngle} />

      {/* ============================================================== */}
      {/* PISTONS & CONNECTING RODS (Cylinders 1-4)                     */}
      {/* ============================================================== */}
      <PistonAssembly cylinderIndex={1} crankAngle={currentCrankAngle} zOffset={zOffsets[0]} />
      <PistonAssembly cylinderIndex={2} crankAngle={currentCrankAngle} zOffset={zOffsets[1]} />
      <PistonAssembly cylinderIndex={3} crankAngle={currentCrankAngle} zOffset={zOffsets[2]} />
      <PistonAssembly cylinderIndex={4} crankAngle={currentCrankAngle} zOffset={zOffsets[3]} />

      {/* ============================================================== */}
      {/* CYLINDERS & HEADS (Cylinders 1-4)                             */}
      {/* ============================================================== */}
      <CylinderAssembly cylinderIndex={1} zOffset={zOffsets[0]} />
      <CylinderAssembly cylinderIndex={2} zOffset={zOffsets[1]} />
      <CylinderAssembly cylinderIndex={3} zOffset={zOffsets[2]} />
      <CylinderAssembly cylinderIndex={4} zOffset={zOffsets[3]} />

      {/* ============================================================== */}
      {/* TURBOCHARGER & INTAKE / EXHAUST MANIFOLDS                      */}
      {/* ============================================================== */}
      <TurbochargerAssembly />
      <IntakeExhaustAssembly />

      {/* ============================================================== */}
      {/* ACCESSORIES (Oil Sump, Alternator, Starter)                   */}
      {/* ============================================================== */}
      {/* Wet Oil Sump (Bottom) */}
      <group position={[0, -0.065 + explodedSumpY, 0]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[0.11, 0.035, 0.24]} />
          <meshStandardMaterial color="#1e293b" metalness={0.6} roughness={0.5} wireframe={wireframe} />
        </mesh>
        {/* Sump Cooling Ribs */}
        {[-0.06, -0.02, 0.02, 0.06].map((z, idx) => (
          <mesh key={idx} position={[0, -0.019, z]}>
            <boxGeometry args={[0.09, 0.004, 0.008]} />
            <meshStandardMaterial color="#0f172a" roughness={0.4} />
          </mesh>
        ))}
      </group>

      {/* Alternator (Front Top Left) */}
      <group position={[-0.055, 0.08, 0.12]}>
        <mesh rotation={[Math.PI / 2, 0, 0]} castShadow>
          <cylinderGeometry args={[0.024, 0.024, 0.045, 16]} />
          <meshStandardMaterial color="#475569" metalness={0.8} roughness={0.3} wireframe={wireframe} />
        </mesh>
        {/* Drive Belt Pulley */}
        <mesh position={[0, 0, 0.024]} rotation={[Math.PI / 2, 0, 0]} castShadow>
          <cylinderGeometry args={[0.018, 0.018, 0.008, 16]} />
          <meshStandardMaterial color="#0f172a" roughness={0.5} />
        </mesh>
      </group>

      {/* Starter Motor (Rear Bellhousing) */}
      <group position={[0.055, -0.03, -0.135]}>
        <mesh rotation={[Math.PI / 2, 0, 0]} castShadow>
          <cylinderGeometry args={[0.02, 0.02, 0.06, 16]} />
          <meshStandardMaterial color="#334155" metalness={0.7} roughness={0.4} wireframe={wireframe} />
        </mesh>
      </group>

      {/* ============================================================== */}
      {/* 3D SPATIAL LABELS / ANNOTATIONS                                */}
      {/* ============================================================== */}
      {showLabels && (
        <group name="Annotations">
          {/* Cylinder 1 Label */}
          <Html position={[-0.19, 0.07, zOffsets[0]]} center distanceFactor={1.2}>
            <button
              onClick={() => setSelectedCylinder(selectedCylinder === 1 ? null : 1)}
              className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded border transition-colors shadow-lg cursor-pointer ${
                selectedCylinder === 1
                  ? 'bg-sky-500 text-slate-950 border-sky-300'
                  : 'bg-slate-900/90 text-sky-400 border-slate-700 hover:border-sky-500'
              }`}
            >
              CYL 1: {telemetry.cht[0]?.toFixed(0)}°C
            </button>
          </Html>

          {/* Cylinder 2 Label */}
          <Html position={[0.19, 0.07, zOffsets[1]]} center distanceFactor={1.2}>
            <button
              onClick={() => setSelectedCylinder(selectedCylinder === 2 ? null : 2)}
              className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded border transition-colors shadow-lg cursor-pointer ${
                selectedCylinder === 2
                  ? 'bg-sky-500 text-slate-950 border-sky-300'
                  : 'bg-slate-900/90 text-sky-400 border-slate-700 hover:border-sky-500'
              }`}
            >
              CYL 2: {telemetry.cht[1]?.toFixed(0)}°C
            </button>
          </Html>

          {/* Cylinder 3 Label */}
          <Html position={[-0.19, 0.07, zOffsets[2]]} center distanceFactor={1.2}>
            <button
              onClick={() => setSelectedCylinder(selectedCylinder === 3 ? null : 3)}
              className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded border transition-colors shadow-lg cursor-pointer ${
                selectedCylinder === 3
                  ? 'bg-sky-500 text-slate-950 border-sky-300'
                  : 'bg-slate-900/90 text-sky-400 border-slate-700 hover:border-sky-500'
              }`}
            >
              CYL 3: {telemetry.cht[2]?.toFixed(0)}°C
            </button>
          </Html>

          {/* Cylinder 4 Label */}
          <Html position={[0.19, 0.07, zOffsets[3]]} center distanceFactor={1.2}>
            <button
              onClick={() => setSelectedCylinder(selectedCylinder === 4 ? null : 4)}
              className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded border transition-colors shadow-lg cursor-pointer ${
                selectedCylinder === 4
                  ? 'bg-sky-500 text-slate-950 border-sky-300'
                  : 'bg-slate-900/90 text-sky-400 border-slate-700 hover:border-sky-500'
              }`}
            >
              CYL 4: {telemetry.cht[3]?.toFixed(0)}°C
            </button>
          </Html>

          {/* Turbocharger Label */}
          <Html position={[0, 0.22, -0.13]} center distanceFactor={1.2}>
            <span className="px-1.5 py-0.5 text-[8px] font-mono font-semibold bg-slate-900/80 text-amber-400 rounded border border-amber-500/40">
              TURBOCHARGER
            </span>
          </Html>
        </group>
      )}
    </group>
  );
};
