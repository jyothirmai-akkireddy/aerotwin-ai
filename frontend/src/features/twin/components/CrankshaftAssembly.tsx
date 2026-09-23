import React, { useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { useTwinStore } from '../../../stores/useTwinStore';
import { DEFAULT_KINEMATICS } from '../kinematics';

interface CrankshaftProps {
  crankAngle: number;
}

export const CrankshaftAssembly: React.FC<CrankshaftProps> = ({ crankAngle }) => {
  const groupRef = useRef<THREE.Group>(null);
  const { wireframe } = useTwinStore();
  const { crankRadius } = DEFAULT_KINEMATICS;

  useFrame(() => {
    if (groupRef.current) {
      groupRef.current.rotation.z = crankAngle;
    }
  });

  return (
    <group ref={groupRef} name="Crankshaft">
      {/* Main Shaft Core (along Z axis) */}
      <mesh rotation={[Math.PI / 2, 0, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[0.016, 0.016, 0.28, 24]} />
        <meshStandardMaterial
          color="#94a3b8"
          metalness={0.85}
          roughness={0.2}
          wireframe={wireframe}
        />
      </mesh>

      {/* Front Propeller Hub Flange */}
      <mesh position={[0, 0, 0.145]} rotation={[Math.PI / 2, 0, 0]} castShadow>
        <cylinderGeometry args={[0.045, 0.045, 0.012, 32]} />
        <meshStandardMaterial
          color="#64748b"
          metalness={0.9}
          roughness={0.25}
          wireframe={wireframe}
        />
      </mesh>

      {/* Rear Flywheel Gear Ring */}
      <mesh position={[0, 0, -0.145]} rotation={[Math.PI / 2, 0, 0]} castShadow>
        <cylinderGeometry args={[0.055, 0.055, 0.015, 36]} />
        <meshStandardMaterial
          color="#475569"
          metalness={0.8}
          roughness={0.3}
          wireframe={wireframe}
        />
      </mesh>

      {/* Crank Throw 1 (Z = +0.06, Angle = 0) */}
      <group position={[0, 0, 0.06]}>
        <mesh position={[crankRadius, 0, 0]} rotation={[Math.PI / 2, 0, 0]} castShadow>
          <cylinderGeometry args={[0.011, 0.011, 0.02, 16]} />
          <meshStandardMaterial color="#cbd5e1" metalness={0.9} roughness={0.15} wireframe={wireframe} />
        </mesh>
        {/* Counterweight */}
        <mesh position={[-crankRadius * 0.9, 0, 0]} castShadow>
          <boxGeometry args={[crankRadius * 1.2, 0.025, 0.018]} />
          <meshStandardMaterial color="#64748b" metalness={0.7} roughness={0.4} wireframe={wireframe} />
        </mesh>
      </group>

      {/* Crank Throw 2 (Z = +0.02, Angle = PI) */}
      <group position={[0, 0, 0.02]} rotation={[0, 0, Math.PI]}>
        <mesh position={[crankRadius, 0, 0]} rotation={[Math.PI / 2, 0, 0]} castShadow>
          <cylinderGeometry args={[0.011, 0.011, 0.02, 16]} />
          <meshStandardMaterial color="#cbd5e1" metalness={0.9} roughness={0.15} wireframe={wireframe} />
        </mesh>
        <mesh position={[-crankRadius * 0.9, 0, 0]} castShadow>
          <boxGeometry args={[crankRadius * 1.2, 0.025, 0.018]} />
          <meshStandardMaterial color="#64748b" metalness={0.7} roughness={0.4} wireframe={wireframe} />
        </mesh>
      </group>

      {/* Crank Throw 3 (Z = -0.02, Angle = PI) */}
      <group position={[0, 0, -0.02]} rotation={[0, 0, Math.PI]}>
        <mesh position={[crankRadius, 0, 0]} rotation={[Math.PI / 2, 0, 0]} castShadow>
          <cylinderGeometry args={[0.011, 0.011, 0.02, 16]} />
          <meshStandardMaterial color="#cbd5e1" metalness={0.9} roughness={0.15} wireframe={wireframe} />
        </mesh>
        <mesh position={[-crankRadius * 0.9, 0, 0]} castShadow>
          <boxGeometry args={[crankRadius * 1.2, 0.025, 0.018]} />
          <meshStandardMaterial color="#64748b" metalness={0.7} roughness={0.4} wireframe={wireframe} />
        </mesh>
      </group>

      {/* Crank Throw 4 (Z = -0.06, Angle = 0) */}
      <group position={[0, 0, -0.06]}>
        <mesh position={[crankRadius, 0, 0]} rotation={[Math.PI / 2, 0, 0]} castShadow>
          <cylinderGeometry args={[0.011, 0.011, 0.02, 16]} />
          <meshStandardMaterial color="#cbd5e1" metalness={0.9} roughness={0.15} wireframe={wireframe} />
        </mesh>
        <mesh position={[-crankRadius * 0.9, 0, 0]} castShadow>
          <boxGeometry args={[crankRadius * 1.2, 0.025, 0.018]} />
          <meshStandardMaterial color="#64748b" metalness={0.7} roughness={0.4} wireframe={wireframe} />
        </mesh>
      </group>
    </group>
  );
};
