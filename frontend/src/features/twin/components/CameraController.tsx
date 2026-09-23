import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useThree, useFrame } from '@react-three/fiber';
import { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { OrbitControls } from '@react-three/drei';
import { CameraPreset, useTwinStore } from '../../../stores/useTwinStore';

const PRESET_CONFIGS: Record<CameraPreset, { position: [number, number, number]; target: [number, number, number] }> = {
  ISOMETRIC: { position: [0.55, 0.4, 0.55], target: [0, 0, 0] },
  FRONT: { position: [0, 0.05, 0.65], target: [0, 0, 0] },
  TOP: { position: [0, 0.75, 0.001], target: [0, 0, 0] },
  LEFT_BANK: { position: [-0.55, 0.1, 0], target: [-0.08, 0, 0] },
  RIGHT_BANK: { position: [0.55, 0.1, 0], target: [0.08, 0, 0] },
};

export const CameraController: React.FC = () => {
  const controlsRef = useRef<OrbitControlsImpl>(null);
  const { camera } = useThree();
  const { cameraPreset, cameraResetTrigger, selectedCylinder } = useTwinStore();

  const targetPosRef = useRef<THREE.Vector3>(new THREE.Vector3(...PRESET_CONFIGS.ISOMETRIC.position));
  const targetLookAtRef = useRef<THREE.Vector3>(new THREE.Vector3(...PRESET_CONFIGS.ISOMETRIC.target));
  const isTransitioningRef = useRef<boolean>(false);

  // React to preset changes
  useEffect(() => {
    let preset = PRESET_CONFIGS[cameraPreset];
    // If a cylinder is selected, adjust focus to that cylinder's bank
    if (selectedCylinder === 1 || selectedCylinder === 3) {
      preset = PRESET_CONFIGS.LEFT_BANK;
    } else if (selectedCylinder === 2 || selectedCylinder === 4) {
      preset = PRESET_CONFIGS.RIGHT_BANK;
    }

    targetPosRef.current.set(...preset.position);
    targetLookAtRef.current.set(...preset.target);
    isTransitioningRef.current = true;
  }, [cameraPreset, cameraResetTrigger, selectedCylinder]);

  // Smooth lerp transition inside animation frame
  useFrame(() => {
    if (isTransitioningRef.current && controlsRef.current) {
      camera.position.lerp(targetPosRef.current, 0.08);
      controlsRef.current.target.lerp(targetLookAtRef.current, 0.08);
      controlsRef.current.update();

      if (camera.position.distanceTo(targetPosRef.current) < 0.005) {
        camera.position.copy(targetPosRef.current);
        controlsRef.current.target.copy(targetLookAtRef.current);
        isTransitioningRef.current = false;
      }
    }
  });

  return (
    <OrbitControls
      ref={controlsRef}
      enableDamping
      dampingFactor={0.08}
      minDistance={0.25}
      maxDistance={2.2}
      maxPolarAngle={Math.PI / 2 + 0.1} // Prevent going below ground grid
    />
  );
};
