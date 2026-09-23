import React, { useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { useTwinStore } from '../../../stores/useTwinStore';
import {
  calculatePistonDisplacement,
  calculateRodAngle,
  CYLINDER_PHASE_OFFSETS,
  DEFAULT_KINEMATICS,
} from '../kinematics';

interface PistonAssemblyProps {
  cylinderIndex: 1 | 2 | 3 | 4;
  crankAngle: number;
  zOffset: number;
}

export const PistonAssembly: React.FC<PistonAssemblyProps> = ({
  cylinderIndex,
  crankAngle,
  zOffset,
}) => {
  const pistonRef = useRef<THREE.Group>(null);
  const rodRef = useRef<THREE.Group>(null);
  const { wireframe, visualizationMode } = useTwinStore();

  const isLeftBank = cylinderIndex === 1 || cylinderIndex === 3;
  const bankSign = isLeftBank ? -1.0 : 1.0;
  const phaseOffset = CYLINDER_PHASE_OFFSETS[cylinderIndex - 1];

  const { crankRadius, connectingRodLength, cylinderBoreRadius } = DEFAULT_KINEMATICS;

  useFrame(() => {
    const theta = crankAngle + phaseOffset;
    const disp = calculatePistonDisplacement(theta, crankRadius, connectingRodLength);
    const rodAngle = calculateRodAngle(theta, crankRadius, connectingRodLength);

    if (pistonRef.current) {
      pistonRef.current.position.x = bankSign * disp;
    }

    if (rodRef.current) {
      // Crank throw pin position
      const crankPinX = crankRadius * Math.cos(theta);
      const crankPinY = crankRadius * Math.sin(theta);
      rodRef.current.position.set(crankPinX, crankPinY, zOffset);
      rodRef.current.rotation.z = bankSign * rodAngle + (isLeftBank ? Math.PI : 0);
    }
  });

  return (
    <group name={`PistonAssembly_Cyl${cylinderIndex}`}>
      {/* Reciprocating Piston Head */}
      <group ref={pistonRef} position={[bankSign * (crankRadius + connectingRodLength), 0, zOffset]}>
        {/* Piston Crown (cylinder oriented along X axis) */}
        <mesh rotation={[0, 0, Math.PI / 2]} castShadow receiveShadow>
          <cylinderGeometry args={[cylinderBoreRadius * 0.96, cylinderBoreRadius * 0.96, 0.045, 24]} />
          <meshStandardMaterial
            color="#cbd5e1"
            metalness={0.75}
            roughness={0.3}
            wireframe={wireframe}
          />
        </mesh>

        {/* Compression Ring Detail (darker ring band) */}
        <mesh position={[bankSign * 0.012, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[cylinderBoreRadius * 0.97, cylinderBoreRadius * 0.97, 0.004, 24]} />
          <meshStandardMaterial color="#334155" metalness={0.9} roughness={0.1} />
        </mesh>

        {/* Gudgeon (Wrist) Pin */}
        <mesh rotation={[Math.PI / 2, 0, 0]} castShadow>
          <cylinderGeometry args={[0.009, 0.009, cylinderBoreRadius * 1.6, 16]} />
          <meshStandardMaterial color="#94a3b8" metalness={0.8} roughness={0.2} />
        </mesh>
      </group>

      {/* Connecting Rod (Pivots from crank pin to piston pin) */}
      <group ref={rodRef} position={[0, 0, zOffset]}>
        {/* Rod Beam */}
        <mesh
          position={[connectingRodLength / 2, 0, 0]}
          rotation={[0, 0, Math.PI / 2]}
          castShadow
        >
          <boxGeometry args={[0.012, connectingRodLength, 0.014]} />
          <meshStandardMaterial
            color="#94a3b8"
            metalness={0.8}
            roughness={0.25}
            wireframe={wireframe || visualizationMode === 'CUTAWAY'}
          />
        </mesh>

        {/* Big End Journal Bearing (Crankshaft side) */}
        <mesh rotation={[Math.PI / 2, 0, 0]} castShadow>
          <cylinderGeometry args={[0.016, 0.016, 0.018, 16]} />
          <meshStandardMaterial color="#64748b" metalness={0.85} roughness={0.2} />
        </mesh>

        {/* Small End Eye (Piston pin side) */}
        <mesh position={[connectingRodLength, 0, 0]} rotation={[Math.PI / 2, 0, 0]} castShadow>
          <cylinderGeometry args={[0.013, 0.013, 0.016, 16]} />
          <meshStandardMaterial color="#64748b" metalness={0.85} roughness={0.2} />
        </mesh>
      </group>
    </group>
  );
};
