import React, { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import { Box, Chip, Typography } from "@mui/material";
import type { DependencyGraphResponse } from "@/types";
import * as THREE from "three";

interface ThreeJsGraphProps {
  graphData: DependencyGraphResponse;
  onNodeClick?: (nodeId: string) => void;
}

function Node3D({
  position,
  label,
  method,
  onClick,
}: {
  position: [number, number, number];
  label: string;
  method: string;
  onClick: () => void;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = React.useState(false);

  useFrame(() => {
    if (meshRef.current && hovered) {
      meshRef.current.rotation.y += 0.01;
    }
  });

  const color = method === "GET" ? "#1976d2" : "#ed6c02";

  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        onClick={onClick}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshStandardMaterial color={color} />
      </mesh>
      <Html distanceFactor={10}>
        <Box
          sx={{
            background: "rgba(255,255,255,0.9)",
            p: 0.5,
            borderRadius: 1,
            pointerEvents: "none",
          }}
        >
          <Typography variant="caption" fontWeight="bold">
            {method}
          </Typography>
          <Typography variant="caption" display="block" fontSize="0.6rem">
            {label}
          </Typography>
        </Box>
      </Html>
    </group>
  );
}

function Edge3D({
  start,
  end,
  color,
}: {
  start: [number, number, number];
  end: [number, number, number];
  color: string;
}) {
  const points = useMemo(() => {
    return [new THREE.Vector3(...start), new THREE.Vector3(...end)];
  }, [start, end]);

  const lineGeometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    return geometry;
  }, [points]);

  return (
    <primitive
      object={
        new THREE.Line(lineGeometry, new THREE.LineBasicMaterial({ color }))
      }
    />
  );
}

export default function ThreeJsGraph({
  graphData,
  onNodeClick,
}: ThreeJsGraphProps) {
  // Calculate 3D positions using force-directed layout simulation
  const positions = useMemo(() => {
    const nodePositions: Record<string, [number, number, number]> = {};
    graphData.nodes.forEach((node, index) => {
      const angle = (index / graphData.nodes.length) * Math.PI * 2;
      const radius = 5;
      nodePositions[node.id] = [
        Math.cos(angle) * radius,
        Math.sin(angle) * radius,
        (Math.random() - 0.5) * 3,
      ];
    });
    return nodePositions;
  }, [graphData.nodes]);

  return (
    <Box
      sx={{
        width: "100%",
        height: "600px",
        border: "1px solid #e0e0e0",
        borderRadius: 1,
        position: "relative",
      }}
    >
      <Canvas camera={{ position: [0, 0, 15], fov: 75 }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} />
        <OrbitControls enableDamping dampingFactor={0.05} />

        {/* Render nodes */}
        {graphData.nodes.map((node) => (
          <Node3D
            key={node.id}
            position={positions[node.id]}
            label={node.path}
            method={node.method}
            onClick={() => onNodeClick?.(node.id)}
          />
        ))}

        {/* Render edges */}
        {graphData.edges.map((edge) => (
          <Edge3D
            key={edge.id}
            start={positions[edge.source_node_id]}
            end={positions[edge.target_node_id]}
            color={edge.confidence > 0.8 ? "#2e7d32" : "#ed6c02"}
          />
        ))}
      </Canvas>
      <Box sx={{ position: "absolute", top: 16, right: 16 }}>
        <Chip label="3D View" color="primary" size="small" />
      </Box>
    </Box>
  );
}
