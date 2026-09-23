import React from 'react';
import { useTwinStore } from '../../../stores/useTwinStore';

export const IntakeExhaustAssembly: React.FC = () => {
  const { explodedDistance, wireframe, telemetry } = useTwinStore();

  const explodedPlenumY = explodedDistance * 0.05;
  const explodedExhaustY = -explodedDistance * 0.04;

  // Throttle valve plate rotation (0 deg closed -> 90 deg wide open)
  const throttleAngle = (telemetry.throttle / 100.0) * (Math.PI / 2);

  return (
    <group name="IntakeExhaust">
      {/* ============================================================== */}
      {/* INTAKE SYSTEM (Top Plenum & Runners)                          */}
      {/* ============================================================== */}
      <group position={[0, 0.075 + explodedPlenumY, 0]}>
        {/* Central Intake Plenum Box */}
        <mesh position={[0, 0, 0]} castShadow>
          <boxGeometry args={[0.075, 0.035, 0.17]} />
          <meshStandardMaterial
            color="#334155"
            metalness={0.7}
            roughness={0.4}
            wireframe={wireframe}
          />
        </mesh>

        {/* Throttle Body Housing (Front of Plenum) */}
        <group position={[0, 0, 0.095]}>
          <mesh rotation={[Math.PI / 2, 0, 0]} castShadow>
            <cylinderGeometry args={[0.02, 0.02, 0.03, 20]} />
            <meshStandardMaterial color="#64748b" metalness={0.8} roughness={0.3} wireframe={wireframe} />
          </mesh>
          {/* Throttle Plate (Rotates with throttle position) */}
          <mesh rotation={[throttleAngle, 0, 0]}>
            <cylinderGeometry args={[0.019, 0.019, 0.002, 16]} />
            <meshStandardMaterial color="#f59e0b" metalness={0.9} roughness={0.1} />
          </mesh>
        </group>

        {/* Intake Runners to Cylinders 1-4 */}
        {/* Runner to Cyl 1 (Left Front: -X, +Z) */}
        <mesh position={[-0.07, -0.015, 0.06]} rotation={[0, 0, -0.3]} castShadow>
          <cylinderGeometry args={[0.011, 0.011, 0.075, 12]} />
          <meshStandardMaterial color="#475569" metalness={0.75} roughness={0.3} wireframe={wireframe} />
        </mesh>

        {/* Runner to Cyl 2 (Right Front: +X, +Z) */}
        <mesh position={[0.07, -0.015, 0.06]} rotation={[0, 0, 0.3]} castShadow>
          <cylinderGeometry args={[0.011, 0.011, 0.075, 12]} />
          <meshStandardMaterial color="#475569" metalness={0.75} roughness={0.3} wireframe={wireframe} />
        </mesh>

        {/* Runner to Cyl 3 (Left Rear: -X, -Z) */}
        <mesh position={[-0.07, -0.015, -0.06]} rotation={[0, 0, -0.3]} castShadow>
          <cylinderGeometry args={[0.011, 0.011, 0.075, 12]} />
          <meshStandardMaterial color="#475569" metalness={0.75} roughness={0.3} wireframe={wireframe} />
        </mesh>

        {/* Runner to Cyl 4 (Right Rear: +X, -Z) */}
        <mesh position={[0.07, -0.015, -0.06]} rotation={[0, 0, 0.3]} castShadow>
          <cylinderGeometry args={[0.011, 0.011, 0.075, 12]} />
          <meshStandardMaterial color="#475569" metalness={0.75} roughness={0.3} wireframe={wireframe} />
        </mesh>
      </group>

      {/* ============================================================== */}
      {/* EXHAUST SYSTEM (Underside Headers routing to Turbo)           */}
      {/* ============================================================== */}
      <group position={[0, -0.05 + explodedExhaustY, 0]}>
        {/* Stainless Steel Tuned Header Pipes */}
        {/* Header from Cyl 1 (Left Front) */}
        <mesh position={[-0.075, 0, 0.03]} rotation={[-0.4, 0, 0.4]} castShadow>
          <cylinderGeometry args={[0.012, 0.012, 0.09, 12]} />
          <meshStandardMaterial color="#64748b" metalness={0.65} roughness={0.4} wireframe={wireframe} />
        </mesh>

        {/* Header from Cyl 2 (Right Front) */}
        <mesh position={[0.075, 0, 0.03]} rotation={[-0.4, 0, -0.4]} castShadow>
          <cylinderGeometry args={[0.012, 0.012, 0.09, 12]} />
          <meshStandardMaterial color="#64748b" metalness={0.65} roughness={0.4} wireframe={wireframe} />
        </mesh>

        {/* Header from Cyl 3 (Left Rear) */}
        <mesh position={[-0.065, 0.02, -0.06]} rotation={[0.4, 0, 0.3]} castShadow>
          <cylinderGeometry args={[0.012, 0.012, 0.08, 12]} />
          <meshStandardMaterial color="#64748b" metalness={0.65} roughness={0.4} wireframe={wireframe} />
        </mesh>

        {/* Header from Cyl 4 (Right Rear) */}
        <mesh position={[0.065, 0.02, -0.06]} rotation={[0.4, 0, -0.3]} castShadow>
          <cylinderGeometry args={[0.012, 0.012, 0.08, 12]} />
          <meshStandardMaterial color="#64748b" metalness={0.65} roughness={0.4} wireframe={wireframe} />
        </mesh>

        {/* Turbo Collector Pipe (Feeds into turbine housing at rear) */}
        <mesh position={[0, 0.07, -0.11]} rotation={[Math.PI / 3, 0, 0]} castShadow>
          <cylinderGeometry args={[0.018, 0.022, 0.09, 16]} />
          <meshStandardMaterial color="#475569" metalness={0.7} roughness={0.5} wireframe={wireframe} />
        </mesh>
      </group>
    </group>
  );
};
