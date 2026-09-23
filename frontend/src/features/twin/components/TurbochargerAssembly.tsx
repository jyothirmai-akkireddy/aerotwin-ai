import React, { useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { useTwinStore } from '../../../stores/useTwinStore';

export const TurbochargerAssembly: React.FC = () => {
  const impellerRef = useRef<THREE.Group>(null);
  const { explodedDistance, wireframe, telemetry } = useTwinStore();

  // Position: Top-Rear of engine
  const explodedY = explodedDistance * 0.08;
  const explodedZ = -explodedDistance * 0.06;

  useFrame((_, delta) => {
    if (impellerRef.current) {
      // Impeller spins faster than engine RPM based on boost level
      const boostFactor = Math.max(1.0, telemetry.manifoldPressure / 29.92);
      const turboOmega = (telemetry.rpm * 2.0 * Math.PI / 60.0) * boostFactor * 2.5;
      impellerRef.current.rotation.z += turboOmega * delta * 0.1;
    }
  });

  return (
    <group
      name="Turbocharger"
      position={[0, 0.13 + explodedY, -0.13 + explodedZ]}
    >
      {/* Center Bearing Housing (CHRA) */}
      <mesh rotation={[0, 0, Math.PI / 2]} castShadow>
        <cylinderGeometry args={[0.024, 0.024, 0.045, 20]} />
        <meshStandardMaterial
          color="#475569"
          metalness={0.7}
          roughness={0.35}
          wireframe={wireframe}
        />
      </mesh>

      {/* Compressor Housing (Front, Aluminum Cast) */}
      <group position={[0, 0, 0.035]}>
        {/* Volute Scroll Ring */}
        <mesh rotation={[0, 0, 0]} castShadow>
          <torusGeometry args={[0.042, 0.016, 16, 32]} />
          <meshStandardMaterial
            color="#cbd5e1"
            metalness={0.8}
            roughness={0.25}
            wireframe={wireframe}
          />
        </mesh>

        {/* Air Inlet Snout */}
        <mesh position={[0, 0, 0.018]} rotation={[0, 0, 0]} castShadow>
          <cylinderGeometry args={[0.022, 0.026, 0.035, 24]} />
          <meshStandardMaterial
            color="#94a3b8"
            metalness={0.75}
            roughness={0.3}
            wireframe={wireframe}
          />
        </mesh>

        {/* Compressor Impeller Blades (Rotating inside inlet) */}
        <group ref={impellerRef} position={[0, 0, 0.02]}>
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <mesh key={i} rotation={[0, 0, (i * Math.PI) / 3]}>
              <boxGeometry args={[0.003, 0.034, 0.008]} />
              <meshStandardMaterial color="#e2e8f0" metalness={0.9} roughness={0.1} />
            </mesh>
          ))}
        </group>
      </group>

      {/* Turbine Exhaust Housing (Rear, High-Temp Alloy) */}
      <group position={[0, 0, -0.035]}>
        <mesh rotation={[0, 0, 0]} castShadow>
          <torusGeometry args={[0.04, 0.015, 16, 32]} />
          <meshStandardMaterial
            color="#334155"
            metalness={0.6}
            roughness={0.6}
            wireframe={wireframe}
          />
        </mesh>
        {/* Exhaust Discharge Flange */}
        <mesh position={[0, 0.035, -0.01]} rotation={[Math.PI / 4, 0, 0]} castShadow>
          <cylinderGeometry args={[0.022, 0.022, 0.04, 20]} />
          <meshStandardMaterial color="#1e293b" metalness={0.5} roughness={0.7} />
        </mesh>
      </group>

      {/* Wastegate Actuator Canister */}
      <group position={[0.055, 0.025, 0.01]}>
        <mesh rotation={[0, 0, Math.PI / 2]} castShadow>
          <cylinderGeometry args={[0.014, 0.014, 0.03, 16]} />
          <meshStandardMaterial color="#64748b" metalness={0.8} roughness={0.3} />
        </mesh>
        {/* Actuator Rod */}
        <mesh position={[-0.02, -0.01, -0.02]} rotation={[0, 0.5, 0]}>
          <cylinderGeometry args={[0.002, 0.002, 0.045, 8]} />
          <meshStandardMaterial color="#d4d4d8" metalness={0.9} roughness={0.2} />
        </mesh>
      </group>
    </group>
  );
};
