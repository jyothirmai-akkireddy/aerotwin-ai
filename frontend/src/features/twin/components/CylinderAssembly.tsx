import React, { useMemo, useState } from 'react';
import { useTwinStore } from '../../../stores/useTwinStore';
import { DEFAULT_KINEMATICS } from '../kinematics';
import { getThermalColor, getThermalEmissive } from '../thermal';

interface CylinderAssemblyProps {
  cylinderIndex: 1 | 2 | 3 | 4;
  zOffset: number;
}

export const CylinderAssembly: React.FC<CylinderAssemblyProps> = ({
  cylinderIndex,
  zOffset,
}) => {
  const [hovered, setHovered] = useState(false);
  const {
    visualizationMode,
    selectedCylinder,
    setSelectedCylinder,
    explodedDistance,
    wireframe,
    telemetry,
  } = useTwinStore();

  const isLeftBank = cylinderIndex === 1 || cylinderIndex === 3;
  const bankSign = isLeftBank ? -1.0 : 1.0;
  const isSelected = selectedCylinder === cylinderIndex;

  const { cylinderBoreRadius, bankOffset } = DEFAULT_KINEMATICS;
  const barrelLength = 0.09;
  const cylinderHeadWidth = 0.035;

  // Temperature for this cylinder from telemetry state
  const chtTemp = telemetry.cht[cylinderIndex - 1] ?? 95.0;

  // Compute thermal material styling
  const { thermalColor, emissiveColor, emissiveIntensity } = useMemo(() => {
    const color = getThermalColor(chtTemp);
    const emissive = getThermalEmissive(chtTemp);
    return {
      thermalColor: color,
      emissiveColor: emissive.color,
      emissiveIntensity: emissive.intensity,
    };
  }, [chtTemp]);

  // Position with exploded view offset
  const explodedOffset = bankSign * explodedDistance * 0.09;
  const barrelCenterX = bankSign * (bankOffset + barrelLength / 2) + explodedOffset;
  const headCenterX = bankSign * (bankOffset + barrelLength + cylinderHeadWidth / 2) + explodedOffset;

  // Material resolution based on active visualization mode
  const barrelMaterial = useMemo(() => {
    if (visualizationMode === 'THERMAL') {
      return (
        <meshStandardMaterial
          color={thermalColor}
          emissive={emissiveColor}
          emissiveIntensity={emissiveIntensity}
          metalness={0.4}
          roughness={0.5}
          wireframe={wireframe}
        />
      );
    }
    if (visualizationMode === 'CUTAWAY') {
      return (
        <meshPhysicalMaterial
          color="#94a3b8"
          transmission={0.8}
          opacity={0.35}
          transparent
          roughness={0.2}
          ior={1.4}
          wireframe={wireframe}
        />
      );
    }
    return (
      <meshStandardMaterial
        color={isSelected ? '#38bdf8' : hovered ? '#cbd5e1' : '#64748b'}
        metalness={0.65}
        roughness={0.35}
        wireframe={wireframe}
      />
    );
  }, [visualizationMode, thermalColor, emissiveColor, emissiveIntensity, isSelected, hovered, wireframe]);

  const finMaterial = useMemo(() => {
    if (visualizationMode === 'THERMAL') {
      return (
        <meshStandardMaterial
          color={thermalColor}
          emissive={emissiveColor}
          emissiveIntensity={emissiveIntensity * 0.8}
          metalness={0.5}
          roughness={0.4}
          wireframe={wireframe}
        />
      );
    }
    return (
      <meshStandardMaterial
        color={isSelected ? '#38bdf8' : hovered ? '#94a3b8' : '#475569'}
        metalness={0.7}
        roughness={0.3}
        wireframe={wireframe}
      />
    );
  }, [visualizationMode, thermalColor, emissiveColor, emissiveIntensity, isSelected, hovered, wireframe]);

  const headMaterial = useMemo(() => {
    if (visualizationMode === 'THERMAL') {
      return (
        <meshStandardMaterial
          color={thermalColor}
          emissive={emissiveColor}
          emissiveIntensity={emissiveIntensity * 1.2}
          metalness={0.4}
          roughness={0.4}
          wireframe={wireframe}
        />
      );
    }
    return (
      <meshStandardMaterial
        color={isSelected ? '#0284c7' : hovered ? '#cbd5e1' : '#475569'}
        metalness={0.6}
        roughness={0.4}
        wireframe={wireframe}
      />
    );
  }, [visualizationMode, thermalColor, emissiveColor, emissiveIntensity, isSelected, hovered, wireframe]);

  // Generate 6 cooling fins along cylinder barrel
  const finCount = 6;
  const fins = useMemo(() => {
    const finArray = [];
    const finSpacing = barrelLength / (finCount + 1);
    for (let i = 1; i <= finCount; i++) {
      const finX = bankSign * (bankOffset + i * finSpacing) + explodedOffset;
      finArray.push(
        <mesh
          key={i}
          position={[finX, 0, zOffset]}
          rotation={[0, 0, Math.PI / 2]}
          castShadow
        >
          <cylinderGeometry args={[cylinderBoreRadius * 1.35, cylinderBoreRadius * 1.35, 0.003, 24]} />
          {finMaterial}
        </mesh>
      );
    }
    return finArray;
  }, [bankSign, bankOffset, barrelLength, cylinderBoreRadius, finCount, explodedOffset, zOffset, finMaterial]);

  return (
    <group
      name={`Cylinder_${cylinderIndex}`}
      onClick={(e) => {
        e.stopPropagation();
        setSelectedCylinder(isSelected ? null : cylinderIndex);
      }}
      onPointerOver={(e) => {
        e.stopPropagation();
        setHovered(true);
      }}
      onPointerOut={() => setHovered(false)}
    >
      {/* Cylinder Barrel Body */}
      <mesh
        position={[barrelCenterX, 0, zOffset]}
        rotation={[0, 0, Math.PI / 2]}
        castShadow
        receiveShadow
      >
        <cylinderGeometry
          args={[cylinderBoreRadius * 1.08, cylinderBoreRadius * 1.08, barrelLength, 24]}
        />
        {barrelMaterial}
      </mesh>

      {/* Cooling Fins */}
      {fins}

      {/* Cylinder Head (Combustion chamber casting) */}
      <group position={[headCenterX, 0, zOffset]}>
        <mesh castShadow receiveShadow>
          <boxGeometry args={[cylinderHeadWidth, 0.105, 0.095]} />
          {headMaterial}
        </mesh>

        {/* Valve Cover (Top side of head) */}
        <mesh position={[0, 0.055, 0]} castShadow>
          <boxGeometry args={[cylinderHeadWidth * 0.9, 0.015, 0.08]} />
          <meshStandardMaterial
            color={isSelected ? '#0284c7' : '#334155'}
            metalness={0.7}
            roughness={0.3}
          />
        </mesh>

        {/* Dual Spark Plugs (Aero dual-ignition standard) */}
        <mesh position={[0, 0.04, 0.025]} rotation={[0.4, 0, 0]}>
          <cylinderGeometry args={[0.005, 0.005, 0.03, 12]} />
          <meshStandardMaterial color="#f8fafc" roughness={0.1} />
        </mesh>
        <mesh position={[0, 0.04, -0.025]} rotation={[-0.4, 0, 0]}>
          <cylinderGeometry args={[0.005, 0.005, 0.03, 12]} />
          <meshStandardMaterial color="#f8fafc" roughness={0.1} />
        </mesh>

        {/* Selection Highlight Ring */}
        {isSelected && (
          <mesh rotation={[0, 0, Math.PI / 2]}>
            <torusGeometry args={[0.065, 0.003, 16, 32]} />
            <meshBasicMaterial color="#38bdf8" />
          </mesh>
        )}
      </group>
    </group>
  );
};
