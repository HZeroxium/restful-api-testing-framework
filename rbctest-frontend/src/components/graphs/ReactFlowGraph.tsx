import { useCallback, useMemo } from "react";
import ReactFlow, {
  type Node,
  type Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  MarkerType,
  Panel,
} from "reactflow";
import "reactflow/dist/style.css";
import { Box, Chip, Typography, IconButton } from "@mui/material";
import { Edit, Delete } from "@mui/icons-material";
import type { DependencyGraphResponse } from "@/types";

interface ReactFlowGraphProps {
  graphData: DependencyGraphResponse;
  onNodeClick?: (nodeId: string) => void;
  onEdgeClick?: (edgeId: string) => void;
  onNodeEdit?: (nodeId: string) => void;
  onNodeDelete?: (nodeId: string) => void;
  autoLayout?: "grid" | "none";
  editable?: boolean;
}

export default function ReactFlowGraph({
  graphData,
  onNodeClick,
  onEdgeClick,
  onNodeEdit,
  onNodeDelete,
  autoLayout = "grid",
  editable = false,
}: ReactFlowGraphProps) {
  // Transform backend data to ReactFlow format
  const initialNodes: Node[] = useMemo(() => {
    const getPosition = (index: number) => {
      if (autoLayout === "none") return { x: 0, y: 0 };
      // simple grid layout
      return { x: (index % 5) * 250, y: Math.floor(index / 5) * 150 };
    };

    return graphData.nodes.map((node, index) => ({
      id: node.id,
      type: "default",
      position: getPosition(index),
      data: {
        label: (
          <Box sx={{ p: 1 }}>
            <Typography variant="caption" fontWeight="bold">
              {node.method}
            </Typography>
            <Typography variant="caption" display="block" noWrap>
              {node.path}
            </Typography>
            {editable && (
              <Box sx={{ display: "flex", gap: 0.5, mt: 0.5 }}>
                <IconButton size="small" onClick={() => onNodeEdit?.(node.id)}>
                  <Edit fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={() => onNodeDelete?.(node.id)}
                >
                  <Delete fontSize="small" />
                </IconButton>
              </Box>
            )}
          </Box>
        ),
      },
      style: {
        background: node.method === "GET" ? "#e3f2fd" : "#fff3e0",
        border: "2px solid #1976d2",
        borderRadius: 8,
        padding: 10,
      },
    }));
  }, [graphData.nodes, editable, onNodeEdit, onNodeDelete, autoLayout]);

  const initialEdges: Edge[] = useMemo(() => {
    return graphData.edges.map((edge) => ({
      id: edge.id,
      source: edge.source_node_id,
      target: edge.target_node_id,
      label: edge.dependency_type,
      type: "smoothstep",
      animated: true,
      markerEnd: {
        type: MarkerType.ArrowClosed,
      },
      style: {
        stroke: edge.confidence > 0.8 ? "#2e7d32" : "#ed6c02",
        strokeWidth: 2,
      },
    }));
  }, [graphData.edges]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  return (
    <Box
      sx={{
        width: "100%",
        height: "600px",
        border: "1px solid #e0e0e0",
        borderRadius: 1,
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={editable ? onConnect : undefined}
        onNodeClick={(_, node) => onNodeClick?.(node.id)}
        onEdgeClick={(_, edge) => onEdgeClick?.(edge.id)}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
        <Panel position="top-right">
          <Chip label={`${nodes.length} Nodes`} size="small" sx={{ mr: 1 }} />
          <Chip label={`${edges.length} Edges`} size="small" />
        </Panel>
      </ReactFlow>
    </Box>
  );
}
